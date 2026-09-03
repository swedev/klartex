"""Compile endpoint: JSON in, PDF out. The only place that runs xelatex.

`klartex.render()` needs its page-template sources as strings and its
assets as a directory on disk. This endpoint takes both inline — the caller
sends `page_template_source` or `header_source`/`footer_source`, plus
`assets` as base64 — writes the
assets to a temporary directory for the duration of the call, and deletes
it afterwards. Nothing survives a request: no registry, no volume, no
knowledge of who asked.

Validation errors and xelatex failures are mapped to HTTP responses with
structured detail. Schema violations and block validation errors both
carry `detail.path` — a `["body", 1, "items", 0, "text"]` list addressing
the failing node in the submitted data — so the caller can pass it
straight through to its own client. Both shapes come from the core:
`ValidationError.absolute_path` for schema violations,
`BlockValidationError.path` for block failures.
"""

import base64
import logging
import os
import re
import tempfile
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from jsonschema import ValidationError
from pydantic import BaseModel, Field

from klartex import BlockValidationError, render as klartex_render
from klartex.page_templates import font_files

log = logging.getLogger(__name__)

router = APIRouter(tags=["render"])


def env_positive_int(name: str, default: int) -> int:
    """Read `name` from the environment as a positive integer.

    An unset variable yields `default`. Anything else that is not a
    positive integer raises `ValueError` at import time, naming the
    variable: `KLARTEX_MAX_CONCURRENT=0` would otherwise start a process
    that answers 503 to every request.
    """
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(
            f"{name} must be a positive integer, got {raw!r}"
        ) from None
    if value < 1:
        raise ValueError(f"{name} must be a positive integer, got {value}")
    return value


# Limits on what a single request may carry. A caller that keeps
# page-template bundles of its own should mirror these, so a bundle it
# accepted is one this endpoint can render.
MAX_TEMPLATE_BYTES = 1 * 1024 * 1024        # 1 MB per slot source
MAX_ASSET_BYTES = 5 * 1024 * 1024           # 5 MB per file
MAX_ASSETS = 10

# Stricter than the core's own filename pattern, which admits `/` and `..`.
# Enforced here so no caller — not even a faulty one — can write outside
# the per-request temporary directory.
ASSET_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

# Cap on concurrent xelatex runs. FastAPI dispatches sync endpoints to a
# thread pool of ~40 threads, so without a cap that many xelatex processes
# can start at once. The value assumes a single uvicorn worker per
# process: additional workers or replicas multiply the effective cap.
MAX_CONCURRENT_RENDERS = env_positive_int("KLARTEX_MAX_CONCURRENT", 2)

_render_slots = threading.BoundedSemaphore(MAX_CONCURRENT_RENDERS)


class RenderRequest(BaseModel):
    template: str = Field(
        ...,
        description="Template name. Use `_block` for the block-engine path.",
        examples=["_block", "protokoll", "faktura"],
    )
    data: dict = Field(..., description="Template data; validated against schema.")
    page_template_source: str | None = Field(
        None,
        description=(
            "Page-template source owning both slots — one source for the "
            "whole design. The document-level settings in "
            "`data.page_template` still apply. Cannot be combined with "
            "`header_source` or `footer_source`."
        ),
    )
    header_source: str | None = Field(
        None,
        description=(
            "Page-template source owning the header slot, or null to let "
            "`data.page_template` decide it."
        ),
    )
    footer_source: str | None = Field(
        None,
        description=(
            "Page-template source owning the footer slot, or null to let "
            "`data.page_template` decide it."
        ),
    )
    assets: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Bundle assets as base64, keyed by filename. Written to a "
            "temporary directory that is handed to xelatex and deleted "
            "when the render returns."
        ),
    )


def _input_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={"type": "input_error", "message": message},
    )


def _decode_assets(assets: dict[str, str]) -> dict[str, bytes]:
    """Validate filenames and sizes, returning the decoded asset bytes."""
    if len(assets) > MAX_ASSETS:
        raise _input_error(f"Too many assets ({len(assets)}); max is {MAX_ASSETS}")

    decoded: dict[str, bytes] = {}
    for filename, b64 in assets.items():
        if not ASSET_NAME_RE.match(filename):
            raise _input_error(
                f"Invalid asset filename {filename!r}; "
                f"must match {ASSET_NAME_RE.pattern}"
            )
        try:
            raw = base64.b64decode(b64, validate=True)
        except (ValueError, TypeError) as e:
            raise _input_error(f"asset {filename!r}: invalid base64: {e}") from e
        if len(raw) > MAX_ASSET_BYTES:
            raise _input_error(
                f"asset {filename!r}: {len(raw)} bytes exceeds limit "
                f"{MAX_ASSET_BYTES}"
            )
        decoded[filename] = raw
    return decoded


