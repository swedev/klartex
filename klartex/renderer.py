"""Core rendering pipeline: JSON data -> .tex -> PDF."""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import jinja2
import jsonschema

from klartex.branding import Branding, load_branding
from klartex.registry import discover_templates
from klartex.tex_escape import escape_data

# Paths relative to this package
_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = _ROOT / "templates"
CLS_DIR = _ROOT / "cls"
BRANDING_DIR = _ROOT / "branding"

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
    loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
)


def render(
    template_name: str,
    data: dict,
    branding: str | Branding = "default",
    branding_dir: str | Path | None = None,
    engine: str = "auto",
) -> bytes:
    """Render a template with data and branding to PDF bytes.

    Args:
        template_name: Name of the template (e.g. "protokoll")
        data: Template data as a dict (validated against schema)
        branding: Branding name (str) or Branding object
        branding_dir: Directory to load branding YAML from (default: built-in)
        engine: Rendering engine selection:
            - "auto" (default): Use .tex.jinja if it exists, otherwise recipe.yaml
            - "legacy": Force .tex.jinja path. Error if not available.
            - "recipe": Force recipe path. Error if not available.

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

    # Load branding
    if isinstance(branding, str):
        brand, resolved_branding_dir = load_branding(
            branding, Path(branding_dir) if branding_dir else BRANDING_DIR
        )
    else:
        brand, resolved_branding_dir = branding, BRANDING_DIR

    # Escape user data for LaTeX safety
    escaped_data = escape_data(data)

    # Determine which rendering path to use
    use_recipe = _select_engine(template_info, engine)

    if use_recipe:
        tex_source = _render_recipe(template_info, escaped_data, brand)
    else:
        tex_source = _render_legacy(template_name, escaped_data, brand)

    # Compile in temp directory
    return _compile_tex(tex_source, resolved_branding_dir)


def _select_engine(template_info, engine: str) -> bool:
    """Determine whether to use recipe rendering.

    Returns True for recipe path, False for legacy path.
    """
    if engine == "auto":
        # Prefer .tex.jinja for backward compatibility
        if template_info.has_legacy:
            return False
        if template_info.has_recipe:
            return True
        raise ValueError(
            f"Template '{template_info.name}' has neither .tex.jinja nor recipe.yaml"
        )
    elif engine == "legacy":
        if not template_info.has_legacy:
            raise ValueError(
                f"Template '{template_info.name}' has no .tex.jinja file "
                f"(required for engine='legacy')"
            )
        return False
    elif engine == "recipe":
        if not template_info.has_recipe:
            raise ValueError(
                f"Template '{template_info.name}' has no recipe.yaml file "
                f"(required for engine='recipe')"
            )
        return True
    else:
        raise ValueError(
            f"Invalid engine '{engine}'. Must be 'auto', 'legacy', or 'recipe'."
        )


def _render_legacy(template_name: str, escaped_data: dict, brand: Branding) -> str:
    """Render using the monolithic .tex.jinja path."""
    context = {
        "data": escaped_data,
        "brand": brand,
    }
    template = _jinja_env.get_template(f"{template_name}/{template_name}.tex.jinja")
    return template.render(context)


def _render_recipe(template_info, escaped_data: dict, brand: Branding) -> str:
    """Render using the YAML recipe path."""
    from klartex.recipe import load_recipe, prepare_recipe_context

    recipe = load_recipe(template_info.recipe_path)
    context = prepare_recipe_context(recipe, escaped_data, brand)

    template = _jinja_env.get_template("_recipe_base.tex.jinja")
    return template.render(context)


def _compile_tex(tex_source: str, branding_dir: Path) -> bytes:
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

        # Symlink branding dir so xelatex can find logos, fonts
        (tmp / "branding").symlink_to(branding_dir)

        # Build environment with cls/ on TEXINPUTS so \RequirePackage finds .sty files
        import os

        env = os.environ.copy()
        # TEXINPUTS: current dir, cls/ dir, then system default (trailing colon)
        env["TEXINPUTS"] = f".:{CLS_DIR}:"

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
