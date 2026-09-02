"""The `klartex serve` compile endpoint.

The renders need xelatex on PATH; everything else runs anywhere. The whole
module is skipped without the `serve` extra, so a contributor who installed
only `.[dev]` still has a green suite — CI installs `.[dev,serve]` and fails
the run if these tests skip.
"""

import base64
import importlib.metadata
import pathlib
import re
import shutil
import subprocess
import sys
import threading

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402
from typer.testing import CliRunner  # noqa: E402

from klartex.cli import app as cli_app  # noqa: E402
from klartex.server import app as app_module  # noqa: E402
from klartex.server import render as render_module  # noqa: E402
from klartex.server.app import app  # noqa: E402

client = TestClient(app)
runner = CliRunner()

HAS_XELATEX = shutil.which("xelatex") is not None
needs_xelatex = pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")


# Typer forces Rich's terminal mode when GITHUB_ACTIONS is set, and Rich's
# highlighter then splits an option name across escape sequences
# (`\x1b[1;36m-\x1b[0m\x1b[1;36m-host\x1b[0m`), so a plain substring check
# passes locally and fails on CI. Assert against the stripped text.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def plain(text: str) -> str:
    """The visible characters of a possibly styled terminal output."""
    return _ANSI_RE.sub("", text)


def b64(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode()
    return base64.b64encode(data).decode()


def post_blocks(body_blocks, **extra):
    return client.post(
        "/render",
        json={"template": "_block", "data": {"body": body_blocks}, **extra},
    )


def post_block_error(body_blocks):
    """POST a block document expected to fail validation; return the detail."""
    r = post_blocks(body_blocks)
    assert r.status_code == 400, r.text
    return r.json()["detail"]


# --- Service surface --------------------------------------------------------


def test_health_reports_the_core_version():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    # The server ships with the core and carries its version.
    assert body["version"] == importlib.metadata.version("klartex")


def test_no_schema_is_published():
    """Internal service: nothing describes it to the outside."""
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404


# --- Environment configuration ---------------------------------------------


def test_env_positive_int_defaults_when_unset(monkeypatch):
    monkeypatch.delenv("KLARTEX_TEST_LIMIT", raising=False)
    assert render_module.env_positive_int("KLARTEX_TEST_LIMIT", 7) == 7


def test_env_positive_int_defaults_when_empty(monkeypatch):
    monkeypatch.setenv("KLARTEX_TEST_LIMIT", "")
    assert render_module.env_positive_int("KLARTEX_TEST_LIMIT", 7) == 7


def test_env_positive_int_reads_the_value(monkeypatch):
    monkeypatch.setenv("KLARTEX_TEST_LIMIT", "12")
    assert render_module.env_positive_int("KLARTEX_TEST_LIMIT", 7) == 12


@pytest.mark.parametrize("value", ["0", "-1", "two", "1.5"], ids=["zero", "negative", "word", "float"])
def test_env_positive_int_rejects_non_positive_integers(monkeypatch, value):
    """A zero cap would answer 503 to every request; fail loudly instead."""
    monkeypatch.setenv("KLARTEX_TEST_LIMIT", value)
    with pytest.raises(ValueError) as exc:
        render_module.env_positive_int("KLARTEX_TEST_LIMIT", 7)
    assert "KLARTEX_TEST_LIMIT" in str(exc.value)


def test_limits_come_from_the_environment():
    """The two documented variables back the two module constants."""
    assert render_module.MAX_CONCURRENT_RENDERS >= 1
    assert app_module.MAX_REQUEST_BYTES % (1024 * 1024) == 0


# --- Rendering --------------------------------------------------------------


@needs_xelatex
def test_render_minimal_block_doc():
    r = client.post(
        "/render",
        json={
            "template": "_block",
            "data": {
                "lang": "sv",
                "body": [
                    {"type": "heading", "text": "Test"},
                    {"type": "text", "text": "Hello world."},
                ],
            },
        },
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"


def test_render_validation_error_returns_structured_400():
    """Block validation errors carry both a message and a structured path.

    klartex.render() wraps block validation as ValueError → input_error;
    render.py recovers the block position from the message and reports it
    as `detail.path`, in the same list shape the jsonschema path uses.
    """
    detail = post_block_error([{"type": "heading"}])  # missing required `text`
    assert detail["type"] == "input_error"
    assert "text" in detail["message"]  # mentions the missing field
    assert detail["path"] == ["body", 0]


def test_render_block_error_path_points_at_the_offending_block():
    detail = post_block_error(
        [
            {"type": "heading", "text": "ok"},
            {"type": "text"},  # missing required `text`
        ]
    )
    assert detail["type"] == "input_error"
    assert detail["path"] == ["body", 1]
    assert "body[1]" in detail["message"]  # message stays readable


def test_render_block_error_path_reaches_into_the_block():
    """A field-level failure inside a block extends the path to the field."""
    detail = post_block_error([{"type": "heading", "text": 123}])
    assert detail["path"] == ["body", 0, "text"]

    detail = post_block_error([{"type": "list", "items": [{"text": 5}]}])
    assert detail["path"] == ["body", 0, "items", 0, "text"]


def test_render_block_error_path_covers_nested_blocks():
    """Blocks nested in a carrier block get their full position."""
    columns = [[{"type": "text", "text": "a"}], [{"type": "text"}]]
    detail = post_block_error([{"type": "columns", "items": columns}])
    assert detail["path"] == ["body", 0, "items", 1, 0]

    columns[1][0] = {"type": "text", "text": 123}  # wrong field type
    detail = post_block_error([{"type": "columns", "items": columns}])
    assert detail["path"] == ["body", 0, "items", 1, 0, "text"]


def test_render_unknown_block_type_carries_path():
    detail = post_block_error([{"type": "nope", "text": "x"}])
    assert detail["type"] == "input_error"
    assert detail["path"] == ["body", 0]


def test_render_unknown_block_type_cannot_forge_a_path():
    """A block type carrying its own `at body[...]` does not move the path."""
    forged = "x' at body[9]. Available: y"
    detail = post_block_error([{"type": forged, "text": "x"}])
    assert detail["path"] == ["body", 0]


def test_render_schema_validation_path_is_unchanged():
    """Both error paths report the same shape for the same position."""
    detail = post_block_error([{"text": "x"}])  # block without `type`
    assert detail["type"] == "validation_error"
    assert detail["path"] == ["body", 0]

    r = client.post("/render", json={"template": "_block", "data": {}})
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["type"] == "validation_error"
    assert detail["path"] == []


def test_render_faktura_top_level_footer_reports_its_path():
    """The invoice recipes carry their footer in the page template's footer
    slot; a payload sending a top-level `footer` gets the field named."""
    r = client.post(
        "/render",
        json={
            "template": "faktura",
            "data": {
                "invoice_number": "F-1",
                "date": "2026-08-06",
                "due_date": "2026-09-05",
                "sender": {"name": "Säljbolaget AB"},
                "recipient": {"name": "Kund AB"},
                "lines": [{"description": "Tjänst", "quantity": 1, "unit_price": 100.0}],
                "footer": {"company": "Bolaget AB"},
            },
        },
    )
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["type"] == "validation_error"
    assert detail["path"] == ["footer"]
    # The message, not just the path, tells the producer where the fields go.
    assert "page_template.footer" in detail["message"]


def test_render_faktura_without_sender_is_rejected():
    """`sender` is required on the invoice recipes — the seller's name is the
    header wordmark and the footer's company line."""
    r = client.post(
        "/render",
        json={
            "template": "faktura",
            "data": {
                "invoice_number": "F-1",
                "date": "2026-08-06",
                "due_date": "2026-09-05",
                "recipient": {"name": "Kund AB"},
                "lines": [{"description": "Tjänst", "quantity": 1, "unit_price": 100.0}],
            },
        },
    )
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["type"] == "validation_error"
    assert "sender" in detail["message"]


def test_render_block_with_empty_type_carries_path():
    """An empty `type` satisfies the top-level schema but not the core.

    It reaches `_validate_blocks`, which reports it as
    `Block at body[i] is missing 'type'` — the third message form the
    path extraction has to recognise.
    """
    detail = post_block_error(
        [{"type": "heading", "text": "ok"}, {"type": "", "text": "x"}]
    )
    assert detail["type"] == "input_error"
    assert detail["path"] == ["body", 1]
    assert "body[1]" in detail["message"]


def test_block_error_path_returns_none_for_other_errors():
    assert render_module._block_error_path(ValueError("Unknown template")) is None


def test_render_unknown_template_returns_400():
    """An error with no block position carries no `path`."""
    r = client.post("/render", json={"template": "nope", "data": {}})
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["type"] == "input_error"
    assert "path" not in detail


def test_render_failure_is_a_500_render_error(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("xelatex exploded")

    monkeypatch.setattr(render_module, "klartex_render", boom)

    r = post_blocks([{"type": "heading", "text": "x"}])
    assert r.status_code == 500
    assert r.json()["detail"]["type"] == "render_error"


# --- Request envelope -------------------------------------------------------
#
# A malformed envelope is answered inside the documented error contract:
# `400 input_error`, never FastAPI's default 422.


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"data": {"body": []}},
        {"template": "_block"},
        {"template": "_block", "data": []},
        {"template": 5, "data": {}},
        {"template": "_block", "data": {}, "assets": "not-a-dict"},
        {"template": "_block", "data": {}, "header_source": 5},
    ],
    ids=[
        "empty",
        "no-template",
        "no-data",
        "data-not-object",
        "template-not-string",
        "assets-not-object",
        "header-source-not-string",
    ],
)
def test_malformed_envelope_is_a_400_input_error(payload):
    r = client.post("/render", json=payload)
    assert r.status_code == 400, r.text
    detail = r.json()["detail"]
    assert detail["type"] == "input_error"
    assert detail["message"]


