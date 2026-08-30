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
    assert "kvitto" in registry
    assert "resultatrakning" in registry
    assert "balansrakning" in registry
    assert "budgetrapport" in registry
    assert "sie-exportrapport" in registry
    assert "_block" in registry


@pytest.mark.parametrize("template_name", [
    "protokoll", "faktura", "kvitto",
    "resultatrakning", "balansrakning", "budgetrapport", "sie-exportrapport",
])
def test_fixture_validates(template_name):
    registry = get_registry()
    fixture_path = FIXTURES / f"{template_name}.json"
    data = json.loads(fixture_path.read_text())
    jsonschema.validate(data, registry[template_name].schema)


def test_protokoll_missing_required():
    registry = get_registry()
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({}, registry["protokoll"].schema)


def test_protokoll_schema_documents_sub_items():
    """The protokoll recipe renders agenda_items[].subItems, so the schema
    `klartex schema protokoll` shows must document the field and its three
    promises, and the shipped example must validate against it (#70)."""
    registry = get_registry()
    schema = registry["protokoll"].schema
    sub_items = schema["properties"]["agenda_items"]["items"]["properties"]["subItems"]
    assert sub_items["type"] == "array"
    assert sub_items["items"] == {"type": "string"}
    description = sub_items["description"]
    assert "numrerade decimalt" in description
    assert "diskussion och beslut" in description
    assert "Inline-markup" in description

    example_path = (
        Path(__file__).resolve().parent.parent
        / "klartex" / "templates" / "protokoll" / "example.json"
    )
    jsonschema.validate(json.loads(example_path.read_text()), schema)


def test_protokoll_sub_items_must_be_strings():
    """Typing subItems rejects the malformed shapes that pass as unknown keys
    today and then misrender in the macro (#70)."""
    registry = get_registry()
    for bad in ([123], "text"):
        data = json.loads((FIXTURES / "protokoll.json").read_text())
        data["agenda_items"][0]["subItems"] = bad
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, registry["protokoll"].schema)


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
