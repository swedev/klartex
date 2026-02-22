"""Core rendering pipeline: JSON data -> .tex -> PDF."""

import json
import subprocess
import tempfile
from pathlib import Path

import jinja2
import jsonschema

from klartex.registry import discover_templates
from klartex.tex_escape import escape_data
from klartex.block_engine import BLOCK_ENGINE_TEMPLATE

# Paths relative to this package
_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = _ROOT / "templates"
CLS_DIR = _ROOT / "cls"

# Template registry (discovered at import time)
_registry = None


def get_registry():
    global _registry
    if _registry is None:
        _registry = discover_templates(TEMPLATES_DIR)
    return _registry


# Jinja2 environment with LaTeX-safe delimiters
_jinja_env = jinja2.Environment(
    block_start_string=r"\BLOCK{",
    block_end_string=r"}",
    variable_start_string=r"\VAR{",
    variable_end_string=r"}",
    comment_start_string=r"\#{",
    comment_end_string=r"}",
    line_statement_prefix="%%",
    line_comment_prefix="%#",
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=False,
    loader=jinja2.FileSystemLoader([str(TEMPLATES_DIR)]),
)


def render(
    template_name: str,
    data: dict,
    page_template_source: str | None = None,
) -> bytes:
    """Render a template with data to PDF bytes.

    Args:
        template_name: Name of the template (e.g. "protokoll")
        data: Template data as a dict (validated against schema)
        page_template_source: Optional raw .tex.jinja content for the page
            template. When set, this is used directly instead of looking up
            the built-in page template from data["page_template"].

    Returns:
        PDF file contents as bytes
    """
    registry = get_registry()

    if template_name not in registry:
        available = ", ".join(sorted(registry.keys()))
        raise ValueError(f"Unknown template '{template_name}'. Available: {available}")

    template_info = registry[template_name]

    # Validate data against schema
    jsonschema.validate(data, template_info.schema)

    # Validate block types and payloads before escaping (escaping mangles underscores)
    if template_info.is_block_engine:
        from klartex.block_engine import KNOWN_BLOCK_TYPES
        from klartex.components import get_component

        for i, block in enumerate(data.get("body", [])):
            block_type = block.get("type")
            if not block_type:
                raise ValueError(f"Block at index {i} is missing 'type'")
            if block_type not in KNOWN_BLOCK_TYPES:
                available = ", ".join(sorted(KNOWN_BLOCK_TYPES))
                raise ValueError(
                    f"Unknown block type '{block_type}' at index {i}. "
                    f"Available: {available}"
                )
            # Validate block payload against its specific schema
            spec = get_component(block_type)
            block_schema = spec.get_block_schema()
            if block_schema:
                try:
                    jsonschema.validate(block, block_schema)
                except jsonschema.ValidationError as e:
                    raise ValueError(
                        f"Invalid '{block_type}' block at index {i}: {e.message}"
                    ) from e

    # Escape user data for LaTeX safety
    escaped_data = escape_data(data)

    # Block engine path
    if template_info.is_block_engine:
        for i, block in enumerate(data.get("body", [])):
            # Restore block type (escaping mangles underscores: title_page → title\_page)
            escaped_data["body"][i]["type"] = block["type"]
            # Restore raw source on latex blocks (must not be escaped)
            if block.get("type") == "latex" and "source" in block:
                escaped_data["body"][i]["source"] = block["source"]
        tex_source = _render_block_engine(escaped_data, page_template_source)
        return _compile_tex(tex_source)

    # Recipe path
    tex_source = _render_recipe(template_info, escaped_data, page_template_source)
    return _compile_tex(tex_source)


def _render_block_engine(
    escaped_data: dict, page_template_source: str | None = None
) -> str:
    """Render using the universal block engine path."""
    from klartex.block_engine import prepare_block_context

    context = prepare_block_context(escaped_data, page_template_source)
    template = _jinja_env.get_template("_block_engine.tex.jinja")
    return template.render(context)


def _render_recipe(
    template_info, escaped_data: dict, page_template_source: str | None = None
) -> str:
    """Render using the YAML recipe path."""
    from klartex.recipe import load_recipe, prepare_recipe_context

    recipe = load_recipe(template_info.recipe_path)
    context = prepare_recipe_context(recipe, escaped_data, page_template_source)
    template = _jinja_env.get_template("_recipe_base.tex.jinja")
    return template.render(context)


def _compile_tex(tex_source: str) -> bytes:
    """Compile LaTeX source to PDF bytes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Write .tex source
        tex_path = tmp / "document.tex"
        tex_path.write_text(tex_source)

        # Symlink entire cls/ directory so xelatex can find .cls and .sty files
        (tmp / "cls").symlink_to(CLS_DIR)
        # Also symlink klartex-base.cls at top level for \documentclass{klartex-base}
        (tmp / "klartex-base.cls").symlink_to(CLS_DIR / "klartex-base.cls")

        # Build environment with cls/ and caller's cwd on TEXINPUTS
        import os

        env = os.environ.copy()
        existing_texinputs = env.get("TEXINPUTS", "")
        cwd = os.getcwd()
        env["TEXINPUTS"] = f".:{CLS_DIR}:{cwd}:{existing_texinputs}"

        # Run xelatex twice (for page references)
        for _ in range(2):
            result = subprocess.run(
                [
                    "xelatex",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    "document.tex",
                ],
                cwd=tmpdir,
                capture_output=True,
                timeout=30,
                env=env,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"xelatex failed (exit {result.returncode}):\n"
                    f"{result.stdout.decode(errors='replace')[-2000:]}"
                )

        pdf_path = tmp / "document.pdf"
        if not pdf_path.exists():
            raise RuntimeError("xelatex did not produce a PDF")

        return pdf_path.read_bytes()
