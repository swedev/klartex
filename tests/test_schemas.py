"""Tests for JSON Schema validation and template discovery."""

import json
from pathlib import Path

import jsonschema
import pytest

from klartex.page_templates import DIMENSION_PATTERN, GUARANTEED_FONTS
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


_MINIMAL_RECIPE_PAYLOAD = {
    "faktura": {
        "invoice_number": "F-1",
        "date": "2026-08-06",
        "due_date": "2026-09-05",
        "recipient": {"name": "Kund AB"},
        "lines": [{"description": "Tjänst", "quantity": 1, "unit_price": 100.0}],
    },
    "kvitto": {
        "receipt_number": "K-1",
        "date": "2026-08-06",
        "total_amount": 100,
        "items": [{"description": "Avgift", "amount": 100}],
    },
}


@pytest.mark.parametrize("template_name", ["faktura", "kvitto"])
def test_top_level_footer_is_rejected(template_name):
    """The footer slot is the only footer surface on the two invoice-shaped
    recipes. A payload sending a top-level `footer` fails validation at that
    path rather than rendering a document without its payment details.

    The guidance lives in the rejecting subschema's `description`, which
    jsonschema interpolates into the message — so the producer is told where
    the fields belong, not just that the value is disallowed. This test is
    what keeps that true if the library's message format changes.
    """
    registry = get_registry()
    data = dict(_MINIMAL_RECIPE_PAYLOAD[template_name])
    jsonschema.validate(data, registry[template_name].schema)

    data["footer"] = {"company": "Bolaget AB", "bankgiro": "1234-5678"}
    with pytest.raises(jsonschema.ValidationError) as excinfo:
        jsonschema.validate(data, registry[template_name].schema)
    assert list(excinfo.value.absolute_path) == ["footer"]
    assert "page_template.footer" in excinfo.value.message
    assert "columns" in excinfo.value.message


@pytest.mark.parametrize("template_name", ["faktura", "kvitto"])
def test_top_level_footer_is_rejected_in_every_shape(template_name):
    """`footer` is not a property of these templates at all — no value shape
    slips through as an unconstrained extra key."""
    registry = get_registry()
    for value in (None, "Bolaget AB", {}, [], {"company": "Bolaget AB"}):
        data = dict(_MINIMAL_RECIPE_PAYLOAD[template_name])
        data["footer"] = value
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, registry[template_name].schema)


@pytest.mark.parametrize("template_name", ["faktura", "kvitto"])
def test_recipe_example_validates(template_name):
    """The shipped example is what `klartex example <name>` hands an agent —
    it must validate against the schema `klartex schema <name>` shows."""
    registry = get_registry()
    example_path = TEMPLATES_DIR / template_name / "example.json"
    jsonschema.validate(json.loads(example_path.read_text()), registry[template_name].schema)


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
    assert "decimal sub-numbering" in description
    assert "discussion and decision" in description
    assert "Inline markup" in description

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
        {"header": "logo", "footer": {"variant": "pagenumber", "title": True}},
        {"header": "logo", "footer": "columns"},
        {"header": None, "footer": None},
        {"header": "logo", "footer": {"variant": "columns", "fields": {"company": "X"}}},
        {"header": {"variant": "letterhead", "fields": {"org_name": "Föreningen", "logo": "logo.pdf"}}},
        {"header": {"variant": "logo", "fields": {"logo": "logo.pdf"}}},
        {"header": {"variant": "logo"}},
        {"footer": "pagenumber"},
        {"margins": None},
        {"margins": {}},
        {"margins": {"left": "2cm"}},
        {"margins": {"top": "3.4cm", "bottom": "2cm", "left": "25mm", "right": "1in"}},
    ],
)
def test_block_schema_accepts_slot_forms(page_template):
    jsonschema.validate(_with_body(page_template), _block_schema())


