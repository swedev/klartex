"""Tests for JSON Schema validation and template discovery."""

import json
from pathlib import Path

import jsonschema
import pytest

from klartex.renderer import get_registry, TEMPLATES_DIR

FIXTURES = Path(__file__).parent / "fixtures"


def test_discover_all_templates():
    registry = get_registry()
    assert "protokoll" in registry
    assert "faktura" in registry
    assert "avtal" in registry


@pytest.mark.parametrize("template_name", ["protokoll", "faktura", "avtal"])
def test_fixture_validates(template_name):
    registry = get_registry()
    fixture_path = FIXTURES / f"{template_name}.json"
    data = json.loads(fixture_path.read_text())
    jsonschema.validate(data, registry[template_name].schema)


def test_protokoll_missing_required():
    registry = get_registry()
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({}, registry["protokoll"].schema)


def test_faktura_missing_lines():
    registry = get_registry()
    data = {
        "invoice_number": "1",
        "date": "2026-01-01",
        "due_date": "2026-02-01",
        "recipient": {"name": "Test"},
        "lines": [],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(data, registry["faktura"].schema)
