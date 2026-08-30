"""Klartex CLI — render PDFs from the command line."""

import json
import sys
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Optional

import typer

from klartex.renderer import render, get_registry

app = typer.Typer(help="Klartex — PDF generation via LaTeX", invoke_without_command=True)

def _version_callback(value: bool):
    if value:
        typer.echo(f"klartex {pkg_version('klartex')}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    data: Optional[Path] = typer.Option(None, "--data", "-d", help="Path to JSON data file (or omit for stdin)"),
    template: str = typer.Option("_block", "--template", "-t", help="Template name"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output PDF path (defaults to input filename with .pdf)"),
    header_template: Optional[str] = typer.Option(
        None,
        "--header-template",
        help=(
            "Page-template file owning the header slot. The footer slot still "
            "comes from data.page_template. Assets referenced from the file "
            "(logos etc.) are found relative to its own directory, both by "
            "plain name (logo.pdf) and with a ./ or ../ prefix; plain names "
            "fall back to the working directory, ./ and ../ references do "
            "not. For a symlinked file the target's directory applies. A "
            "--header-template and a --footer-template must live in the same "
            "directory."
        ),
    ),
    footer_template: Optional[str] = typer.Option(
        None,
        "--footer-template",
        help=(
            "Page-template file owning the footer slot. The header slot still "
            "comes from data.page_template. Same asset resolution and the same "
            "restrictions as --header-template."
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
        if not data.is_file():
            typer.echo(f"Error: data path is not a file: {data}", err=True)
            raise typer.Exit(1)
        raw_text = data.read_text(encoding="utf-8")
    else:
        if sys.stdin.isatty():
            typer.echo("Error: no data provided. Use -d <file> or pipe JSON to stdin.", err=True)
            raise typer.Exit(1)
        raw_text = sys.stdin.read()

    # Custom slot sources from files. Assets referenced from them resolve
    # against the files' shared directory (asset_dir), with cwd as fallback.
    header_source = None
    footer_source = None
    asset_dir: Optional[Path] = None
    slot_flags = {
        "--header-template": header_template,
        "--footer-template": footer_template,
    }
    given_slots = {flag: value for flag, value in slot_flags.items() if value}

    if given_slots:
        slot_paths = {}
        for flag, value in given_slots.items():
            path = Path(value)
            if not path.is_file():
                typer.echo(f"Error: page template file not found: {value}", err=True)
                raise typer.Exit(1)
            slot_paths[flag] = path.resolve()
        parents = {path.parent for path in slot_paths.values()}
        if len(parents) > 1:
            typer.echo(
                "Error: --header-template and --footer-template must live in "
                "the same directory (assets resolve against one directory).",
                err=True,
            )
            raise typer.Exit(1)
        asset_dir = parents.pop()
        if "--header-template" in slot_paths:
            header_source = slot_paths["--header-template"].read_text(encoding="utf-8")
        if "--footer-template" in slot_paths:
            footer_source = slot_paths["--footer-template"].read_text(encoding="utf-8")

    # Default output filename: same as input but with .pdf extension
    if output is None:
        output = Path(data.stem + ".pdf") if data is not None else Path("output.pdf")

    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError as e:
        typer.echo(f"Error: invalid JSON input: {e}", err=True)
        raise typer.Exit(1)

    try:
        pdf_bytes = render(
            template,
            raw,
            asset_dir=asset_dir,
            header_source=header_source,
            footer_source=footer_source,
        )
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    try:
        output.write_bytes(pdf_bytes)
    except OSError as e:
        typer.echo(f"Error: could not write output to {output}: {e}", err=True)
        raise typer.Exit(1)
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
    typer.echo(example_path.read_text(encoding="utf-8").rstrip())


if __name__ == "__main__":
    app()
