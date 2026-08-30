"""Tests for agent-friendly CLI features: blocks, example, schema oneOf."""

import json
from pathlib import Path

import jsonschema
import pytest

from klartex.renderer import get_registry
from klartex.components import _COMPONENTS


def test_block_schema_has_oneof():
    registry = get_registry()
    schema = registry["_block"].schema
    items = schema["properties"]["body"]["items"]
    assert "oneOf" in items, "body.items should have oneOf discriminated union"


def test_block_schema_oneof_contains_all_block_types():
    registry = get_registry()
    schema = registry["_block"].schema
    one_of = schema["properties"]["body"]["items"]["oneOf"]

    # Collect type values from oneOf entries (const or enum)
    schema_types = set()
    for entry in one_of:
        type_prop = entry.get("properties", {}).get("type", {})
        if "const" in type_prop:
            schema_types.add(type_prop["const"])
        elif "enum" in type_prop:
            schema_types.update(type_prop["enum"])

    # Collect expected block types (those with block_schema_path)
    expected = {name for name, spec in _COMPONENTS.items() if spec.block_schema_path}

    assert schema_types == expected


def test_block_schema_oneof_entries_are_valid():
    registry = get_registry()
    one_of = registry["_block"].schema["properties"]["body"]["items"]["oneOf"]
    for entry in one_of:
        assert "type" in entry.get("properties", {}), f"Missing type property in {entry.get('title')}"
        assert "required" in entry, f"Missing required in {entry.get('title')}"


def test_block_example_is_valid_json():
    from pathlib import Path

    example_path = Path(__file__).resolve().parent.parent / "klartex" / "schemas" / "block_engine.example.json"
    assert example_path.exists(), "block_engine.example.json should exist"
    data = json.loads(example_path.read_text())
    assert "body" in data
    assert len(data["body"]) > 0


def test_block_example_validates_against_schema():
    from pathlib import Path

    registry = get_registry()
    schema = registry["_block"].schema
    example_path = Path(__file__).resolve().parent.parent / "klartex" / "schemas" / "block_engine.example.json"
    data = json.loads(example_path.read_text())
    jsonschema.validate(data, schema)


def test_block_example_covers_all_block_types():
    from pathlib import Path

    example_path = Path(__file__).resolve().parent.parent / "klartex" / "schemas" / "block_engine.example.json"
    data = json.loads(example_path.read_text())

    example_types = {block["type"] for block in data["body"]}
    expected = {name for name, spec in _COMPONENTS.items() if spec.block_schema_path}

    missing = expected - example_types
    assert not missing, f"Example is missing block types: {missing}"


def test_block_schema_exposes_slot_variants():
    """`klartex schema _block` is how an agent discovers the surface, so the
    slot variant names must be in the schema it prints."""
    registry = get_registry()
    page_template = registry["_block"].schema["properties"]["page_template"]
    printed = json.dumps(page_template, ensure_ascii=False)
    assert "letterhead" in printed
    assert "standard" in printed


def test_block_example_uses_the_slot_form():
    """The canonical example demonstrates structured header content, which is
    the whole point of the slot model."""
    example_path = (
        Path(__file__).resolve().parent.parent
        / "klartex"
        / "schemas"
        / "block_engine.example.json"
    )
    data = json.loads(example_path.read_text())
    assert data["page_template"]["header"]["variant"] == "letterhead"
    assert data["page_template"]["header"]["org_name"]
