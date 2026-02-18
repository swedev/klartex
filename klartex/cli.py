"""Klartex CLI — render PDFs from the command line."""

import json
import sys
from pathlib import Path

import typer

from klartex.renderer import render, get_registry, BRANDING_DIR

app = typer.Typer(help="Klartex — PDF generation via LaTeX")


@app.command("render")
def render_cmd(
    template: str = typer.Option(..., "--template", "-t", help="Template name"),
    data: Path = typer.Option(..., "--data", "-d", help="Path to JSON data file"),
    output: Path = typer.Option("output.pdf", "--output", "-o", help="Output PDF path"),
    branding: str = typer.Option("default", "--branding", "-b", help="Branding name"),
    branding_dir: Path = typer.Option(None, "--branding-dir", help="Directory with branding YAML files"),
    engine: str = typer.Option("auto", "--engine", "-e", help="Rendering engine: auto, legacy, or recipe"),
):
    """Render a template to PDF."""
    if not data.exists():
        typer.echo(f"Error: data file not found: {data}", err=True)
        raise typer.Exit(1)

    raw = json.loads(data.read_text())
    try:
        pdf_bytes = render(template, raw, branding=branding, branding_dir=branding_dir, engine=engine)
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
        engine_indicator = ""
        if info.has_legacy and info.has_recipe:
            engine_indicator = " [legacy+recipe]"
        elif info.has_recipe:
            engine_indicator = " [recipe]"
        else:
            engine_indicator = " [legacy]"
        typer.echo(f"  {name:20s} {info.description}{engine_indicator}")


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