@pytest.mark.parametrize(
    "page_template",
    [
        {"header": "standard"},
        {"header": {"org_name": "X"}},
        {"header": {"variant": "logo", "fields": {"org_name": "X"}}},
        {"header": {"variant": "letterhead", "org_name": "X"}},
        {"footer": {"variant": "letterhead"}},
        {"footer": {"variant": "pagenumber", "page_numbers": True}},
        {"footer": {"variant": "pagenumber", "bogus": 1}},
        {"footer": {"variant": "columns", "company": "X"}},
        {"footer": {"variant": "columns", "fields": {"bogus": 1}}},
        {"footer": {"variant": "columns", "title": True}},
        {"footer": {"variant": "pagenumber", "fields": {"company": "X"}}},
        {"footer": {"title": True}},
        {"footer": {"fields": {"company": "X"}}},
        {"header": "letterhead", "bogus": 1},
        {"margins": "2cm"},
        {"margins": {"inner": "2cm"}},
        {"margins": {"top": "2,5cm"}},
        {"margins": {"top": "2.5"}},
        {"margins": {"top": "2.5em"}},
        {"margins": {"top": 2.5}},
        # The schema must anchor at the absolute end too — Python's `$`
        # matches before a final newline, and jsonschema uses Python's re.
        {"margins": {"top": "2.5cm\n"}},
        {"margins": {"left": "2cm\n"}},
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


@pytest.mark.parametrize("template_name", RECIPE_SCHEMA_NAMES + ("_block",))
def test_every_template_schema_carries_the_generated_page_template(template_name):
    """The page_template subtree is generated from the slot model and injected
    by the registry; the schema files only hold a placeholder."""
    schema = get_registry()[template_name].schema
    pt = schema["properties"]["page_template"]
    assert "$comment" not in pt
    assert pt["properties"]["header"]["oneOf"][1]["enum"] == ["letterhead", "logo"]
    assert pt["properties"]["footer"]["oneOf"][1]["enum"] == ["pagenumber", "columns"]
    assert pt["properties"]["diff_style"]["enum"] == ["color", "underline"]
    margins = pt["properties"]["margins"]
    assert margins["type"] == ["object", "null"]
    assert margins["additionalProperties"] is False
    assert set(margins["properties"]) == {"top", "bottom", "left", "right"}
    assert all(v["pattern"] == DIMENSION_PATTERN for v in margins["properties"].values())


def test_schema_files_hold_only_the_placeholder():
    for path in [Path(__file__).parent.parent / "klartex/schemas/block_engine.schema.json"] + [
        TEMPLATES_DIR / name / "schema.json" for name in RECIPE_SCHEMA_NAMES
    ]:
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert set(raw["properties"]["page_template"]) == {"$comment"}, path


@pytest.mark.parametrize(
    "page_template",
    [
        {"header": {"variant": "letterhead", "fields": {"email": "a@b.se"}}},
        {"header": {"variant": "letterhead", "fields": {"address": "Storgatan 1"}}},
        {"header": {"variant": "letterhead"}},
        {"header": {"variant": "letterhead", "fields": {"org_name": "X", "logo": "my_logo.pdf"}}},
        {"header": {"variant": "letterhead", "fields": {"org_name": "X", "logo": "a&b.pdf"}}},
        {"header": {"variant": "logo", "fields": {"logo": "my_logo.pdf"}}},
    ],
)
def test_block_schema_rejects_unrenderable_headers(page_template):
    """A letterhead needs its org name, and a logo filename that escape_data()
    would rewrite must fail validation rather than xelatex."""
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(_with_body(page_template), _block_schema())


@pytest.mark.parametrize(
    "logo",
    ["logo.pdf", "../delat/logo.pdf", "branding/logo.pdf", "logotyp-åäö.pdf"],
)
def test_block_schema_accepts_safe_logo_names(logo):
    """The pattern must not reject ordinary paths or non-ASCII names, which
    need no escaping."""
    jsonschema.validate(
        _with_body({"header": {"variant": "letterhead", "fields": {"org_name": "X", "logo": logo}}}),
        _block_schema(),
    )


@pytest.mark.parametrize("template_name", ["faktura", "kvitto"])
def test_logo_height_schema_default(template_name):
    """The documented logo_height default matches the renderer's fallback.

    The runtime fallback lives in `_recipe_base.tex.jinja`; nothing else
    verifies that the schema the agent reads says the same thing.
    """
    schema = json.loads((TEMPLATES_DIR / template_name / "schema.json").read_text())
    assert schema["properties"]["logo_height"]["default"] == "1cm"


@pytest.mark.parametrize("setting", ["font", "header_font"])
def test_block_schema_documents_the_guaranteed_fonts(setting):
    """The discovery surface names the render environment's font guarantee.

    An agent picks a font from `klartex schema _block` alone, so every family
    the base image is built to carry has to appear in the description — and
    conversely, nothing may be promised there that the image is not checked
    for (docker/Dockerfile.base fails the build on a missing family).
    """
    settings = _block_schema()["properties"]["page_template"]["properties"]
    assert "ghcr.io/swedev/klartex-base" in settings["font"]["description"]
    description = settings[setting]["description"]
    if setting == "font":
        for family in GUARANTEED_FONTS:
            assert family in description, family
    else:
        assert "guaranteed families are the same as for font" in description


def test_dockerfile_font_list_matches_the_constant():
    """docker/guaranteed-fonts.txt is the Dockerfile's copy of the constant.

    The image build cannot import klartex — it verifies the fonts before the
    package is installed — so the list travels as a file. This test is what
    keeps the copy honest.
    """
    repo_root = Path(__file__).resolve().parent.parent
    lines = (repo_root / "docker" / "guaranteed-fonts.txt").read_text(
        encoding="utf-8"
    ).splitlines()
    families = tuple(
        line.strip()
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    )
    assert families == GUARANTEED_FONTS
