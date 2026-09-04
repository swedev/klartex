"""Core rendering pipeline: JSON data -> .tex -> PDF."""

import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version as pkg_version
from pathlib import Path

import jinja2
import jsonschema

from klartex.inline_markup import render_inline
from klartex.jinja_env import make_env
from klartex.page_templates import font_files
from klartex.registry import discover_templates
from klartex.tex_escape import escape_data
from klartex.block_engine import BLOCK_ENGINE_TEMPLATE

# Paths relative to this package
_ROOT = Path(__file__).resolve().parent
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
_jinja_env = make_env(jinja2.FileSystemLoader([str(TEMPLATES_DIR)]))


@jinja2.pass_context
def _inline_filter(ctx, value):
    """Jinja filter: parse inline markup against the document language."""
    if value is None:
        return ""
    return render_inline(str(value), lang=ctx.get("lang", "sv"))


@jinja2.pass_context
def _inline_cell_filter(ctx, value):
    """`inline` for paragraph-mode tabular cells (p/X columns): \\n becomes
    \\newline, since \\\\ would end the table row instead of the line."""
    if value is None:
        return ""
    return render_inline(str(value), lang=ctx.get("lang", "sv"), newlines="cell")


@jinja2.pass_context
def _inline_flat_filter(ctx, value):
    """`inline` for LR-mode tabular cells (l columns), where no in-cell
    line break exists: \\n collapses to a space."""
    if value is None:
        return ""
    return render_inline(str(value), lang=ctx.get("lang", "sv"), newlines="space")


def _number_style(ctx) -> str:
    """Resolve the number style for a template context: an explicit
    ``number_format`` in the data wins, else the document language."""
    return ctx.get("number_format") or ctx.get("lang", "sv")


@jinja2.pass_context
def _money_filter(ctx, value):
    """Jinja filter: format an amount with two decimals per the document's
    number style. Swedish (default): thin-space groups and decimal comma
    (``32\\,400,00``); English: ``32,400.00``. Output is raw LaTeX."""
    if value is None:
        return ""
    formatted = f"{float(value):,.2f}"
    if _number_style(ctx) == "en":
        return formatted
    return (
        formatted.replace(",", "\x00").replace(".", ",").replace("\x00", r"\,")
    )


@jinja2.pass_context
def _num_filter(ctx, value):
    """Jinja filter: format a bare number (quantity, percentage) per the
    document's number style — no grouping, no forced decimals, decimal
    comma in Swedish."""
    if value is None:
        return ""
    # .10g rather than bare g: g flips to exponent notation at 6 significant
    # digits, which would turn quantity 1234567 into "1.23457e+06".
    formatted = f"{float(value):.10g}"
    if _number_style(ctx) == "en":
        return formatted
    return formatted.replace(".", ",")


_jinja_env.filters["inline"] = _inline_filter
_jinja_env.filters["inline_cell"] = _inline_cell_filter
_jinja_env.filters["inline_flat"] = _inline_flat_filter
_jinja_env.filters["money"] = _money_filter
_jinja_env.filters["num"] = _num_filter


def validate(template_name: str, data: dict) -> None:
    """Validate payload data against a template without rendering it.

    Runs exactly the validation `render()` runs: the JSON-Schema check
    against the template's validation schema (the base schema without the
    blocks' `oneOf`, so messages stay readable), then — on the block-engine
    path — the recursive per-block check of every block's type and payload.
    `render()` calls this function, so the two cannot diverge.

    No part of the TeX toolchain is touched: nothing is escaped, compiled or
    written to disk, and `xelatex` need not be installed.

    Args:
        template_name: Name of the template (e.g. "protokoll", "_block")
        data: Template data as a dict

    Returns:
        None. Validity is signalled by returning without raising.

    Raises:
        ValueError: The template name is unknown; the message lists the
            available templates.
        jsonschema.ValidationError: The data violates the template schema.
        BlockValidationError: A block on the block-engine path has an unknown
            type or a payload that fails its component schema. `path` locates
            the offending block.

    Page-template composition is *not* covered: those checks run at render
    time, when the chrome is composed. A payload that passes here can still
    raise from `render()` for a `page_template.margins.top` at or below the
    header band while a predefined header carries content, a `letterhead`
    whose `fields.org_name` is present but empty, or a whole-page source
    combined with a per-slot source. External font files are likewise checked
    against the asset root only by `render()`, which knows `asset_dir`.
    """
    registry = get_registry()

    if template_name not in registry:
        available = ", ".join(sorted(registry.keys()))
        raise ValueError(f"Unknown template '{template_name}'. Available: {available}")

    template_info = registry[template_name]

    # Validate data against schema (use validation_schema to avoid oneOf noise;
    # per-block validation below gives better error messages)
    jsonschema.validate(data, template_info.get_validation_schema())

    # Validate block types and payloads before escaping (escaping mangles underscores)
    if template_info.is_block_engine:
        _validate_blocks(data.get("body", []), ["body"])