@pytest.mark.parametrize(
    "payload",
    [
        b'{"template":"\\ud800","data":{}}',
        b'{"template":"_block","data":{"body":[]},"header_source":"\\ud800"}',
        b'{"template":"_block","data":{"body":[]},"footer_source":"\\ud800"}',
        b'{"template":"_block","data":{"body":[]},"page_template_source":"\\ud800"}',
        b'{"template":"_block","data":{"body":[{"type":"text","text":"\\ud800"}]}}',
        b'{"template":"_block","data":{"\\ud800":1,"body":[]}}',
    ],
    ids=[
        "template",
        "header-source",
        "footer-source",
        "whole-page-source",
        "nested-value",
        "object-key",
    ],
)
def test_unpaired_surrogate_is_a_400_input_error(payload):
    """JSON admits `"\\ud800"`; UTF-8 does not, and the contract has no 500.

    Left to reach the .tex write or the JSON error response that quotes
    it, such a string fails as a bare `500 Internal Server Error` — a
    shape no caller of this endpoint is told to expect.
    """
    r = client.post(
        "/render", content=payload, headers={"content-type": "application/json"}
    )
    assert r.status_code == 400, r.text
    detail = r.json()["detail"]
    assert detail["type"] == "input_error"
    assert "Unicode" in detail["message"]


