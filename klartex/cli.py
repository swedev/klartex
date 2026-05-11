"""Klartex CLI — render PDFs from the command line."""

import json
import sys
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Optional

import typer

from klartex.renderer import render, get_registry

app = typer.Typer(help="Klartex — PDF generation via LaTeX", invoke_without_command=True)

# Filename for cwd-level page template auto-discovery.
DEFAULT_PAGE_TEMPLATE_FILENAME = "page_template.tex.jinja"


def _version_callback(value: bool):
    if value:
        typer.echo(f"klartex {pkg_version('klartex')}")
        raise typer.Exit()


def _autodetect_page_template(data_path: Optional[Path]) -> Optional[Path]:
    """Return the page-template path inferred from the working directory.

    Lookup order:
      1. ``<data-stem>.tex.jinja`` next to the data file (if data is a file).
      2. ``./page_template.tex.jinja`` in the current working directory.
      3. None.
    """
    if data_path is not None:
        sibling = data_path.with_suffix(".tex.jinja")
        if sibling.exists():
            return sibling
    cwd_default = Path.cwd() / DEFAULT_PAGE_TEMPLATE_FILENAME
    if cwd_default.exists():
        return cwd_default
    return None


@app.callback()
def main(
    ctx: typer.Context,
    data: Optional[Path] = typer.Option(None, "--data", "-d", help="Path to JSON data file (or omit for stdin)"),
    template: str = typer.Option("_block", "--template", "-t", help="Template name"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output PDF path (defaults to input filename with .pdf)"),
    page_template: Optional[str] = typer.Option(
        None,
        "--page-template",
        help=(
            "Page template file path. Overrides data.page_template. "
            "If omitted, klartex auto-detects <data-stem>.tex.jinja next to "
            "the data file, then ./page_template.tex.jinja in cwd."
        ),
    ),
    version: Optional[bool] = typer.Option(None, "--version", "-V", help="Show version and exit.", callback=_version_callback, is_eager=True),
):
    """Render JSON data to PDF. Reads from stdin if no --data is given."""
    if ctx.invoked_subcommand is not None:
        return

    # Read data from file or stdin
    if data is not None:
        if not data.exists():
            typer.echo(f"Error: data file not found: {data}", err=True)
            raise typer.Exit(1)
        raw_text = data.read_text()
    else:
        if sys.stdin.isatty():
            typer.echo("Error: no data provided. Use -d <file> or pipe JSON to stdin.", err=True)
            raise typer.Exit(1)
        raw_text = sys.stdin.read()

    # Resolve page template source. Explicit --page-template wins; otherwise
    # try <data-stem>.tex.jinja next to the data file, then
    # ./page_template.tex.jinja in cwd.
    page_template_source = None
    if page_template is not None:
        pt_path = Path(page_template)
        if not pt_path.exists():
            typer.echo(f"Error: page template file not found: {page_template}", err=True)
            raise typer.Exit(1)
        page_template_source = pt_path.read_text()
    else:
        auto = _autodetect_page_template(data)
        if auto is not None:
            page_template_source = auto.read_text()
            typer.echo(f"Using page template: {auto}", err=True)

    # Default output filename: same as input but with .pdf extension
    if output is None:
        output = Path(data.stem + ".pdf") if data is not None else Path("output.pdf")

    raw = json.loads(raw_text)
    try:
        pdf_bytes = render(template, raw, page_template_source=page_template_source)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    output.write_bytes(pdf_bytes)
    typer.echo(f"Written {len(pdf_bytes)} bytes to {output}")


@app.command("templates")
def list_templates():
    """List available templates."""
    registry = get_registry()
    for name, info in sorted(registry.items()):
        kind = " [block-engine]" if info.is_block_engine else " [recipe]"
        typer.echo(f"  {name:20s} {info.description}{kind}")


@app.command("schema")
def show_schema(
    template: str = typer.Argument(help="Template name"),
):
    """Print the JSON Schema for a template."""
    registry = get_registry()
    if template not in registry:
        typer.echo(f"Error: unknown template '{template}'", err=True)
        raise typer.Exit(1)
    typer.echo(json.dumps(registry[template].schema, indent=2, ensure_ascii=False))


@app.command("blocks")
def list_blocks():
    """List available block types for the block engine."""
    from klartex.components import _COMPONENTS

    for name, spec in sorted(_COMPONENTS.items()):
        if spec.block_schema_path:
            typer.echo(f"  {name:25s} {spec.description}")


@app.command("example")
def show_example(
    template: str = typer.Argument(help="Template name"),
):
    """Print an example JSON input for a template."""
    registry = get_registry()
    if template not in registry:
        typer.echo(f"Error: unknown template '{template}'", err=True)
        raise typer.Exit(1)
    info = registry[template]

    # Look for example file
    if info.is_block_engine:
        example_path = Path(__file__).resolve().parent / "schemas" / "block_engine.example.json"
    else:
        example_path = Path(__file__).resolve().parent / "templates" / template / "example.json"

    if not example_path.exists():
        typer.echo(f"Error: no example available for '{template}'", err=True)
        raise typer.Exit(1)
    typer.echo(example_path.read_text().rstrip())


@app.command("serve")
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h"),
    port: int = typer.Option(8000, "--port", "-p"),
):
    """Start the HTTP server."""
    import uvicorn
    from klartex.main import app as fastapi_app

    uvicorn.run(fastapi_app, host=host, port=port)


if __name__ == "__main__":
    app()