def render(
    template_name: str,
    data: dict,
    asset_dir: Path | str | None = None,
    *,
    header_source: str | None = None,
    footer_source: str | None = None,
    page_template_source: str | None = None,
) -> bytes:
    """Render a template with data to PDF bytes.

    Args:
        template_name: Name of the template (e.g. "protokoll")
        data: Template data as a dict (validated against schema)
        header_source: Optional raw .tex.jinja content owning the header slot.
            The footer slot still resolves from data["page_template"].
        footer_source: Optional raw .tex.jinja content owning the footer slot.
            The header slot still resolves from data["page_template"].
        page_template_source: Optional raw content owning both page-template
            slots — one file for the whole design. The document-level settings
            in data["page_template"] (font, header_font, diff_style, margins)
            still apply, and are emitted before the source so its own
            \\geometry and font commands win. Cannot be combined with
            `header_source` or `footer_source`, which raises `ValueError`.
        asset_dir: Optional directory that assets (`\\includegraphics`,
            `\\input`, custom fonts, …) resolve against. Useful when callers
            (e.g. a server) keep page-template bundles in a known location
            separate from the working directory. A relative path is resolved
            against the caller's cwd; a path that is not an existing
            directory raises `ValueError`. Note that the source arguments
            are raw text with no path of their own, so API
            callers must pass `asset_dir` explicitly to get assets resolved
            outside cwd.

            Both reference styles work, via two different mechanisms:

            * *Plain names* (`\\input{brand}`, `\\includegraphics{logo.pdf}`)
              go through TEXINPUTS and get a full search chain: the internal
              tempdir, the bundled `cls/`, `asset_dir`, the caller's cwd, and
              finally any inherited TEXINPUTS. Of the caller-controlled roots
              that means `asset_dir` wins, with cwd as fallback.
            * *Explicitly relative names* (`./logo.pdf`, `../shared/x.tex`)
              are never looked up in TEXINPUTS by Kpathsea; they resolve
              against xelatex's working directory, which this function sets
              to `asset_dir` (or the caller's cwd when `asset_dir` is unset).
              There is no fallback chain — a process has exactly one cwd — so
              a `./` reference that is missing from `asset_dir` fails even if
              the file exists in the caller's cwd.

            A `./` reference inside a *nested* included file also resolves
            against that single asset root, not against the including file's
            own directory.

            Font files named by a file-form `page_template.font` /
            `header_font` follow the explicitly relative contract, and are
            checked against the asset root before compiling: a face file that
            is not there raises `ValueError` naming it.

            Build artifacts stay in an internal tempdir (`-output-directory`);
            rendering never writes into `asset_dir` or the caller's cwd.

    Returns:
        PDF file contents as bytes

    Raises:
        RuntimeError: `xelatex` is not on PATH, or the compilation failed.
            The toolchain check runs after every check on the payload — so
            validation errors stay reportable where TeX is absent — and
            before any escaping or template rendering, so a missing toolchain
            surfaces as itself rather than as a failure mid-render.
    """
    validate(template_name, data)

    template_info = get_registry()[template_name]

    # The payload checks first, so they remain reachable without TeX; both
    # also settle the asset root the compile will run in.
    _preflight_font_files(data, asset_dir)
    _resolve_asset_root(asset_dir)
    _require_xelatex()

    # Escape user data for LaTeX safety
    escaped_data = escape_data(data)

    # Block engine path
    if template_info.is_block_engine:
        # Walk nested block structures and restore unescaped block type strings
        # (escaping turns "description_list" into "description\_list", which then
        # fails to match the dispatch). Also restore raw source on latex blocks.
        _restore_block_types(data.get("body", []), escaped_data["body"])
        tex_source = _render_block_engine(
            escaped_data,
            header_source=header_source,
            footer_source=footer_source,
            page_template_source=page_template_source,
        )
        return _compile_tex(tex_source, asset_dir=asset_dir)

    # Recipe path
    tex_source = _render_recipe(
        template_info,
        escaped_data,
        header_source=header_source,
        footer_source=footer_source,
        page_template_source=page_template_source,
    )
    return _compile_tex(tex_source, asset_dir=asset_dir)


