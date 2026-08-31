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
    """Return the whole-page template path inferred from the surroundings.

    Lookup order:
      1. ``<data-stem>.tex.jinja`` next to the data file (if data is a file).
      2. ``./page_template.tex.jinja`` in the current working directory.
      3. None.
    """
    if data_path is not None:
        sibling = data_path.with_suffix(".tex.jinja")
        if sibling.is_file():
            return sibling
    cwd_default = Path.cwd() / DEFAULT_PAGE_TEMPLATE_FILENAME
    if cwd_default.is_file():
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
            "Page-template file owning both slots — one file for the whole "
            "design. The document-level settings in data.page_template (font, "
            "header_font, diff_style, margins) still apply. If omitted, "
            "klartex auto-detects <data-stem>.tex.jinja next to the data "
            "file, then ./page_template.tex.jinja in cwd. Assets referenced "
            "from the file (logos etc.) are found relative to its own "
            "directory, both by plain name (logo.pdf) and with a ./ or ../ "
            "prefix; plain names fall back to the working directory, ./ and "
            "../ references do not. For a symlinked file the target's "
            "directory applies. Cannot be combined with --header-template or "
            "--footer-template."
        ),
    ),
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
            "directory. Cannot be combined with --page-template; a slot flag "
            "also suppresses auto-detection."
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

    # Custom sources from files. Assets referenced from them resolve against
    # the files' shared directory (asset_dir), with cwd as fallback. Explicit
    # flags win over auto-detection, and a slot flag suppresses it entirely.
    page_template_source = None
    header_source = None
    footer_source = None
    asset_dir: Optional[Path] = None
    slot_flags = {
        "--header-template": header_template,
        "--footer-template": footer_template,
    }
    given_slots = {flag: value for flag, value in slot_flags.items() if value}

    if page_template is not None and given_slots:
        names = " and ".join(sorted(given_slots))
        typer.echo(
            "Error: --page-template owns both slots and cannot be combined "
            f"with {names}.",
            err=True,
        )
        raise typer.Exit(1)

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
    elif page_template is not None:
        pt_path = Path(page_template)
        if not pt_path.is_file():
            typer.echo(f"Error: page template file not found: {page_template}", err=True)
            raise typer.Exit(1)
        page_template_source = pt_path.read_text(encoding="utf-8")
        asset_dir = pt_path.resolve().parent
    else:
        auto = _autodetect_page_template(data)
        if auto is not None:
            page_template_source = auto.read_text(encoding="utf-8")
            asset_dir = auto.resolve().parent
            typer.echo(f"Using page template: {auto}", err=True)

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
            page_template_source=page_template_source,
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


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Address to bind to."),
    port: int = typer.Option(8000, "--port", help="Port to listen on."),
):
    """Run the HTTP compile endpoint (requires the `serve` extra).

    Serves `POST /render` (JSON in, PDF out) and `GET /health`. The server
    owns no authentication or rate limiting — put it behind a caller that
    does, which is why it binds to localhost unless told otherwise.
    """
    try:
        import uvicorn

        from klartex.server.app import app as fastapi_app
    except ImportError as e:
        root = (e.name or "").split(".")[0]
        if root not in {"fastapi", "uvicorn", "httpx"}:
            raise
        typer.echo(
            "Error: the serve extra is not installed. "
            "Install with: pip install 'klartex[serve]'",
            err=True,
        )
        raise typer.Exit(1)
    except ValueError as e:
        # Configuration is read from the environment when the server
        # modules are imported.
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    # One worker: the concurrency cap is a semaphore inside the process,
    # so a second worker would silently double it.
    uvicorn.run(fastapi_app, host=host, port=port, workers=1)


if __name__ == "__main__":
    app()
