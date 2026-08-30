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


RECIPE_SCHEMA_NAMES = (
    "protokoll",
    "faktura",
    "kvitto",
    "resultatrakning",
    "balansrakning",
    "budgetrapport",
    "sie-exportrapport",
)


def _block_schema():
    return get_registry()["_block"].get_validation_schema()


def _with_body(page_template):
    return {
        "page_template": page_template,
        "body": [{"type": "heading", "text": "x"}],
    }


@pytest.mark.parametrize(
    "page_template",
    [
        {"header": "logo", "footer": {"variant": "standard", "company": "X", "title": True}},
        {"header": None, "footer": None},
        {"name": "clean", "footer": {"company": "X"}},
        {"header": {"variant": "letterhead", "org_name": "Föreningen", "logo": "logo.pdf"}},
        {"header": {"variant": "logo", "logo": "logo.pdf"}},
        {"footer": "standard"},
    ],
)
def test_block_schema_accepts_slot_forms(page_template):
    jsonschema.validate(_with_body(page_template), _block_schema())


@pytest.mark.parametrize(
    "page_template",
    [
        {"header": "standard"},
        {"header": {"org_name": "X"}},
        {"header": {"variant": "logo", "org_name": "X"}},
        {"footer": {"variant": "letterhead"}},
        {"footer": {"page_numbers": True}},
        {"footer": {"bogus": 1}},
        {"header": "letterhead", "bogus": 1},
    ],
)
def test_block_schema_rejects_bad_slots(page_template):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(_with_body(page_template), _block_schema())


def _strip_descriptions(node):
    """Drop every `description` key so schemas compare on structure alone."""
    if isinstance(node, dict):
        return {
            k: _strip_descriptions(v)
            for k, v in node.items()
            if k != "description"
        }
    if isinstance(node, list):
        return [_strip_descriptions(v) for v in node]
    return node


def _object_form(schema):
    return next(
        form
        for form in schema["properties"]["page_template"]["oneOf"]
        if form.get("type") == "object"
    )


@pytest.mark.parametrize("template_name", RECIPE_SCHEMA_NAMES)
@pytest.mark.parametrize("slot", ["header", "footer"])
def test_recipe_slot_definitions_match_block_engine(template_name, slot):
    """The eight schemas hand-duplicate the slot definitions; they must agree
    on structure, so a slot added on one path is not missing on the other."""
    block_slot = _object_form(
        json.loads(
            (Path(__file__).parent.parent / "klartex/schemas/block_engine.schema.json").read_text(
                encoding="utf-8"
            )
        )
    )["properties"][slot]
    recipe_slot = _object_form(
        json.loads(
            (TEMPLATES_DIR / template_name / "schema.json").read_text(encoding="utf-8")
        )
    )["properties"][slot]
    assert _strip_descriptions(recipe_slot) == _strip_descriptions(block_slot)