def test_unpaired_surrogate_is_rejected_before_a_slot_is_taken(render_slots):
    """Encodability is caller input, so it is checked before the cap."""
    for _ in range(render_module.MAX_CONCURRENT_RENDERS):
        assert render_slots.acquire(blocking=False)

    r = client.post(
        "/render",
        content=b'{"template":"_block","data":{"body":[]},"header_source":"\\ud800"}',
        headers={"content-type": "application/json"},
    )

    assert r.status_code == 400
    assert r.json()["detail"]["type"] == "input_error"


def test_invalid_json_body_is_a_400_input_error():
    r = client.post(
        "/render",
        content=b"{not json",
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["type"] == "input_error"


def test_unknown_fields_are_ignored(monkeypatch):
    """The contract is minimal, not strict."""
    monkeypatch.setattr(
        render_module, "klartex_render", lambda *a, **kw: b"%PDF-fake"
    )

    r = post_blocks(MINIMAL_BODY, surprise="ignored")
    assert r.status_code == 200


# --- Inline assets ----------------------------------------------------------
#
# The caller sends the bundle inline; the service writes it to a temporary
# directory for the duration of the call and hands that to xelatex.

# 1×1 transparent PNG — small enough to inline, real enough for graphicx.
PNG_1PX = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmM"
    "IQAAAABJRU5ErkJggg=="
)

LOGO_HEADER_SOURCE = (
    r"\fancyhead[R]{\includegraphics[height=1cm]{logo.png}}" "\n"
)

MINIMAL_BODY = [{"type": "heading", "text": "x"}]


@needs_xelatex
def test_render_with_inline_bundle_uses_the_asset():
    """A slot source referencing an inline asset compiles against it."""
    r = post_blocks(
        MINIMAL_BODY,
        header_source=LOGO_HEADER_SOURCE,
        assets={"logo.png": PNG_1PX},
    )
    assert r.status_code == 200, r.text
    assert r.content[:4] == b"%PDF"


@needs_xelatex
def test_render_with_a_footer_source():
    r = post_blocks(
        MINIMAL_BODY,
        footer_source=r"\fancyfoot[C]{\thepage}" "\n",
    )
    assert r.status_code == 200, r.text
    assert r.content[:4] == b"%PDF"


