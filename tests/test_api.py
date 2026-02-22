"""Tests for the FastAPI HTTP API."""

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from klartex.main import app

FIXTURES = Path(__file__).parent / "fixtures"
HAS_XELATEX = shutil.which("xelatex") is not None

client = TestClient(app)


def test_list_templates():
    resp = client.get("/templates")
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()]
    assert "protokoll" in names
    assert "faktura" in names
    assert "_block" in names


def test_list_templates_includes_type():
    """Templates should include type information."""
    resp = client.get("/templates")
    assert resp.status_code == 200
    templates = {t["name"]: t for t in resp.json()}

    assert templates["protokoll"]["type"] == "recipe"
    assert templates["faktura"]["type"] == "recipe"
    assert templates["_block"]["type"] == "block-engine"


def test_get_schema():
    resp = client.get("/templates/protokoll/schema")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["title"] == "Protokoll"


def test_get_schema_not_found():
    resp = client.get("/templates/nonexistent/schema")
    assert resp.status_code == 404


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
def test_render_endpoint():
    data = json.loads((FIXTURES / "protokoll.json").read_text())
    resp = client.post("/render", json={"template": "protokoll", "data": data})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:5] == b"%PDF-"


def test_render_unknown_template():
    resp = client.post("/render", json={"template": "nonexistent", "data": {}})
    assert resp.status_code == 400


# --- Page template API tests ---


def test_list_page_templates():
    resp = client.get("/page-templates")
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()]
    assert "formal" in names
    assert "clean" in names
    assert "none" in names


def test_page_templates_have_descriptions():
    resp = client.get("/page-templates")
    for t in resp.json():
        assert "description" in t
        assert "defaults" in t


# --- Block registry API tests ---


def test_list_blocks():
    resp = client.get("/blocks")
    assert resp.status_code == 200
    names = [b["name"] for b in resp.json()]
    assert "heading" in names
    assert "clause" in names
    assert "signatures" in names
    assert "text" in names
    assert "parties" in names
    assert "title_page" in names


def test_get_block_schema():
    resp = client.get("/blocks/heading/schema")
    assert resp.status_code == 200
    schema = resp.json()
    assert schema["title"] == "Heading Block"
    assert "text" in schema["properties"]


def test_get_block_schema_clause():
    resp = client.get("/blocks/clause/schema")
    assert resp.status_code == 200
    schema = resp.json()
    assert "items" in schema["properties"]


def test_get_block_schema_not_found():
    resp = client.get("/blocks/nonexistent/schema")
    assert resp.status_code == 404


# --- Block engine in templates list ---


def test_block_engine_in_templates():
    resp = client.get("/templates")
    assert resp.status_code == 200
    templates = {t["name"]: t for t in resp.json()}
    assert "_block" in templates
    assert templates["_block"]["type"] == "block-engine"


def test_block_engine_schema():
    resp = client.get("/templates/_block/schema")
    assert resp.status_code == 200
    schema = resp.json()
    assert "body" in schema["properties"]


# --- Block engine render via API ---


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
def test_render_block_engine():
    data = {
        "page_template": "formal",
        "body": [
            {"type": "heading", "text": "API Test"},
            {"type": "text", "text": "Rendered via the block engine API."},
        ],
    }
    resp = client.post("/render", json={"template": "_block", "data": data})
    assert resp.status_code == 200
    assert resp.content[:5] == b"%PDF-"