def _render_image_reference() -> str:
    """The render image tag matching this installation.

    Every release publishes `ghcr.io/swedev/klartex-render:X.Y.Z` with the
    tag equal to the klartex version, so the installed version names an image
    that exists. Falls back to the placeholder when no distribution metadata
    is installed (a source tree on `sys.path`), where no version is known.
    """
    try:
        return f"ghcr.io/swedev/klartex-render:{pkg_version('klartex')}"
    except PackageNotFoundError:
        return "ghcr.io/swedev/klartex-render:X.Y.Z"


def _require_xelatex() -> None:
    """Fail before any rendering work when the environment has no TeX.

    Raises:
        RuntimeError: If `xelatex` is not on PATH. The message names the
            published render image before the TeX Live install, since the
            image renders without a multi-gigabyte install and without root
            on the host; installing is the answer for callers that embed
            klartex as a library in their own environment.
    """
    if shutil.which("xelatex"):
        return
    raise RuntimeError(
        "xelatex not found: this environment has no TeX installation.\n"
        "\n"
        "To render without installing TeX, run the published render image — "
        "it serves POST /render locally and leaves the host without a TeX "
        "install:\n"
        f"  docker run --rm -p 127.0.0.1:8000:8000 {_render_image_reference()}\n"
        "\n"
        "Install TeX Live if klartex is to run as a library in this "
        "environment:\n"
        "  macOS:  brew install --cask mactex\n"
        "  Ubuntu: apt install texlive-xetex"
    )


def _resolve_asset_root(asset_dir: Path | str | None) -> Path:
    """The directory explicitly relative asset names resolve against.

    The resolved `asset_dir` when one is given, else the caller's cwd.
    `.resolve()` is what lets assets follow a symlinked template bundle to its
    target directory, and the result has to be absolute because it serves as
    both a TEXINPUTS entry and xelatex's working directory.

    Raises:
        ValueError: If `asset_dir` is not an existing directory. Raised here
                    rather than at the subprocess, so the caller bug surfaces
                    as a clear error even where TeX is not installed.
    """
    if asset_dir is None:
        return Path(os.getcwd())
    asset_root = Path(asset_dir).resolve()
    if not asset_root.is_dir():
        raise ValueError(f"asset_dir is not a directory: {asset_dir}")
    return asset_root


def _preflight_font_files(data: dict, asset_dir: Path | str | None) -> None:
    """Check the font face files a file-form font references are present.

    File fonts are emitted with `Path=./`, so the engine resolves them against
    its working directory — the asset root, with no search chain behind it. A
    face file that never arrived would otherwise surface as a fontspec error
    buried in the TeX log; here it names the file and the contract, before
    xelatex is even looked for.

    Raises:
        ValueError: If a referenced face file is not a readable file in the
                    asset root, or if `asset_dir` is not a directory.
    """
    files = font_files(data.get("page_template"))
    if not files:
        return
    asset_root = _resolve_asset_root(asset_dir)
    for name in files:
        path = asset_root / name
        if not path.is_file() or not os.access(path, os.R_OK):
            raise ValueError(
                f"Font file '{name}' is not readable in the asset root "
                f"({asset_root}). Font files resolve against asset_dir alone "
                "(the working directory when no asset_dir is set) — there is "
                "no search chain, so send the file with the render."
            )


class BlockValidationError(ValueError):
    """Raised when a block on the block-engine path fails validation.

    `path` addresses the failing node in the submitted data: `["body", 1]` is
    the block itself, `["body", 0, "items", 1, 0, "text"]` a field inside a
    nested block. The message is the human-readable form of the same position.
    """

    def __init__(self, message: str, path: Sequence[str | int]):
        super().__init__(message)
        self.path = list(path)