@needs_xelatex
def test_render_with_a_whole_page_source():
    """One source owns both slots, and its inline asset resolves."""
    r = post_blocks(
        MINIMAL_BODY,
        page_template_source=LOGO_HEADER_SOURCE + r"\fancyfoot[C]{\thepage}" "\n",
        assets={"logo.png": PNG_1PX},
    )
    assert r.status_code == 200, r.text
    assert r.content[:4] == b"%PDF"


@pytest.mark.parametrize("slot", ["header_source", "footer_source"])
def test_whole_page_source_with_a_slot_source_is_a_400(slot):
    """The core's ValueError surfaces through the documented contract."""
    r = post_blocks(MINIMAL_BODY, page_template_source="% w", **{slot: "% s"})
    assert r.status_code == 400, r.text
    detail = r.json()["detail"]
    assert detail["type"] == "input_error"
    assert "cannot be combined" in detail["message"]


def test_whole_page_source_is_forwarded_to_the_core(monkeypatch):
    seen: list = []

    def capture(template, data, asset_dir=None, **kwargs):
        seen.append(kwargs)
        return b"%PDF-fake"

    monkeypatch.setattr(render_module, "klartex_render", capture)

    r = post_blocks(MINIMAL_BODY, page_template_source="% whole page")
    assert r.status_code == 200
    assert seen[0]["page_template_source"] == "% whole page"


@needs_xelatex
def test_render_bundle_without_the_asset_fails():
    """The asset really comes from the request, not from the container."""
    r = post_blocks(MINIMAL_BODY, header_source=LOGO_HEADER_SOURCE)
    assert r.status_code == 500
    assert r.json()["detail"]["type"] == "render_error"


def test_assets_do_not_outlive_the_request(monkeypatch):
    """The temporary directory is gone once the response is written."""
    seen: list = []

    def capture(template, data, asset_dir=None, **kwargs):
        seen.append(asset_dir)
        assert (asset_dir / "logo.png").read_bytes()
        return b"%PDF-fake"

    monkeypatch.setattr(render_module, "klartex_render", capture)

    r = post_blocks(MINIMAL_BODY, assets={"logo.png": PNG_1PX})
    assert r.status_code == 200
    assert len(seen) == 1
    assert not seen[0].exists()


def test_render_without_a_bundle_passes_no_asset_dir(monkeypatch):
    """A plain render resolves its inputs exactly as the core does alone."""
    seen: list = []

    def capture(template, data, asset_dir=None, **kwargs):
        seen.append(asset_dir)
        return b"%PDF-fake"

    monkeypatch.setattr(render_module, "klartex_render", capture)

    assert post_blocks(MINIMAL_BODY).status_code == 200
    assert seen == [None]


def test_slot_sources_reach_the_core(monkeypatch):
    """Both slots are forwarded under the core's own keyword names."""
    seen: list = []

    def capture(template, data, asset_dir=None, **kwargs):
        seen.append(kwargs)
        return b"%PDF-fake"

    monkeypatch.setattr(render_module, "klartex_render", capture)

    r = post_blocks(MINIMAL_BODY, header_source="H", footer_source="F")
    assert r.status_code == 200
    assert seen[0]["header_source"] == "H"
    assert seen[0]["footer_source"] == "F"


@pytest.mark.parametrize(
    "filename",
    ["../escape.png", "sub/logo.png", ".hidden", "", "a" * 200],
    ids=["parent", "subdir", "dotfile", "empty", "too-long"],
)
def test_invalid_asset_filename_is_rejected(filename):
    """No caller can write outside the per-request temporary directory."""
    r = post_blocks(MINIMAL_BODY, assets={filename: PNG_1PX})
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["type"] == "input_error"
    assert "asset filename" in detail["message"]
    # The hint quotes the rule that was applied, length cap included — a
    # name rejected for being too long must not get a hint it satisfies.
    assert render_module.ASSET_NAME_RE.pattern in detail["message"]


def test_asset_write_failure_is_a_500_render_error(monkeypatch):
    """A full disk is a server-side failure, not caller input."""

    def boom(self, *args, **kwargs):
        raise OSError("No space left on device")

    monkeypatch.setattr("pathlib.Path.write_bytes", boom)

    r = post_blocks(MINIMAL_BODY, assets={"logo.png": PNG_1PX})
    assert r.status_code == 500
    assert r.json()["detail"]["type"] == "render_error"


