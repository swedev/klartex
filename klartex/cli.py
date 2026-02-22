"""Klartex CLI — render PDFs from the command line."""

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from klartex.renderer import render, get_registry

app = typer.Typer(help="Klartex — PDF generation via LaTeX")


@app.command("render")
def render_cmd(
    template: str = typer.Option(..., "--template", "-t", help="Template name"),
    data: Path = typer.Option(..., "--data", "-d", help="Path to JSON data file"),
    output: Path = typer.Option("output.pdf", "--output", "-o", help="Output PDF path"),
    page_template: Optional[str] = typer.Option(
        None,
        "--page-template",
        help="Page template file (path or '-' for stdin). Overrides data.page_template.",
    ),
):
    """Render a template to PDF."""
    if not data.exists():
        typer.echo(f"Error: data file not found: {data}", err=True)
        raise typer.Exit(1)

    # Read page template source if provided
    page_template_source = None
    if page_template is not None:
        if page_template == "-":
            page_template_source = sys.stdin.read()
        else:
            pt_path = Path(page_template)
            if not pt_path.exists():
                typer.echo(f"Error: page template file not found: {page_template}", err=True)
                raise typer.Exit(1)
            page_template_source = pt_path.read_text()

    raw = json.loads(data.read_text())
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