def _format_block_path(path: Sequence[str | int]) -> str:
    """Render a block path as the text form used in error messages.

    `["body", 0, "items", 1, 0]` becomes ``body[0].items[1][0]``.
    """
    segments = []
    for i, seg in enumerate(path):
        if isinstance(seg, int):
            segments.append(f"[{seg}]")
        elif i == 0:
            segments.append(str(seg))
        else:
            segments.append(f".{seg}")
    return "".join(segments)


def _child_block_lists(
    block: dict, path: Sequence[str | int] = ()
) -> list[tuple[list[str | int], list]]:
    """Return the nested block carriers of `block` as (path, blocks) pairs.

    Single source of truth for which block types nest other blocks. Both
    recursive validation and `_restore_block_types` walk these carriers, so
    any new nesting block only needs to be added here.
    """
    btype = block.get("type")
    if btype == "list":
        return [
            ([*path, "items", i, "content"], item.get("content", []))
            for i, item in enumerate(block.get("items", []))
            if isinstance(item, dict)
        ]
    if btype == "columns":
        return [
            ([*path, "items", i], col)
            for i, col in enumerate(block.get("items", []))
            if isinstance(col, list)
        ]
    if btype == "clause":
        return [([*path, "content"], block.get("content", []))]
    return []


def _validate_blocks(blocks: list, path: Sequence[str | int]) -> None:
    """Validate every block against its schema, recursing into nested carriers.

    `path` locates the current block list, e.g. ``["body", 2, "content"]`` or
    ``["body", 1, "items", 0]``.
    """
    from klartex.block_engine import KNOWN_BLOCK_TYPES
    from klartex.components import get_component

    for i, block in enumerate(blocks):
        where = [*path, i]
        where_text = _format_block_path(where)
        if not isinstance(block, dict):
            continue  # non-dict shapes are rejected by the carrier's schema
        block_type = block.get("type")
        if not block_type:
            raise BlockValidationError(
                f"Block at {where_text} is missing 'type'", where
            )
        if block_type not in KNOWN_BLOCK_TYPES:
            available = ", ".join(sorted(KNOWN_BLOCK_TYPES))
            raise BlockValidationError(
                f"Unknown block type '{block_type}' at {where_text}. "
                f"Available: {available}",
                where,
            )
        spec = get_component(block_type)
        block_schema = spec.get_block_schema()
        if block_schema:
            try:
                jsonschema.validate(block, block_schema)
            except jsonschema.ValidationError as e:
                raise BlockValidationError(
                    f"Invalid '{block_type}' block at {where_text}: {e.message}",
                    [*where, *e.absolute_path],
                ) from e
        for child_path, child_blocks in _child_block_lists(block, where):
            _validate_blocks(child_blocks, child_path)


def _restore_block_types(orig_blocks: list, esc_blocks: list) -> None:
    """Walk parallel block-arrays and copy unescaped `type` (and raw `latex.source`)
    from the original onto the escape-mangled copy.

    Recurses into the nested block carriers listed by `_child_block_lists`.
    """
    for orig, esc in zip(orig_blocks, esc_blocks):
        if not isinstance(orig, dict) or not isinstance(esc, dict):
            continue
        btype = orig.get("type")
        if btype is None:
            continue
        esc["type"] = btype
        if btype == "latex" and "source" in orig:
            esc["source"] = orig["source"]
        for (_, o_kids), (_, e_kids) in zip(
            _child_block_lists(orig), _child_block_lists(esc)
        ):
            _restore_block_types(o_kids, e_kids)


def _render_block_engine(
    escaped_data: dict,
    *,
    header_source: str | None = None,
    footer_source: str | None = None,
    page_template_source: str | None = None,
) -> str:
    """Render using the universal block engine path."""
    from klartex.block_engine import prepare_block_context

    context = prepare_block_context(
        escaped_data,
        header_source=header_source,
        footer_source=footer_source,
        page_template_source=page_template_source,
    )
    template = _jinja_env.get_template("_block_engine.tex.jinja")
    return template.render(context)


def _render_recipe(
    template_info,
    escaped_data: dict,
    *,
    header_source: str | None = None,
    footer_source: str | None = None,
    page_template_source: str | None = None,
) -> str:
    """Render using the YAML recipe path."""
    from klartex.recipe import load_recipe, prepare_recipe_context

    recipe = load_recipe(template_info.recipe_path)
    context = prepare_recipe_context(
        recipe,
        escaped_data,
        header_source=header_source,
        footer_source=footer_source,
        page_template_source=page_template_source,
    )
    template = _jinja_env.get_template("_recipe_base.tex.jinja")
    return template.render(context)