def test_invalid_base64_asset_is_rejected():
    r = post_blocks(MINIMAL_BODY, assets={"logo.png": "not-base64!!!"})
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["type"] == "input_error"
    assert "base64" in detail["message"]


def test_oversized_asset_is_rejected():
    oversized = b64(b"x" * (render_module.MAX_ASSET_BYTES + 1))
    r = post_blocks(MINIMAL_BODY, assets={"logo.png": oversized})
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["type"] == "input_error"
    assert "exceeds limit" in detail["message"]


# --- Font files as assets ---------------------------------------------------

FONT_FILE = "lmroman10-regular.otf"


def post_font_document(font, **extra):
    """POST a block document whose page_template carries `font`."""
    return client.post(
        "/render",
        json={
            "template": "_block",
            "data": {
                "body": [{"type": "text", "text": "Text med **fet** stil."}],
                "page_template": {"font": font},
            },
            **extra,
        },
    )


@needs_xelatex
def test_font_file_rides_the_assets_map():
    """A file-form font compiles from a face sent inline — the designed path
    for a font the render environment does not install."""
    located = subprocess.run(
        ["kpsewhich", FONT_FILE], capture_output=True, text=True
    ).stdout.strip()
    assert located, f"kpsewhich could not locate {FONT_FILE}"
    face = base64.b64encode(pathlib.Path(located).read_bytes()).decode()

    r = post_font_document({"file": FONT_FILE}, assets={FONT_FILE: face})
    assert r.status_code == 200, r.text
    assert r.content[:4] == b"%PDF"


def test_font_file_absent_from_the_assets_is_a_structured_400():
    """The core's preflight ValueError reaches the caller as input_error,
    naming the file — no xelatex needed to say the font never arrived."""
    r = post_font_document({"file": FONT_FILE}, assets={"logo.png": PNG_1PX})
    assert r.status_code == 400, r.text
    detail = r.json()["detail"]
    assert detail["type"] == "input_error"
    assert FONT_FILE in detail["message"]


