"""FastAPI application: the compile endpoint and a health probe.

Two endpoints — `POST /render` (JSON in, PDF out) and `GET /health`. No
schema is published and the routes carry no prefix: this is an internal
compile layer, not a public API.

Configuration is environment-only:

* `KLARTEX_MAX_CONCURRENT` — concurrent xelatex runs (default 2)
* `KLARTEX_MAX_BODY_MB` — largest request body looked at (default 80)

`KLARTEX_MAX_BODY_MB` is a *declared-size* limit: the check reads the
Content-Length header and answers 413 before a byte of the body is read,
so a chunked or header-less request passes it. Capping actually received
bytes is the job of the ASGI server or the proxy in front of it.
"""

import importlib.metadata
import json

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from klartex.server.render import env_positive_int
from klartex.server.render import router as render_router

__version__ = importlib.metadata.version("klartex")

# Largest request the service will look at. The biggest bundle a caller can
# send is 10 assets of 5 MB plus two 1 MB slot sources; base64 inflates that
# to ~68 MB, and the document data comes on top.
MAX_REQUEST_BYTES = env_positive_int("KLARTEX_MAX_BODY_MB", 80) * 1024 * 1024

app = FastAPI(
    title="klartex render service",
    description="Stateless wrapper around klartex.render().",
    version=__version__,
    docs_url=None,
    openapi_url=None,
    redoc_url=None,
)


def _input_error_response(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"detail": {"type": "input_error", "message": message}},
    )


def _describe(errors: list[dict]) -> str:
    """Render pydantic's error list as one line the caller can act on."""
    parts = []
    for err in errors:
        # Drop the leading "body" element: every location is inside the body.
        loc = [str(p) for p in err.get("loc", ()) if p != "body"]
        where = ".".join(loc)
        msg = err.get("msg", "invalid value")
        parts.append(f"{where}: {msg}" if where else msg)
    return "; ".join(parts) or "malformed request body"


@app.exception_handler(RequestValidationError)
async def _envelope_error(request: Request, exc: RequestValidationError):
    """Answer a malformed envelope inside the documented error contract.

    FastAPI's default is a 422 with its own body shape, which is outside
    the four documented error types; a caller then has to special-case it.
    """
    return _input_error_response(_describe(exc.errors()))


@app.exception_handler(json.JSONDecodeError)
async def _malformed_json(request: Request, exc: json.JSONDecodeError):
    return _input_error_response(f"invalid JSON body: {exc}")


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared = int(content_length)
        except ValueError:
            declared = None
        if declared is not None and declared > MAX_REQUEST_BYTES:
            return JSONResponse(
                status_code=413,
                content={
                    "detail": {
                        "type": "payload_too_large",
                        "message": (
                            f"Request body of {declared} bytes exceeds the "
                            f"limit of {MAX_REQUEST_BYTES} bytes."
                        ),
                    }
                },
            )
    return await call_next(request)


@app.get("/health")
def health() -> dict:
    """Liveness probe — used by the container healthcheck and by deploys.

    `version` is the installed klartex version: the service ships with the
    core and carries its version, so a caller comparing renderer versions
    reads it here.
    """
    return {"status": "ok", "version": __version__}


app.include_router(render_router)