def _compile_tex(tex_source: str, asset_dir: Path | str | None = None) -> bytes:
    """Compile LaTeX source to PDF bytes.

    xelatex runs with its working directory set to the *asset root* — the
    resolved `asset_dir` when given, else the caller's cwd — and writes all
    build artifacts to a private tempdir via `-output-directory`. The cwd is
    what makes explicitly relative asset names (`./logo.pdf`, `../shared.tex`)
    resolve: Kpathsea never consults TEXINPUTS for those, it only tries them
    as-is against the process cwd. Plain names are carried by TEXINPUTS
    instead, whose order (tempdir, bundled cls/, asset_dir, caller cwd,
    inherited) is unchanged by the cwd switch because the leading `.` entry
    is replaced with the absolute tempdir path.

    Presence of the toolchain is `render()`'s check (`_require_xelatex`),
    made before any of the rendering work whose output arrives here.
    """
    # `render()` has already resolved this and rejected a bogus directory,
    # which with cwd=asset_root would otherwise die as a raw FileNotFoundError
    # from subprocess.
    asset_root = _resolve_asset_root(asset_dir)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Write .tex source
        tex_path = tmp / "document.tex"
        tex_path.write_text(tex_source, encoding="utf-8")

        # Symlink entire cls/ directory so xelatex can find .cls and .sty files
        (tmp / "cls").symlink_to(CLS_DIR)
        # Also symlink klartex-base.cls at top level for \documentclass{klartex-base}
        (tmp / "klartex-base.cls").symlink_to(CLS_DIR / "klartex-base.cls")

        # Build environment with the tempdir, cls/, optional asset_dir, and the
        # caller's cwd on TEXINPUTS. asset_dir slots in after the bundled cls/
        # so server callers can resolve page-template bundles without chdir.
        #
        # The first entry is the absolute tempdir rather than the usual `.`:
        # xelatex now runs with cwd=asset_root, so a bare `.` would mean the
        # asset root and place it *ahead* of the bundled cls/, letting a
        # template-dir file shadow a .sty/.cls. Spelling the tempdir out keeps
        # the plain-name search order identical to before the cwd change.
        # All entries are absolute for the same reason: a relative entry would
        # now be interpreted against the asset root.
        env = os.environ.copy()
        existing_texinputs = env.get("TEXINPUTS", "")
        cwd = os.getcwd()
        asset_part = f"{asset_root}:" if asset_dir is not None else ""
        env["TEXINPUTS"] = f"{tmp}:{CLS_DIR}:{asset_part}{cwd}:{existing_texinputs}"

        # Run xelatex twice (for page references).
        # -output-directory keeps every build artifact (.aux, .log, .pdf) in
        # the tempdir even though cwd is the user's asset root, so a render
        # never writes into the template directory or the caller's cwd. TeX
        # Live also searches the output directory for inputs, so the second
        # run finds the first run's .aux there (tmp is on TEXINPUTS too).
        # -no-shell-escape disables \write18 and shell command execution from
        # within the .tex source — important when callers (e.g. klartex.se)
        # render user-supplied page templates that could otherwise execute
        # arbitrary shell commands during compilation.
        for _ in range(2):
            try:
                result = subprocess.run(
                    [
                        "xelatex",
                        "-interaction=nonstopmode",
                        "-halt-on-error",
                        "-no-shell-escape",
                        "-output-directory",
                        tmpdir,
                        str(tex_path),
                    ],
                    cwd=asset_root,
                    capture_output=True,
                    timeout=60,
                    env=env,
                )
            except subprocess.TimeoutExpired as e:
                raise RuntimeError(
                    f"xelatex timed out after {e.timeout:.0f}s"
                ) from e
            if result.returncode != 0:
                raise RuntimeError(
                    f"xelatex failed (exit {result.returncode}):\n"
                    f"{result.stdout.decode(errors='replace')[-2000:]}"
                )

        pdf_path = tmp / "document.pdf"
        if not pdf_path.exists():
            raise RuntimeError("xelatex did not produce a PDF")

        return pdf_path.read_bytes()
