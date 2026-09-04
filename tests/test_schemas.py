"""Tests for JSON Schema validation and template discovery."""

import json
from pathlib import Path

import jsonschema
import pytest

from klartex.page_templates import DIMENSION_PATTERN, GUARANTEED_FONTS, list_slot_variants
from klartex.renderer import get_registry, TEMPLATES_DIR

FIXTURES = Path(__file__).parent / "fixtures"

RECIPE_SCHEMA_NAMES = (
    "protokoll",
    "faktura",
    "kvitto",
    "resultatrakning",
    "balansrakning",
    "budgetrapport",
    "sie-exportrapport",
)


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
    # The tests below parametrize over the static tuple; discovery is what the
    # renderer serves. They must name the same recipes.
    assert {
        name for name, info in registry.items() if not info.is_block_engine
    } == set(RECIPE_SCHEMA_NAMES)


@pytest.mark.parametrize("template_name", RECIPE_SCHEMA_NAMES)
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
        "sender": {"name": "Säljbolaget AB"},
        "recipient": {"name": "Kund AB"},
        "lines": [{"description": "Tjänst", "quantity": 1, "unit_price": 100.0}],
    },
    "kvitto": {
        "receipt_number": "K-1",
        "date": "2026-08-06",
        "total_amount": 100,
        "sender": {"name": "Säljbolaget AB"},
        "items": [{"description": "Avgift", "amount": 100}],
    },
}


@pytest.mark.parametrize("template_name", ["faktura", "kvitto"])
def test_sender_is_required(template_name):
    """A document without a seller is not an invoice or a receipt: the name
    is the header wordmark and the footer's company line, so the schema names
    the missing property rather than rendering a blank header."""
    registry = get_registry()
    data = dict(_MINIMAL_RECIPE_PAYLOAD[template_name])
    del data["sender"]
    with pytest.raises(jsonschema.ValidationError) as excinfo:
        jsonschema.validate(data, registry[template_name].schema)
    assert "sender" in excinfo.value.message


@pytest.mark.parametrize("template_name", ["faktura", "kvitto"])
@pytest.mark.parametrize("sender", [{}, {"name": ""}, {"name": "   "}])
def test_sender_name_must_carry_a_non_whitespace_character(template_name, sender):
    """`required` alone would admit a blank name — the state the wordmark and
    the footer's company line are built on."""
    registry = get_registry()
    data = dict(_MINIMAL_RECIPE_PAYLOAD[template_name], sender=sender)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(data, registry[template_name].schema)


MARGINS_CLAUSE = "margins default to left 2cm, right 2cm, top 1.7cm, overridden per key"


@pytest.mark.parametrize(
    "template_name,expected",
    [
        ("faktura", ["the columns footer, with fields derived from sender", MARGINS_CLAUSE]),
        ("kvitto", ["the columns footer, with fields derived from sender", MARGINS_CLAUSE]),
        ("protokoll", ["the page-number footer with the document title"]),
    ],
)
def test_injected_page_template_describes_the_recipes_own_default(
    template_name, expected
):
    """`klartex schema <name>` is the agent's discovery surface: the defaults a
    left-out slot and left-out margins resolve to are the recipe's, not a
    blanket sentence."""
    registry = get_registry()
    description = registry[template_name].schema["properties"]["page_template"][
        "description"
    ]
    for clause in expected:
        assert clause in description
    if MARGINS_CLAUSE not in expected:
        assert "margins default to" not in description


def test_recipe_schema_has_no_class_options():
    """The document class carries no options, so a recipe cannot pass any."""
    schema = json.loads(
        (TEMPLATES_DIR.parent / "schemas" / "recipe.schema.json").read_text()
    )
    assert "class_options" not in schema["properties"]["document"]["properties"]


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


@pytest.mark.parametrize("template_name", RECIPE_SCHEMA_NAMES)
def test_recipe_example_validates(template_name):
    """The shipped example is what `klartex example <name>` hands an agent —
    it must validate against the schema `klartex schema <name>` shows."""
    registry = get_registry()
    example_path = TEMPLATES_DIR / template_name / "example.json"
    jsonschema.validate(json.loads(example_path.read_text()), registry[template_name].schema)


