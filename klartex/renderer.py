"""Core rendering pipeline: JSON data → .tex → PDF."""

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
) -> bytes:
    """Render a template with data and branding to PDF bytes.

    Args:
        template_name: Name of the template (e.g. "protokoll")
        data: Template data as a dict (validated against schema)
        branding: Branding name (str) or Branding object

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
        brand = load_branding(branding, BRANDING_DIR)
    else:
        brand = branding

    # Escape user data for LaTeX safety
    escaped_data = escape_data(data)

    # Build Jinja2 context
    context = {
        "data": escaped_data,
        "brand": brand,
    }

    # Render .tex.jinja → .tex
    template = _jinja_env.get_template(f"{template_name}/{template_name}.tex.jinja")
    tex_source = template.render(context)

    # Compile in temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Write .tex source
        tex_path = tmp / "document.tex"
        tex_path.write_text(tex_source)

        # Symlink cls so xelatex can find it
        (tmp / "klartex-base.cls").symlink_to(CLS_DIR / "klartex-base.cls")

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