def _check_encodable(value: object, where: str) -> None:
    """Reject text that cannot survive a UTF-8 round trip.

    JSON admits escaped lone surrogates (`"\\ud800"`), and Python parses
    them into `str` values that no UTF-8 encoder accepts. Left alone, such
    a string fails much later — while the .tex file is written, or while
    the JSON error response that quotes it is serialised — and answers
    with a bare 500 that is outside the documented error contract. Caught
    here it is what it is: bad input.
    """
    if isinstance(value, str):
        try:
            value.encode()
        except UnicodeEncodeError as e:
            raise _input_error(
                f"{where}: text is not valid Unicode "
                f"(unpaired surrogate at position {e.start})"
            ) from e
    elif isinstance(value, dict):
        for key, item in value.items():
            _check_encodable(key, where)
            _check_encodable(item, f"{where}.{key}" if isinstance(key, str) else where)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _check_encodable(item, f"{where}[{i}]")


def _check_source_size(field: str, source: str | None) -> None:
    if source is None:
        return
    source_bytes = len(source.encode())
    if source_bytes > MAX_TEMPLATE_BYTES:
        raise _input_error(
            f"{field}: {source_bytes} bytes exceeds limit {MAX_TEMPLATE_BYTES}"
        )


@router.post(
    "/render",
    response_class=Response,
    responses={
        200: {"content": {"application/pdf": {}}},
        400: {
            "description": (
                "Schema validation or input failure. `detail.type` is "
                "`validation_error` or `input_error`; `detail.path` "
                "locates the failing node when one can be identified."
            )
        },
        500: {"description": "xelatex failure (`detail.type` is `render_error`)"},
        503: {
            "description": (
                "Too many concurrent renders — `detail.type` is "
                "`overloaded` and `Retry-After` says when to come back."
            )
        },
    },
)
def render(req: RenderRequest) -> Response:
    """Compile a template + data combination to a PDF."""
    _check_encodable(req.template, "template")
    _check_encodable(req.page_template_source, "page_template_source")
    _check_encodable(req.header_source, "header_source")
    _check_encodable(req.footer_source, "footer_source")
    _check_encodable(req.data, "data")

    assets = _decode_assets(req.assets)
    _check_source_size("page_template_source", req.page_template_source)
    _check_source_size("header_source", req.header_source)
    _check_source_size("footer_source", req.footer_source)

    if not _render_slots.acquire(blocking=False):
        raise HTTPException(
            status_code=503,
            detail={
                "type": "overloaded",
                "message": (
                    "Too many concurrent renders. Retry in a few seconds."
                ),
            },
            headers={"Retry-After": "5"},
        )

    try:
        with tempfile.TemporaryDirectory(prefix="klartex-render-") as tmp:
            # asset_dir stays None unless the request references something
            # that has to resolve out of a root of its own, so a plain render
            # resolves its inputs exactly as it does without this service in
            # front of it. A file-form font counts even with no assets sent:
            # left to the process working directory, a font file that happens
            # to sit there would be embedded although no caller supplied it.
            asset_dir: Path | None = None
            if (
                req.page_template_source is not None
                or req.header_source is not None
                or req.footer_source is not None
                or assets
                or font_files(req.data.get("page_template"))
            ):
                asset_dir = Path(tmp)
                for filename, content in assets.items():
                    (asset_dir / filename).write_bytes(content)

            pdf_bytes = klartex_render(
                req.template,
                req.data,
                asset_dir=asset_dir,
                page_template_source=req.page_template_source,
                header_source=req.header_source,
                footer_source=req.footer_source,
            )
    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "type": "validation_error",
                "message": e.message,
                "path": list(e.absolute_path),
            },
        ) from e
    except BlockValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "type": "input_error",
                "message": str(e),
                "path": e.path,
            },
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"type": "input_error", "message": str(e)},
        ) from e
    except (RuntimeError, OSError) as e:
        # OSError covers the asset writes and the tempdir itself: a full
        # disk is a server-side render failure, not caller input.
        log.exception("klartex render failed for template=%s", req.template)
        raise HTTPException(
            status_code=500,
            detail={"type": "render_error", "message": str(e)},
        ) from e
    finally:
        _render_slots.release()

    return Response(content=pdf_bytes, media_type="application/pdf")