def test_font_file_never_comes_from_the_server_working_directory(tmp_path, monkeypatch):
    """A font is only ever what the request sent.

    A file-form font with no assets beside it would otherwise resolve against
    the process working directory, so a font file that happens to sit there
    would be embedded although no caller supplied it. The endpoint gives the
    request a root of its own instead, and the face is simply missing from it.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / FONT_FILE).write_bytes(b"a font file the caller never sent")

    r = post_font_document({"file": FONT_FILE})
    assert r.status_code == 400, r.text
    detail = r.json()["detail"]
    assert detail["type"] == "input_error"
    assert FONT_FILE in detail["message"]


def test_font_file_name_the_schema_rejects_never_reaches_the_assets_rule():
    """The schema's font-file pattern is stricter than ASSET_NAME_RE, so a
    name the endpoint would accept as an asset can still be a bad font name."""
    bad = "lmroman10_regular.otf"
    assert render_module.ASSET_NAME_RE.match(bad)
    r = post_font_document({"file": bad}, assets={bad: PNG_1PX})
    assert r.status_code == 400, r.text
    assert r.json()["detail"]["type"] == "validation_error"


def test_too_many_assets_is_rejected():
    assets = {
        f"f{i}.png": PNG_1PX for i in range(render_module.MAX_ASSETS + 1)
    }
    r = post_blocks(MINIMAL_BODY, assets=assets)
    assert r.status_code == 400
    assert r.json()["detail"]["type"] == "input_error"


@pytest.mark.parametrize(
    "field", ["header_source", "footer_source", "page_template_source"]
)
def test_oversized_slot_source_is_rejected(field):
    source = "%" * (render_module.MAX_TEMPLATE_BYTES + 1)
    r = post_blocks(MINIMAL_BODY, **{field: source})
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["type"] == "input_error"
    assert field in detail["message"]


def test_oversized_request_is_rejected_before_the_body_is_read(monkeypatch):
    """The Content-Length header alone decides; the body is never parsed."""
    monkeypatch.setattr(app_module, "MAX_REQUEST_BYTES", 10)

    r = post_blocks(MINIMAL_BODY)

    assert r.status_code == 413
    assert r.json()["detail"]["type"] == "payload_too_large"


# --- Concurrency cap -------------------------------------------------------
#
# The tests below never invoke xelatex: klartex_render is replaced by a fake,
# so they exercise the semaphore alone and run anywhere.

MINIMAL_REQUEST = {"template": "_block", "data": {"body": MINIMAL_BODY}}


@pytest.fixture
def render_slots(monkeypatch):
    """Give each test its own semaphore, so a failure cannot leak slots."""
    slots = threading.BoundedSemaphore(render_module.MAX_CONCURRENT_RENDERS)
    monkeypatch.setattr(render_module, "_render_slots", slots)
    return slots


def assert_all_slots_free(slots):
    """Every slot is free — and no more than MAX_CONCURRENT_RENDERS exist."""
    acquired = [
        slots.acquire(blocking=False)
        for _ in range(render_module.MAX_CONCURRENT_RENDERS)
    ]
    extra = slots.acquire(blocking=False)
    for ok in acquired:
        if ok:
            slots.release()
    if extra:
        slots.release()
    assert all(acquired), "a render slot leaked"
    assert not extra, "more slots than MAX_CONCURRENT_RENDERS"


def test_render_returns_503_when_all_slots_taken(render_slots):
    for _ in range(render_module.MAX_CONCURRENT_RENDERS):
        assert render_slots.acquire(blocking=False)

    r = client.post("/render", json=MINIMAL_REQUEST)

    assert r.status_code == 503
    assert r.headers["Retry-After"] == "5"
    assert r.json()["detail"]["type"] == "overloaded"


def test_render_releases_slot_after_success(render_slots, monkeypatch):
    monkeypatch.setattr(
        render_module, "klartex_render", lambda *a, **kw: b"%PDF-fake"
    )

    r = client.post("/render", json=MINIMAL_REQUEST)

    assert r.status_code == 200
    assert_all_slots_free(render_slots)


def test_render_releases_slot_after_failure(render_slots, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("xelatex exploded")

    monkeypatch.setattr(render_module, "klartex_render", boom)

    r = client.post("/render", json=MINIMAL_REQUEST)

    assert r.status_code == 500
    assert r.json()["detail"]["type"] == "render_error"
    assert_all_slots_free(render_slots)


def test_invalid_asset_does_not_take_a_slot(render_slots):
    """Input validation happens before the cap, so it cannot be starved."""
    for _ in range(render_module.MAX_CONCURRENT_RENDERS):
        assert render_slots.acquire(blocking=False)

    r = post_blocks(MINIMAL_BODY, assets={"../escape.png": PNG_1PX})

    assert r.status_code == 400


def test_render_third_concurrent_request_gets_503(render_slots, monkeypatch):
    """Two renders occupy both slots; a third is rejected immediately."""
    in_render = threading.Semaphore(0)
    release = threading.Event()

    def blocking_render(*args, **kwargs):
        in_render.release()
        assert release.wait(timeout=10), "render fake was never released"
        return b"%PDF-fake"

    monkeypatch.setattr(render_module, "klartex_render", blocking_render)

    results: dict[int, int] = {}

    def run(index):
        results[index] = client.post("/render", json=MINIMAL_REQUEST).status_code

    threads = [
        threading.Thread(target=run, args=(i, ), daemon=True)
        for i in range(render_module.MAX_CONCURRENT_RENDERS)
    ]
    for t in threads:
        t.start()
    try:
        for _ in threads:
            assert in_render.acquire(timeout=10), "renders never started"

        r = client.post("/render", json=MINIMAL_REQUEST)
        assert r.status_code == 503
        assert r.json()["detail"]["type"] == "overloaded"
    finally:
        release.set()
        for t in threads:
            t.join(timeout=10)

    assert not any(t.is_alive() for t in threads)
    assert sorted(results.values()) == [200] * len(threads)
    assert_all_slots_free(render_slots)


# --- CLI surface ------------------------------------------------------------


def test_serve_help_lists_the_options():
    result = runner.invoke(cli_app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "--host" in plain(result.output)
    assert "--port" in plain(result.output)


def test_serve_without_the_extra_explains_how_to_install_it(monkeypatch):
    """A None in sys.modules makes the import fail exactly as a missing one."""
    monkeypatch.setitem(sys.modules, "uvicorn", None)

    result = runner.invoke(cli_app, ["serve"])

    assert result.exit_code == 1
    assert "klartex[serve]" in plain(result.output)


def test_serve_propagates_an_unrelated_import_error(monkeypatch):
    """Only the extra's own modules produce the install hint."""
    monkeypatch.setitem(sys.modules, "klartex.server.app", None)

    result = runner.invoke(cli_app, ["serve"])

    assert result.exit_code != 0
    assert "klartex[serve]" not in plain(result.output)