def _object_nodes(node, path="$"):
    """Yield every object node in a schema, with the path that locates it.

    An object node is one a payload can put keys into: `type: "object"`, the
    nullable `["object", "null"]` form, or a node carrying `properties`
    without a `type`.
    """
    if isinstance(node, dict):
        node_type = node.get("type")
        if (
            node_type == "object"
            or (isinstance(node_type, list) and "object" in node_type)
            or (node_type is None and "properties" in node)
        ):
            yield path, node
        for key, value in node.items():
            yield from _object_nodes(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _object_nodes(value, f"{path}[{index}]")


@pytest.mark.parametrize(
    "template_name",
    [name for name, info in get_registry().items() if not info.is_block_engine],
)
def test_recipe_schemas_are_closed_at_every_object_level(template_name):
    """A recipe payload's unknown key is rejected, not silently dropped (#78).

    The recipe surface makes the same promise the block engine's block schemas
    do: a producer's typo (`subitems` for `subItems`) fails validation with the
    key named, instead of rendering as if the field had been omitted. The walk
    covers the loaded schema, so the injected `page_template` subtree is held
    to it too — an object reopened in the slot model reopens the recipe
    surface just as surely as one in the schema file.

    An object level that must stay open needs its reasoning written down here
    as an exemption; that friction is the point.
    """
    schema = get_registry()[template_name].schema
    for path, node in _object_nodes(schema, template_name):
        assert node.get("additionalProperties") is False, path


@pytest.mark.parametrize(
    "template_name,parent_path,unknown_key",
    [
        # The typos the issue names: a misspelt property renders as nothing.
        ("protokoll", ("agenda_items", 0), "subitems"),
        ("protokoll", ("agenda_items", 0), "discusion"),
        ("faktura", ("lines", 0), "price"),
        ("faktura", ("sender",), "adress"),
        ("kvitto", ("items", 0), "amout"),
    ]
    + [(name, (), "organisation") for name in RECIPE_SCHEMA_NAMES],
)
def test_recipe_unknown_key_is_rejected(template_name, parent_path, unknown_key):
    """The message names the key and the path locates the object holding it.

    `klartex serve` reports `detail.message` and `detail.path` straight from
    this error, so the shape asserted here is the one a producer sees over
    HTTP: jsonschema puts the offending key in the message and the *parent*
    object in the path.
    """
    schema = get_registry()[template_name].schema
    data = json.loads((FIXTURES / f"{template_name}.json").read_text())
    jsonschema.validate(data, schema)

    node = data
    for step in parent_path:
        node = node[step]
    node[unknown_key] = "x"

    with pytest.raises(jsonschema.ValidationError) as excinfo:
        jsonschema.validate(data, schema)
    assert excinfo.value.validator == "additionalProperties"
    assert unknown_key in excinfo.value.message
    assert list(excinfo.value.absolute_path) == list(parent_path)


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
        {"footer": {"variant": "pagenumber", "page_numbers": "auto"}},
        {"footer": {"variant": "pagenumber", "title": True, "page_numbers": "off"}},
        {"footer": {"variant": "columns", "page_numbers": "off"}},
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
        {"footer": {"variant": "pagenumber", "page_numbers": "sometimes"}},
        {"footer": {"variant": "pagenumber", "bogus": 1}},
        {"page_numbers": True},
        {"page_numbers": "auto"},
        {"header": {"variant": "logo", "page_numbers": "on"}},
        {"footer": {"variant": "columns", "company": "X"}},
        {"footer": {"variant": "columns", "fields": {"bogus": 1}}},
        {"footer": {"variant": "columns", "title": True}},
        {"footer": {"variant": "pagenumber", "fields": {"company": "X"}}},
        {"footer": {"title": True}},
        {"footer": {"fields": {"company": "X"}}},
        {"header": "letterhead", "bogus": 1},
        {"first_page_header": False},
        {"header": "letterhead", "first_page_header": False},
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


@pytest.mark.parametrize("template_name", RECIPE_SCHEMA_NAMES + ("_block",))
def test_first_page_header_is_not_a_document_key(template_name):
    """A title_page block renders chrome-free by itself, so no schema carries
    a first-page header switch."""
    pt = get_registry()[template_name].schema["properties"]["page_template"]
    assert "first_page_header" not in pt["properties"]


@pytest.mark.parametrize("template_name", RECIPE_SCHEMA_NAMES + ("_block",))
def test_page_numbers_is_a_footer_setting_not_a_document_key(template_name):
    """The tri-state sits on both footer variants; nothing carries it at the
    document level or on a header variant."""
    pt = get_registry()[template_name].schema["properties"]["page_template"]
    assert "page_numbers" not in pt["properties"]
    object_forms = [f for f in pt["properties"]["footer"]["oneOf"] if f.get("type") == "object"]
    assert [f["properties"]["variant"]["const"] for f in object_forms] == ["pagenumber", "columns"]
    for form in object_forms:
        setting = form["properties"]["page_numbers"]
        assert setting["enum"] == ["auto", "on", "off"]
        assert setting["default"] == "auto"
    for form in pt["properties"]["header"]["oneOf"]:
        assert "page_numbers" not in form.get("properties", {})


def test_slot_listing_exposes_page_numbers_on_both_footer_variants():
    footer = {v["name"]: v for v in list_slot_variants()["footer"]}
    assert "page_numbers" in footer["pagenumber"]["settings"]
    assert "page_numbers" in footer["columns"]["settings"]


@pytest.mark.parametrize("field_name", ["web", "email"])
def test_letterhead_address_fields_document_where_they_wrap(field_name):
    """The wrapping is invisible in the payload — an agent only learns about
    it from the field description, and the structure tests above strip
    descriptions, so this is what proves the clause reaches the schema."""
    header = _block_schema()["properties"]["page_template"]["properties"]["header"]
    letterhead = next(
        form
        for form in header["oneOf"]
        if "org_name" in form.get("properties", {}).get("fields", {}).get("properties", {})
    )
    description = letterhead["properties"]["fields"]["properties"][field_name]["description"]
    assert "may wrap after @, . and /" in description


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
        # The pattern must anchor at the absolute end and exclude whitespace —
        # Python's `$` matches before a final newline, and jsonschema uses
        # Python's re.
        {"header": {"variant": "logo", "fields": {"logo": "logo.pdf\n"}}},
        {"header": {"variant": "logo", "fields": {"logo": "logo.pdf\r"}}},
        {"header": {"variant": "logo", "fields": {"logo": "logo.pdf x"}}},
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
