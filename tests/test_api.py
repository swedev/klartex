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
    assert "avtal" in names


def test_list_templates_includes_engines():
    """Templates should include engine information."""
    resp = client.get("/templates")
    assert resp.status_code == 200
    templates = {t["name"]: t for t in resp.json()}

    # protokoll has both engines
    assert "legacy" in templates["protokoll"]["engines"]
    assert "recipe" in templates["protokoll"]["engines"]

    # faktura has only legacy
    assert templates["faktura"]["engines"] == ["legacy"]


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


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
def test_render_with_engine_recipe():
    """API should support engine='recipe'."""
    data = json.loads((FIXTURES / "protokoll.json").read_text())
    resp = client.post("/render", json={"template": "protokoll", "data": data, "engine": "recipe"})
    assert resp.status_code == 200
    assert resp.content[:5] == b"%PDF-"


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
def test_render_with_engine_legacy():
    """API should support engine='legacy'."""
    data = json.loads((FIXTURES / "protokoll.json").read_text())
    resp = client.post("/render", json={"template": "protokoll", "data": data, "engine": "legacy"})
    assert resp.status_code == 200
    assert resp.content[:5] == b"%PDF-"


def test_render_unknown_template():
    resp = client.post("/render", json={"template": "nonexistent", "data": {}})
    assert resp.status_code == 400
