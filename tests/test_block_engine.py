"""Tests for the universal block engine."""

import json
import shutil
from pathlib import Path

import pytest

from klartex.block_engine import prepare_block_context, BLOCK_ENGINE_TEMPLATE

FIXTURES = Path(__file__).parent / "fixtures"
HAS_XELATEX = shutil.which("xelatex") is not None


class TestPrepareBlockContext:
    """Tests for block engine context preparation."""

    def test_context_has_required_keys(self):
        data = {
            "page_template": {"header": "letterhead", "footer": {"variant": "pagenumber", "title": True}},
            "lang": "sv",
            "body": [{"type": "heading", "text": "Test"}],
        }
        ctx = prepare_block_context(data)
        assert "body" in ctx
        assert "lang" in ctx
        assert "page_template" in ctx
        assert "doc_title" in ctx

    def test_missing_body_raises(self):
        with pytest.raises(ValueError, match="body"):
            prepare_block_context({"page_template": {"header": "logo"}})

    def test_default_page_template(self):
        data = {"body": [{"type": "heading", "text": "Test"}]}
        ctx = prepare_block_context(data)
        # The block engine defaults to an empty header and the page-number footer
        assert ctx["page_template"].header.is_empty
        assert "fancyfoot" in ctx["page_template"].footer_fragment

    def test_page_template_object(self):
        data = {
            "page_template": {"header": "logo", "page_numbers": False},
            "body": [{"type": "heading", "text": "Test"}],
        }
        ctx = prepare_block_context(data)
        assert ctx["page_template"].header.variant == "logo"
        assert "fancyhead" in ctx["page_template"].header_fragment
        assert ctx["page_template"].page_numbers is False

    def test_caller_provided_sources_override(self):
        data = {"body": [{"type": "heading", "text": "Test"}]}
        ctx = prepare_block_context(data, header_source="% h", footer_source="% f")
        assert ctx["page_template"].header.source == "% h"
        assert ctx["page_template"].footer.source == "% f"

    def test_doc_title_from_heading(self):
        data = {
            "body": [{"type": "heading", "text": "My Document"}],
        }
        ctx = prepare_block_context(data)
        assert ctx["doc_title"] == "My Document"

    def test_doc_title_from_title_page(self):
        data = {
            "body": [
                {"type": "title_page", "title": "Agreement", "party1": "A", "party2": "B"},
                {"type": "heading", "text": "Different"},
            ],
        }
        ctx = prepare_block_context(data)
        assert ctx["doc_title"] == "Agreement"

    def test_lang_defaults_to_sv(self):
        data = {"body": [{"type": "heading", "text": "Test"}]}
        ctx = prepare_block_context(data)
        assert ctx["lang"] == "sv"

    def test_lang_en(self):
        data = {"lang": "en", "body": [{"type": "heading", "text": "Test"}]}
        ctx = prepare_block_context(data)
        assert ctx["lang"] == "en"


class TestBlockTypeValidation:
    """Tests for block type detection and per-block schema validation."""

    def test_unknown_block_type_raises(self):
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "heading", "text": "Test"},
                {"type": "nonexistent_block", "text": "Bad"},
            ],
        }
        with pytest.raises(ValueError, match="Unknown block type 'nonexistent_block'"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_invalid_block_payload_raises(self):
        """A heading block without required 'text' should fail validation."""
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "heading"},  # missing required 'text'
            ],
        }
        with pytest.raises(ValueError, match="Invalid 'heading' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_invalid_signatures_payload_raises(self):
        """A signatures block with no parties should fail validation."""
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "signatures", "parties": []},
            ],
        }
        with pytest.raises(ValueError, match="Invalid 'signatures' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_invalid_signatures_columns_raises(self):
        """A signatures block with columns < 1 should fail validation."""
        from klartex.renderer import render

        data = {
            "body": [
                {
                    "type": "signatures",
                    "columns": 0,
                    "parties": [{"name": "A"}, {"name": "B"}],
                },
            ],
        }
        with pytest.raises(ValueError, match="Invalid 'signatures' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_underscore_block_types_render(self):
        """Block types with underscores (title_page, description_list) must render."""
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "title_page", "title": "Test", "party1": "A", "party2": "B"},
                {"type": "heading", "text": "Test Document"},
                {
                    "type": "description_list",
                    "entries": [
                        {"label": "Date:", "value": "2026-02-22"},
                    ],
                },
                {"type": "text", "text": "Content here."},
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    def test_missing_block_type_raises(self):
        from jsonschema import ValidationError
        from klartex.renderer import render

        data = {
            "body": [
                {"text": "No type field"},
            ],
        }
        with pytest.raises((ValueError, ValidationError)):
            render(BLOCK_ENGINE_TEMPLATE, data)


class TestBlockEngineRendering:
    """Integration tests for block engine PDF rendering."""

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_simple_document(self):
        """Heading + text + signatures produces valid PDF."""
        from klartex.renderer import render

        data = json.loads((FIXTURES / "block_simple.json").read_text())
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_avtal_via_block_engine(self):
        """Full avtal-style document via block engine produces valid PDF."""
        from klartex.renderer import render

        data = json.loads((FIXTURES / "avtal_block.json").read_text())
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_page_template_logo_header(self):
        """Block engine with the logo header renders."""
        from klartex.renderer import render

        data = {
            "page_template": {"header": "logo"},
            "body": [
                {"type": "heading", "text": "Clean Template Test"},
                {"type": "text", "text": "This uses the clean page template."},
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_page_template_empty_header(self):
        """Block engine with an empty header renders."""
        from klartex.renderer import render

        data = {
            "page_template": {"header": None},
            "body": [
                {"type": "heading", "text": "No Header Test"},
                {"type": "text", "text": "This uses no page template."},
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_description_list_block(self):
        """Metadata table block renders."""
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "heading", "text": "Meeting Notes"},
                {
                    "type": "description_list",
                    "entries": [
                        {"label": "Date:", "value": "2026-02-22"},
                        {"label": "Location:", "value": "Stockholm"},
                    ],
                },
                {"type": "text", "text": "Meeting content here."},
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_agenda_block(self):
        """Agenda block with discussion and decisions renders."""
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "heading", "text": "Styrelsemöte"},
                {
                    "type": "agenda",
                    "items": [
                        {"title": "Mötets öppnande"},
                        {
                            "title": "Val av justerare",
                            "decision": "Anna och Erik valdes.",
                        },
                        {
                            "title": "Ekonomisk rapport",
                            "discussion": "Kassören presenterade rapporten.",
                            "decision": "Styrelsen godkände rapporten.",
                        },
                        {"title": "Mötets avslutande"},
                    ],
                },
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_name_roster_block(self):
        """Name roster block renders a name/role table."""
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "heading", "text": "Förening"},
                {
                    "type": "name_roster",
                    "title": "Styrelsen 2025/2026",
                    "people": [
                        {"name": "Anna Andersson", "role": "Ordförande", "note": "omval 2 år"},
                        {"name": "Erik Eriksson", "role": "Kassör"},
                    ],
                },
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_agenda_fixture(self):
        """Full agenda fixture with both block types renders."""
        from klartex.renderer import render

        data = json.loads((FIXTURES / "block_dagordning.json").read_text())
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    def test_invalid_agenda_no_items_raises(self):
        """Agenda block without items should fail validation."""
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "agenda"},
            ],
        }
        with pytest.raises(ValueError, match="Invalid 'agenda' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_invalid_name_roster_no_people_raises(self):
        """Name roster block without people should fail validation."""
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "name_roster", "title": "Board"},
            ],
        }
        with pytest.raises(ValueError, match="Invalid 'name_roster' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)


class TestListContentField:
    """Tests for the list-item content[] field — block-level continuation
    inside a single list item, replacing the old nested-items shorthand."""

    def test_object_item_requires_content(self):
        """An object-form item must have content[] — bare {text} is invalid."""
        from klartex.renderer import render

        data = {
            "body": [
                {
                    "type": "list",
                    "items": [{"text": "no content"}],
                },
            ],
        }
        with pytest.raises(ValueError, match="Invalid 'list' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_old_nested_items_shorthand_rejected(self):
        """The pre-0.6 'items' field on an object item is no longer accepted."""
        from klartex.renderer import render

        data = {
            "body": [
                {
                    "type": "list",
                    "items": [
                        {"text": "main", "items": ["sub a", "sub b"]},
                    ],
                },
            ],
        }
        with pytest.raises(ValueError, match="Invalid 'list' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_disallowed_nested_block_type_rejected(self):
        """Block types that only make sense at top level are rejected in content[]."""
        from klartex.renderer import render

        data = {
            "body": [
                {
                    "type": "list",
                    "items": [
                        {
                            "text": "main",
                            "content": [{"type": "heading", "text": "no"}],
                        },
                    ],
                },
            ],
        }
        with pytest.raises(ValueError, match="Invalid 'list' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_quote_inside_numbered_item_keeps_numbering(self):
        """A numbered list with a quote in content[] must not introduce sub-numbering."""
        from klartex.renderer import render

        data = {
            "body": [
                {
                    "type": "list",
                    "style": "numbered",
                    "items": [
                        "First.",
                        {
                            "text": "Second with a continuation quote.",
                            "content": [
                                {"type": "quote", "text": "Föreslagen formulering."}
                            ],
                        },
                        "Third.",
                    ],
                },
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_text_and_sublist_inside_item(self):
        """text + nested list in content[] should both render under the parent item."""
        from klartex.renderer import render

        data = {
            "body": [
                {
                    "type": "list",
                    "style": "numbered",
                    "items": [
                        {
                            "text": "Outer item.",
                            "content": [
                                {"type": "text", "text": "Förklarande paragraf."},
                                {
                                    "type": "list",
                                    "style": "numbered",
                                    "items": ["Alt 1", "Alt 2"],
                                },
                            ],
                        }
                    ],
                },
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_callout_table_latex_allowed_in_content(self):
        """callout, table and latex blocks are valid nested content."""
        from klartex.renderer import render

        data = {
            "body": [
                {
                    "type": "list",
                    "style": "bullet",
                    "items": [
                        {
                            "text": "Item with callout.",
                            "content": [
                                {"type": "callout", "variant": "info", "text": "FYI"}
                            ],
                        },
                        {
                            "text": "Item with table.",
                            "content": [
                                {
                                    "type": "table",
                                    "header": ["A", "B"],
                                    "rows": [["1", "2"]],
                                }
                            ],
                        },
                        {
                            "text": "Item with latex.",
                            "content": [{"type": "latex", "source": "\\textbf{x}"}],
                        },
                    ],
                },
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"


class TestFormBlock:
    """Tests for the form block — label/value rows with blank or pre-filled fields."""

    def test_missing_fields_raises(self):
        from klartex.renderer import render

        data = {"body": [{"type": "form"}]}
        with pytest.raises(ValueError, match="Invalid 'form' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_field_without_label_raises(self):
        from klartex.renderer import render

        data = {
            "body": [{"type": "form", "fields": [{"value": "no label"}]}]
        }
        with pytest.raises(ValueError, match="Invalid 'form' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_form_does_not_accept_title(self):
        """Composition: use a heading block before the form for sub-titles."""
        from klartex.renderer import render

        data = {
            "body": [
                {
                    "type": "form",
                    "title": "rejected",
                    "fields": [{"label": "X"}],
                }
            ]
        }
        with pytest.raises(ValueError, match="Invalid 'form' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_blank_and_filled_renders(self):
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "heading", "text": "Avtal"},
                {
                    "type": "form",
                    "fields": [
                        {"label": "Namn"},
                        {"label": "Personnr", "value": "19700101-0000"},
                        {"label": "Telefon"},
                    ],
                },
            ]
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"


class TestColumnsBlock:
    """Tests for the columns block — side-by-side layout of column-stacks."""

    def test_missing_items_raises(self):
        from klartex.renderer import render

        data = {"body": [{"type": "columns"}]}
        with pytest.raises(ValueError, match="Invalid 'columns' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_too_many_columns_raises(self):
        from klartex.renderer import render

        data = {
            "body": [
                {
                    "type": "columns",
                    "items": [
                        [{"type": "text", "text": str(i)}] for i in range(5)
                    ],
                }
            ]
        }
        with pytest.raises(ValueError, match="Invalid 'columns' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_disallowed_inner_type_rejected(self):
        from klartex.renderer import render

        data = {
            "body": [
                {
                    "type": "columns",
                    "items": [[{"type": "signatures", "parties": []}]],
                }
            ]
        }
        with pytest.raises(ValueError, match="Invalid 'columns' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_nested_columns_rejected(self):
        from klartex.renderer import render

        data = {
            "body": [
                {
                    "type": "columns",
                    "items": [
                        [{"type": "columns", "items": [[{"type": "text", "text": "x"}]]}]
                    ],
                }
            ]
        }
        with pytest.raises(ValueError, match="Invalid 'columns' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_empty_column_rejected(self):
        from klartex.renderer import render

        data = {"body": [{"type": "columns", "items": [[]]}]}
        with pytest.raises(ValueError, match="Invalid 'columns' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_two_columns_with_heading_and_form(self):
        from klartex.renderer import render

        data = {
            "body": [
                {
                    "type": "columns",
                    "items": [
                        [
                            {"type": "heading", "level": 3, "text": "Upplåtare"},
                            {
                                "type": "description_list",
                                "entries": [{"label": "Namn", "value": "Förening"}],
                            },
                        ],
                        [
                            {"type": "heading", "level": 3, "text": "Arrendator"},
                            {
                                "type": "form",
                                "fields": [{"label": "Namn"}, {"label": "Personnr"}],
                            },
                        ],
                    ],
                }
            ]
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_image_left_text_right_aligns_top(self):
        """Image (zero-strut content) and text in side-by-side columns should
        top-align, not baseline-align at image bottom. Uses \\rule as a
        baseline-bottom stand-in for \\includegraphics — the rendering
        mechanic is identical."""
        from klartex.renderer import render

        data = {
            "body": [
                {
                    "type": "columns",
                    "items": [
                        [{"type": "latex", "source": r"\rule{3cm}{2cm}"}],
                        [{"type": "text", "text": "Bildtext på höger sida."}],
                    ],
                }
            ]
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_four_columns_renders(self):
        from klartex.renderer import render

        data = {
            "body": [
                {
                    "type": "columns",
                    "items": [
                        [{"type": "text", "text": f"Col {i}"}] for i in range(4)
                    ],
                }
            ]
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_single_column_renders_as_full_width(self):
        from klartex.renderer import render

        data = {
            "body": [
                {
                    "type": "columns",
                    "items": [
                        [
                            {"type": "text", "text": "single column passes through"},
                            {"type": "form", "fields": [{"label": "X"}]},
                        ]
                    ],
                }
            ]
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"


class TestSignaturesFeatures:
    """Tests for signatures signatory/title fallback."""

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_signatures_signatory_defaults_to_name(self):
        """Signatures without explicit signatory should fall back to party name."""
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "heading", "text": "Test"},
                {
                    "type": "signatures",
                    "parties": [
                        {"name": "Acme AB"},
                        {"name": "Beta Corp"},
                    ],
                },
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_signatures_with_title_renders(self):
        """Signatures with title field should render valid PDF."""
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "heading", "text": "Test"},
                {
                    "type": "signatures",
                    "parties": [
                        {"name": "Acme AB", "signatory": "Anna Svensson", "title": "VD, Acme AB"},
                        {"name": "Beta Corp", "signatory": "Erik Johansson", "title": "Styrelseordförande"},
                    ],
                },
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_signatures_single_party_renders(self):
        """A single-party signatures block should render."""
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "heading", "text": "Test"},
                {
                    "type": "signatures",
                    "parties": [{"name": "Solo AB", "signatory": "Anna Andersson"}],
                },
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_signatures_three_parties_two_columns(self):
        """3 parties laid out in 2 columns should render (2 + 1 layout)."""
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "heading", "text": "Test"},
                {
                    "type": "signatures",
                    "columns": 2,
                    "parties": [
                        {"name": "Acme AB"},
                        {"name": "Beta Corp"},
                        {"name": "Gamma Ltd"},
                    ],
                },
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"


class TestFinancialComponents:
    """Tests for resultatrakning, budgettabell, and notapparat block types."""

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_resultatrakning_renders(self):
        from klartex.renderer import render

        data = json.loads((FIXTURES / "block_resultatrakning.json").read_text())
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_budgettabell_renders(self):
        from klartex.renderer import render

        data = json.loads((FIXTURES / "block_budgettabell.json").read_text())
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_notapparat_renders(self):
        from klartex.renderer import render

        data = json.loads((FIXTURES / "block_notapparat.json").read_text())
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    def test_resultatrakning_missing_grupper_raises(self):
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "resultatrakning", "rubrik_ar1": "2025", "rubrik_ar2": "2024"},
            ],
        }
        with pytest.raises(ValueError, match="Invalid 'resultatrakning' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_budgettabell_missing_poster_raises(self):
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "budgettabell", "rubrik_budget": "B", "rubrik_ar1": "Y1", "rubrik_ar2": "Y2"},
            ],
        }
        with pytest.raises(ValueError, match="Invalid 'budgettabell' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_notapparat_missing_noter_raises(self):
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "notapparat"},
            ],
        }
        with pytest.raises(ValueError, match="Invalid 'notapparat' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)


class TestArsmotespaket:
    """Annual meeting package — 8 document types composed from block engine."""

    ARSMOTE_FIXTURES = [
        "block_kallelse",
        "block_verksamhetsberattelse",
        "block_arsredovisning",
        "block_revisionsberattelse",
        "block_budget",
        "block_valberedning",
        "block_motion",
        "block_styrelseyttrande",
    ]

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    @pytest.mark.parametrize("fixture", ARSMOTE_FIXTURES)
    def test_arsmotespaket_renders(self, fixture):
        from klartex.renderer import render

        data = json.loads((FIXTURES / f"{fixture}.json").read_text())
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"


class TestClauseBlock:
    """Tests for the new clause block: manual numbering (free-form `number` string),
    optional `text` and `level`, and recursive `content[]` for nested blocks
    including nested clauses for sub-sections."""

    def _render_tex(self, data: dict) -> str:
        """Helper: run the renderer's pre-compile pipeline and return the
        rendered LaTeX source (no xelatex needed)."""
        from klartex.renderer import _render_block_engine, _restore_block_types
        from klartex.tex_escape import escape_data

        escaped = escape_data(data)
        _restore_block_types(data["body"], escaped["body"])
        return _render_block_engine(escaped)

    def test_number_required(self):
        from klartex.renderer import render

        data = {"body": [{"type": "clause", "text": "no number"}]}
        with pytest.raises(ValueError, match="Invalid 'clause' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_number_must_be_string(self):
        from klartex.renderer import render

        data = {"body": [{"type": "clause", "number": 7, "text": "x"}]}
        with pytest.raises(ValueError, match="Invalid 'clause' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_text_or_content_required(self):
        """A clause with only `number` is rejected — must also have text or content."""
        from klartex.renderer import render

        data = {"body": [{"type": "clause", "number": "§ 7"}]}
        with pytest.raises(ValueError, match="Invalid 'clause' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_invalid_level_rejected(self):
        from klartex.renderer import render

        data = {
            "body": [{"type": "clause", "number": "§ 1", "level": 1, "text": "x"}],
        }
        with pytest.raises(ValueError, match="Invalid 'clause' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_disallowed_nested_block_type_rejected(self):
        """Top-only block types (e.g. signatures) cannot live inside content[]."""
        from klartex.renderer import render

        data = {
            "body": [
                {
                    "type": "clause",
                    "number": "§ 1",
                    "text": "x",
                    "content": [{"type": "signatures", "parties": []}],
                }
            ]
        }
        with pytest.raises(ValueError, match="Invalid 'clause' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_freeform_number_passes_through_verbatim(self):
        """The number string is rendered exactly as written — no auto-period."""
        data = {
            "body": [
                {
                    "type": "clause",
                    "number": "§ 7.",
                    "level": 3,
                    "text": "Arrendatorns skyldigheter",
                },
            ],
        }
        tex = self._render_tex(data)
        # number rendered verbatim (period was in the input)
        assert r"\textbf{§ 7.}" in tex
        # level 3 → \large + bold text
        assert r"\large" in tex
        assert r"\textbf{Arrendatorns skyldigheter}" in tex

    def test_number_no_auto_period(self):
        """An author-written 'a)' label renders as 'a)', not 'a).'."""
        data = {
            "body": [
                {"type": "clause", "number": "a)", "text": "alternative one"},
            ],
        }
        tex = self._render_tex(data)
        assert "a)" in tex
        assert "a)." not in tex

    def test_omitted_level_neither_bold(self):
        """Without level, neither label nor text is bold (matched weight)."""
        data = {
            "body": [
                {"type": "clause", "number": "7.1.", "text": "vara folkbokförd..."},
            ],
        }
        tex = self._render_tex(data)
        # neither label nor text wrapped in \textbf
        assert r"\textbf{7.1.}" not in tex
        assert r"\textbf{vara folkbokförd...}" not in tex
        # but the number and text are present verbatim
        assert "7.1." in tex
        assert "vara folkbokförd..." in tex

    def test_level_4_text_bold_no_size(self):
        """level 4 = body size + bold text."""
        data = {
            "body": [{"type": "clause", "number": "1", "level": 4, "text": "Body bold"}],
        }
        tex = self._render_tex(data)
        assert r"\textbf{Body bold}" in tex
        # no size macro
        assert r"\Large" not in tex
        assert r"\large" not in tex

    def test_nested_clause_increases_indent(self):
        """A nested clause is rendered at parent's label-width offset."""
        data = {
            "body": [
                {
                    "type": "clause",
                    "number": "§ 7",
                    "level": 3,
                    "text": "Outer",
                    "content": [
                        {"type": "clause", "number": "7.1", "text": "Inner"},
                    ],
                },
            ],
        }
        tex = self._render_tex(data)
        # outer clause at indent 0
        assert r"\setlength{\leftskip}{0cm}" in tex
        # inner clause indented by sub_step (0.5cm), independent of parent label width
        assert r"\setlength{\leftskip}{0.5cm}" in tex

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_recursive_clause_renders(self):
        """End-to-end: § 7 with intro text and nested clauses produces a valid PDF."""
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "heading", "text": "Arrendeavtal"},
                {
                    "type": "clause",
                    "number": "§ 7",
                    "level": 3,
                    "text": "Arrendatorns skyldigheter",
                    "content": [
                        {
                            "type": "text",
                            "text": "Arrendatorn förbinder sig under arrendetiden att:",
                        },
                        {"type": "clause", "number": "7.1", "text": "vara folkbokförd."},
                        {"type": "clause", "number": "7.2", "text": "inte äga annan."},
                        {"type": "clause", "number": "7.3", "text": "inte upplåta."},
                    ],
                },
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_three_levels_of_nesting(self):
        """Deep nesting (§ 1 > 1.1 > 1.1.1) renders without errors."""
        from klartex.renderer import render

        data = {
            "body": [
                {
                    "type": "clause",
                    "number": "§ 1",
                    "level": 3,
                    "text": "Top",
                    "content": [
                        {
                            "type": "clause",
                            "number": "1.1",
                            "level": 4,
                            "text": "Mid",
                            "content": [
                                {"type": "clause", "number": "1.1.1", "text": "Leaf"},
                            ],
                        },
                    ],
                },
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"


class TestRecipeTemplatesStillWork:
    """Ensure recipe templates are unaffected by block engine changes."""

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_protokoll_still_works(self):
        from klartex.renderer import render

        data = json.loads((FIXTURES / "protokoll.json").read_text())
        pdf = render("protokoll", data)
        assert pdf[:5] == b"%PDF-"



def _render_tex(data: dict, **sources: str) -> str:
    """Module helper: run the renderer's pre-compile pipeline and return the
    rendered LaTeX source (no xelatex needed).

    ``sources`` forwards ``header_source`` / ``footer_source`` to the
    block-engine renderer.
    """
    from klartex.renderer import _render_block_engine, _restore_block_types
    from klartex.tex_escape import escape_data

    escaped = escape_data(data)
    _restore_block_types(data["body"], escaped["body"])
    return _render_block_engine(
        escaped,
        header_source=sources.get("header_source"),
        footer_source=sources.get("footer_source"),
    )


class TestCellSafeLineBreaks:
    """Literal \\n inside tabular cells must not become \\\\ — with
    \\arraybackslash that ends the table row instead of breaking the line."""

    def test_table_cell_newline_uses_newline_macro(self):
        data = {"body": [{"type": "table", "header": ["A", "B"], "rows": [["x\ny", "z"]]}]}
        tex = _render_tex(data)
        assert r"x \newline y" in tex
        assert r"x \\ y" not in tex

    def test_table_header_cell_newline_uses_newline_macro(self):
        data = {"body": [{"type": "table", "header": ["Lång\nrubrik", "B"], "rows": [["x", "z"]]}]}
        tex = _render_tex(data)
        assert r"Lång \newline rubrik" in tex

    def test_form_value_newline_is_cell_safe(self):
        data = {"body": [{"type": "form", "fields": [{"label": "Adress", "value": "Rad 1\nRad 2"}]}]}
        tex = _render_tex(data)
        assert r"Rad 1 \newline Rad 2" in tex

    def test_form_label_newline_collapses_to_space(self):
        """Labels sit in an LR-mode `l` column where no in-cell break exists."""
        data = {"body": [{"type": "form", "fields": [{"label": "Två\nrader", "value": "x"}]}]}
        tex = _render_tex(data)
        assert "Två rader" in tex

    def test_description_list_value_newline_is_cell_safe(self):
        data = {"body": [{"type": "description_list",
                          "entries": [{"label": "Adress", "value": "Rad 1\nRad 2"}]}]}
        tex = _render_tex(data)
        assert r"Rad 1 \newline Rad 2" in tex
        assert r"Rad 1 \\ Rad 2" not in tex

    def test_description_list_label_newline_collapses_to_space(self):
        """Labels sit in an LR-mode `l` column where no in-cell break exists."""
        data = {"body": [{"type": "description_list",
                          "entries": [{"label": "Två\nrader", "value": "x"}]}]}
        tex = _render_tex(data)
        assert "Två rader" in tex

    def test_text_block_newline_still_paragraph_break(self):
        data = {"body": [{"type": "text", "text": "rad 1\nrad 2"}]}
        tex = _render_tex(data)
        assert r"rad 1 \\ rad 2" in tex

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_cell_newlines_compile(self):
        from klartex.renderer import render

        data = {"body": [
            {"type": "table", "header": ["Rubrik\nrad två", "B"], "rows": [["x\ny", "z"], ["a", "b"]]},
            {"type": "form", "fields": [{"label": "Fält\nnamn", "value": "v1\nv2"}]},
        ]}
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"


class TestNestedBlockValidation:
    """Nested blocks (clause.content[], list.items[].content[], columns.items[][])
    are validated against their own schemas, with a path in the error."""

    def test_nested_list_missing_items_rejected(self):
        from klartex.renderer import render

        data = {"body": [{"type": "clause", "number": "§ 1", "content": [{"type": "list"}]}]}
        with pytest.raises(ValueError, match=r"Invalid 'list' block at body\[0\]\.content\[0\]"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_nested_text_missing_text_rejected(self):
        from klartex.renderer import render

        data = {"body": [{"type": "list", "items": [{"text": "punkt", "content": [{"type": "text"}]}]}]}
        with pytest.raises(ValueError, match=r"Invalid 'text' block at body\[0\]\.items\[0\]\.content\[0\]"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_columns_nested_block_validated(self):
        from klartex.renderer import render

        data = {"body": [{"type": "columns", "items": [[{"type": "text"}]]}]}
        with pytest.raises(ValueError, match=r"Invalid 'text' block at body\[0\]\.items\[0\]\[0\]"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_unknown_type_reports_path(self):
        from klartex.renderer import render

        data = {"body": [{"type": "foo"}]}
        with pytest.raises(ValueError, match=r"Unknown block type 'foo' at body\[0\]"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_valid_nested_document_passes(self):
        """A correctly shaped nested document still renders to .tex."""
        data = {"body": [
            {"type": "clause", "number": "§ 1", "text": "Topp", "content": [
                {"type": "list", "items": ["a", {"text": "b", "content": [
                    {"type": "text", "text": "nested"},
                ]}]},
            ]},
            {"type": "columns", "items": [[{"type": "text", "text": "kolumn"}]]},
        ]}
        tex = _render_tex(data)
        assert "nested" in tex and "kolumn" in tex


class TestSignaturesContractIntro:
    """The contract boilerplate intro is opt-in via contract_intro, not
    inferred from the party count."""

    def test_two_parties_without_flag_has_no_intro(self):
        data = {"body": [{"type": "signatures", "new_page": False,
                          "parties": [{"name": "A"}, {"name": "B"}]}]}
        tex = _render_tex(data)
        assert r"\kxsignaturesintro" not in tex

    def test_contract_intro_true_renders_intro(self):
        data = {"body": [{"type": "signatures", "new_page": False, "contract_intro": True,
                          "parties": [{"name": "A"}, {"name": "B"}]}]}
        tex = _render_tex(data)
        assert r"\kxsignaturesintro" in tex

    def test_contract_intro_independent_of_party_count(self):
        data = {"body": [{"type": "signatures", "new_page": False, "contract_intro": True,
                          "parties": [{"name": "A"}, {"name": "B"}, {"name": "C"}]}]}
        tex = _render_tex(data)
        assert r"\kxsignaturesintro" in tex

    def test_contract_intro_accepted_by_schema(self):
        from klartex.renderer import render

        data = {"body": [{"type": "signatures", "contract_intro": True,
                          "parties": [{"name": "A"}]}]}
        if HAS_XELATEX:
            assert render(BLOCK_ENGINE_TEMPLATE, data)[:5] == b"%PDF-"
        else:
            _render_tex(data)


class TestPartySignatory:
    """parties.party*.signatory renders as a 'Företräds av' line, skipped
    when it equals the party name (same convention as the signature pane)."""

    def _data(self, party1, party2):
        return {"body": [{"type": "parties", "party1": party1, "party2": party2}]}

    def test_signatory_rendered_when_differs_from_name(self):
        tex = _render_tex(self._data(
            {"name": "Acme AB", "org_number": "556789-0123", "signatory": "Anna Andersson, VD"},
            {"name": "Erik Eriksson"},
        ))
        assert "Företräds av: Anna Andersson, VD" in tex

    def test_signatory_skipped_when_same_as_name(self):
        tex = _render_tex(self._data(
            {"name": "Erik Eriksson", "signatory": "Erik Eriksson"},
            {"name": "Acme AB"},
        ))
        assert "Företräds av" not in tex

    def test_address_still_renders(self):
        tex = _render_tex(self._data(
            {"name": "Acme AB", "address": "Storgatan 1, 111 22 Stockholm"},
            {"name": "Erik Eriksson", "address_line1": "Lilla vägen 3", "address_line2": "222 33 Göteborg"},
        ))
        assert "Storgatan 1" in tex
        assert "Lilla vägen 3" in tex


class TestTableColumnAlign:
    """align must apply also when a fixed column width is given."""

    def test_fixed_width_column_gets_align_prefix(self):
        data = {"body": [{"type": "table", "header": ["A", "B"], "rows": [["1", "2"]],
                          "columns": [{"width": "3cm", "align": "right"}, {"align": "left"}]}]}
        tex = _render_tex(data)
        assert r">{\raggedleft\arraybackslash}p{3cm}" in tex

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_fixed_width_aligned_table_compiles(self):
        from klartex.renderer import render

        data = {"body": [{"type": "table", "header": ["A", "B"], "rows": [["1", "2"]],
                          "columns": [{"width": "3cm", "align": "right"}, {"align": "center"}]}]}
        assert render(BLOCK_ENGINE_TEMPLATE, data)[:5] == b"%PDF-"


class TestTitlePageOptionalParties:
    """title_page without parties renders only the title — no stray 'Och'
    or blank party rows (handled inside \\makedoctitle)."""

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_title_only_and_single_party_compile(self):
        from klartex.renderer import render

        data = {"body": [
            {"type": "title_page", "title": "Verksamhetsberättelse 2025"},
            {"type": "title_page", "party1": "Föreningen X", "title": "Stadgar"},
        ]}
        assert render(BLOCK_ENGINE_TEMPLATE, data)[:5] == b"%PDF-"

    def test_title_only_passes_empty_party_args(self):
        data = {"body": [{"type": "title_page", "title": "Bara titel"}]}
        tex = _render_tex(data)
        assert r"\makedoctitle{}{}{Bara titel}" in tex


class TestSpacingOverrides:
    """Issue #29: per-instance spacing_before/spacing_after and document-level
    block_settings, resolution per-instance > block_settings > default."""

    def test_table_default_spacing(self):
        data = {"body": [{"type": "table", "header": ["A"], "rows": [["1"]]}]}
        tex = _render_tex(data)
        assert tex.count(r"\vspace{1em}") == 2

    def test_block_settings_overrides_default(self):
        data = {
            "block_settings": {"table": {"spacing_after": "2.5em"}},
            "body": [{"type": "table", "header": ["A"], "rows": [["1"]]}],
        }
        tex = _render_tex(data)
        assert r"\vspace{2.5em}" in tex
        assert tex.count(r"\vspace{1em}") == 1  # before behåller default

    def test_per_instance_beats_block_settings(self):
        data = {
            "block_settings": {"table": {"spacing_after": "2.5em"}},
            "body": [{"type": "table", "header": ["A"], "rows": [["1"]], "spacing_after": "3em"}],
        }
        tex = _render_tex(data)
        assert r"\vspace{3em}" in tex
        assert r"\vspace{2.5em}" not in tex

    def test_heading_spacing_before_overrides_level_default(self):
        base = {"body": [{"type": "heading", "text": "Rubrik"}]}
        assert r"\vspace{2.0em}" in _render_tex(base)

        overridden = {"body": [{"type": "heading", "text": "Rubrik", "spacing_before": "0em"}]}
        tex = _render_tex(overridden)
        assert r"\vspace{0em}" in tex
        assert r"\vspace{2.0em}" not in tex

    def test_heading_block_settings_applies_to_all_levels(self):
        data = {
            "block_settings": {"heading": {"spacing_before": "0.7em"}},
            "body": [
                {"type": "heading", "text": "Ett", "level": 1},
                {"type": "heading", "text": "Två", "level": 2},
            ],
        }
        tex = _render_tex(data)
        assert tex.count(r"\vspace{0.7em}") == 2
        assert r"\vspace{2.0em}" not in tex
        assert r"\vspace{1.4em}" not in tex

    def test_text_has_no_spacing_by_default_but_gains_override(self):
        base = {"body": [{"type": "text", "text": "hej"}]}
        assert r"\vspace{4em}" not in _render_tex(base)

        overridden = {"body": [{"type": "text", "text": "hej", "spacing_after": "4em"}]}
        assert r"\vspace{4em}" in _render_tex(overridden)

    def test_quote_keeps_default_when_unset(self):
        data = {"body": [{"type": "quote", "text": "citat"}]}
        tex = _render_tex(data)
        assert tex.count(r"\vspace{2em}") == 2

    def test_description_list_block_settings(self):
        data = {
            "block_settings": {"description_list": {"spacing_before": "0.5em", "spacing_after": "0.5em"}},
            "body": [{"type": "description_list", "entries": [{"label": "Datum", "value": "2026-07-06"}]}],
        }
        tex = _render_tex(data)
        assert tex.count(r"\vspace{0.5em}") == 2
        assert r"\vspace{2em}" not in tex

    def test_spacing_field_rejected_on_unsupported_block(self):
        from klartex.renderer import render

        data = {"body": [{"type": "signatures", "parties": [{"name": "A"}], "spacing_before": "1em"}]}
        with pytest.raises(ValueError, match="Invalid 'signatures' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_malformed_block_settings_rejected(self):
        import jsonschema

        from klartex.renderer import render

        data = {
            "block_settings": {"heading": {"spacing_before": 5}},
            "body": [{"type": "heading", "text": "x"}],
        }
        with pytest.raises(jsonschema.ValidationError):
            render(BLOCK_ENGINE_TEMPLATE, data)

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_spacing_overrides_compile(self):
        from klartex.renderer import render

        data = {
            "block_settings": {"heading": {"spacing_before": "1em"}, "table": {"spacing_after": "2em"}},
            "body": [
                {"type": "heading", "text": "Dokument"},
                {"type": "text", "text": "Stycke.", "spacing_after": "2em"},
                {"type": "table", "header": ["A", "B"], "rows": [["1", "2"]], "spacing_before": "0em"},
                {"type": "list", "items": ["a", "b"], "spacing_before": "1.5em", "spacing_after": "1.5em"},
                {"type": "callout", "text": "Obs", "spacing_before": "1em"},
                {"type": "quote", "text": "Citat", "spacing_after": "0em"},
                {"type": "description_list", "entries": [{"label": "Datum", "value": "Idag"}], "spacing_before": "1em"},
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"


class TestHeadingAlignment:
    """Left-aligned headings set \\raggedright; center/right rely on their
    surrounding environment instead."""

    def test_left_is_ragged_right_by_default(self):
        tex = _render_tex({"body": [{"type": "heading", "text": "Rubrik"}]})
        assert tex.count(r"\raggedright") == 1

    def test_explicit_left_is_ragged_right(self):
        data = {"body": [{"type": "heading", "text": "Rubrik", "textAlign": "left"}]}
        assert _render_tex(data).count(r"\raggedright") == 1

    def test_center_is_not_ragged_right(self):
        data = {"body": [{"type": "heading", "text": "Rubrik", "textAlign": "center"}]}
        tex = _render_tex(data)
        assert r"\begin{center}" in tex
        assert r"\raggedright" not in tex

    def test_right_is_not_ragged_right(self):
        data = {"body": [{"type": "heading", "text": "Rubrik", "textAlign": "right"}]}
        tex = _render_tex(data)
        assert r"\begin{flushright}" in tex
        assert r"\raggedright" not in tex


class TestChangeMarking:
    """Change marking (#40): inline `{+…+}` / `[-…-]` markers and the
    block-level `revision` attribute on `text`."""

    def test_inline_markers_become_macros(self):
        data = {"body": [{"type": "text", "text": "tidigast [-sex-]{+åtta+} veckor"}]}
        tex = _render_tex(data)
        assert r"\kxremoved{sex}" in tex
        assert r"\kxadded{åtta}" in tex

    def test_marker_delimiters_are_consumed(self):
        data = {"body": [{"type": "text", "text": "{+ny+} och [-gammal-]"}]}
        tex = _render_tex(data)
        assert r"\{+" not in tex
        assert r"+\}" not in tex
        assert "[-" not in tex
        assert "-]" not in tex

    def test_markers_work_in_table_cells(self):
        data = {"body": [{
            "type": "table",
            "header": ["Avgift", "Förslag"],
            "rows": [["Årsavgift", "[-kvartalsvis-] {+månadsvis+}"]],
        }]}
        tex = _render_tex(data)
        assert r"\kxremoved{kvartalsvis}" in tex
        assert r"\kxadded{månadsvis}" in tex

    def test_markers_work_in_description_list(self):
        data = {"body": [{
            "type": "description_list",
            "entries": [{"label": "Beslutsform:",
                         "value": "Två stämmor, [-två tredjedels-] {+enkel+} majoritet"}],
        }]}
        tex = _render_tex(data)
        assert r"\kxremoved{två tredjedels}" in tex
        assert r"\kxadded{enkel}" in tex
        assert r"\{+" not in tex
        assert "[-" not in tex

    def test_markers_work_in_agenda(self):
        data = {"body": [{
            "type": "agenda",
            "items": [{"title": "Kallelse",
                       "decision": "Kallelse skickas [-sex-] {+åtta+} veckor i förväg."}],
        }]}
        tex = _render_tex(data)
        assert r"\kxremoved{sex}" in tex
        assert r"\kxadded{åtta}" in tex
        assert r"\{+" not in tex
        assert "[-" not in tex

    def test_revision_added_wraps_paragraph(self):
        data = {"body": [{"type": "text", "text": "Nytt stycke.", "revision": "added"}]}
        tex = _render_tex(data)
        assert r"\kxadded{Nytt stycke.}" in tex

    def test_revision_removed_wraps_paragraph(self):
        data = {"body": [{"type": "text", "text": "Utgår helt.", "revision": "removed"}]}
        tex = _render_tex(data)
        assert r"\kxremoved{Utgår helt.}" in tex

    def test_no_revision_leaves_paragraph_unwrapped(self):
        data = {"body": [{"type": "text", "text": "Oförändrat stycke."}]}
        tex = _render_tex(data)
        assert "Oförändrat stycke." in tex
        assert r"\kxadded" not in tex
        assert r"\kxremoved" not in tex

    def test_revision_inside_clause_content(self):
        data = {"body": [{
            "type": "clause",
            "number": "§ 7",
            "level": 2,
            "text": "Kallelse",
            "content": [
                {"type": "text", "text": "Gamla lydelsen.", "revision": "removed"},
                {"type": "text", "text": "Nya lydelsen.", "revision": "added"},
            ],
        }]}
        tex = _render_tex(data)
        assert r"\kxremoved{Gamla lydelsen.}" in tex
        assert r"\kxadded{Nya lydelsen.}" in tex

    def test_invalid_revision_value_rejected(self):
        from klartex.renderer import render

        data = {"body": [{"type": "text", "text": "x", "revision": "changed"}]}
        with pytest.raises(ValueError, match="Invalid 'text' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    def test_fixture_validates_and_renders_tex(self):
        data = json.loads((FIXTURES / "block_stadgeandring.json").read_text())
        tex = _render_tex(data)
        assert r"\kxadded{" in tex
        assert r"\kxremoved{" in tex
        assert r"\{+" not in tex
        assert r"-\}" not in tex

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_stadgeandring_fixture_compiles(self):
        from klartex.renderer import render

        data = json.loads((FIXTURES / "block_stadgeandring.json").read_text())
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    @pytest.mark.parametrize("revision", ["added", "removed"])
    def test_revision_block_compiles(self, revision):
        from klartex.renderer import render

        data = {"body": [
            {"type": "text", "text": "Ett stycke med ändringsmarkering.", "revision": revision},
            {"type": "text", "text": "Inline {+tillagt+} och [-struket-] i löptext."},
        ]}
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"


class TestDiffStyle:
    """The diff_style page-template option reaches the LaTeX source."""

    def test_absent_by_default(self):
        tex = _render_tex({"body": [{"type": "text", "text": "hej"}]})
        assert r"\kxdiffstyle" not in tex

    def test_color_emits_nothing(self):
        data = {
            "page_template": {"header": "logo", "diff_style": "color"},
            "body": [{"type": "text", "text": "hej"}],
        }
        assert r"\kxdiffstyle" not in _render_tex(data)

    def test_underline_is_emitted(self):
        data = {
            "page_template": {"header": "logo", "diff_style": "underline"},
            "body": [{"type": "text", "text": "hej"}],
        }
        assert r"\kxdiffstyle{underline}" in _render_tex(data)

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_underlined_document_compiles(self):
        from klartex.renderer import render

        data = {
            "lang": "sv",
            "page_template": {"header": "logo", "diff_style": "underline"},
            "body": [
                {"type": "heading", "text": "tidigast [-sex-] {+åtta+} veckor"},
                {"type": "text", "text": "Struket: [-gammal-] och tillagt: {+ny lydelse+}."},
                {"type": "text", "text": "Tillagt stycke.", "revision": "added"},
                {"type": "table", "header": ["A"], "rows": [["[-x-] {+y+}"]]},
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"


class TestDescriptionListInlineMarkup:
    """`description_list` routes both columns through the inline filters:
    `inline_flat` for the LR-mode label column, `inline_cell` for the
    paragraph-mode value column (#47)."""

    def test_bold_in_value_becomes_textbf(self):
        data = {"body": [{"type": "description_list",
                          "entries": [{"label": "Ärende:", "value": "Ändring av **§ 24**"}]}]}
        tex = _render_tex(data)
        assert r"\textbf{§ 24}" in tex
        assert "**" not in tex

    def test_bold_in_label_nests_inside_the_column_bold(self):
        """The label column already wraps its content in \\textbf, so a bare
        \\textbf assertion would pass without the filter — assert the nesting."""
        data = {"body": [{"type": "description_list",
                          "entries": [{"label": "**Obs:**", "value": "x"}]}]}
        tex = _render_tex(data)
        assert r"\textbf{\textbf{Obs:}}" in tex
        assert "**" not in tex

    def test_code_and_italic_in_value(self):
        data = {"body": [{"type": "description_list",
                          "entries": [{"label": "Fält:", "value": "*lutande* och `kod`"}]}]}
        tex = _render_tex(data)
        assert r"\textit{lutande}" in tex
        assert r"\texttt{kod}" in tex

    def test_swedish_smart_quotes_by_default(self):
        data = {"body": [{"type": "description_list",
                          "entries": [{"label": "Namn:", "value": 'Föreningen "Norden"'}]}]}
        tex = _render_tex(data)
        assert "Föreningen ”Norden”" in tex

    def test_english_lang_reaches_the_imported_macro(self):
        """The inline filters are pass_context and read `lang` from the render
        context; the macro import must carry it (`with context`)."""
        data = {
            "lang": "en",
            "body": [
                {"type": "heading", "text": 'The "Nordic" Society'},
                {"type": "description_list",
                 "entries": [{"label": "Name:", "value": 'The "Nordic" Society'}]},
            ],
        }
        tex = _render_tex(data)
        assert tex.count("The “Nordic” Society") == 2
        assert "The ”Nordic” Society" not in tex

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_marked_up_description_list_compiles(self):
        from klartex.renderer import render

        data = {"body": [{
            "type": "description_list",
            "entries": [
                {"label": "**Ärende:**", "value": 'Stadgeändring i "§ 24"'},
                {"label": "Beslutsform:", "value": "Två stämmor, [-två tredjedels-] {+enkel+} majoritet"},
                {"label": "Adress:", "value": "Storgatan 1\n123 45 Staden"},
            ],
        }]}
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"


class TestAgendaInlineMarkup:
    """`agenda` routes item text through the inline filter — title, discussion,
    decision, `decisionLabel` and `subItems`, in both numbering styles (#60)."""

    @pytest.mark.parametrize(
        "numbering_style, expected_title",
        [
            # The section branch emits \punkt{…} and \punkt supplies the outer
            # \textbf itself; the decimal branch writes the \textbf inline. A
            # bare \textbf{justerare} would pass in the decimal branch without
            # the fix, so each branch asserts its own shape.
            ("section", r"\punkt{\textbf{justerare}}"),
            ("decimal", r"\textbf{\textbf{justerare}}"),
        ],
    )
    def test_item_fields_pass_through_inline_markup(self, numbering_style, expected_title):
        data = {"body": [{
            "type": "agenda",
            "numberingStyle": numbering_style,
            "decisionLabel": "Beslut\nfattat:",
            "items": [{
                "title": "**justerare**",
                "discussion": "[-Kort-] {+Lång+} diskussion\nRad 2",
                "decision": "*lutande* och `kod`",
            }],
        }]}
        tex = _render_tex(data)
        assert expected_title in tex
        assert "**" not in tex
        assert r"\kxremoved{Kort}" in tex
        assert r"\kxadded{Lång}" in tex
        assert r"\{+" not in tex
        assert "[-" not in tex
        assert r"diskussion \\ Rad 2" in tex
        assert r"\textit{lutande}" in tex
        assert r"\texttt{kod}" in tex
        assert r"\textbf{Beslut fattat:}" in tex

    def test_sub_items_pass_through_inline_markup(self):
        data = {"body": [{
            "type": "agenda",
            "numberingStyle": "decimal",
            "items": [{"title": "Ekonomi",
                       "subItems": ["**Budget** [-2025-] {+2026+}"]}],
        }]}
        tex = _render_tex(data)
        assert (r"\makebox[1.0cm][l]{\textbf{1.1.}}"
                r"\textbf{Budget} \kxremoved{2025} \kxadded{2026}") in tex

    def test_english_lang_reaches_the_imported_macro(self):
        """The inline filter is pass_context and reads `lang` from the render
        context; the macro import must carry it (`with context`)."""
        data = {
            "lang": "en",
            "body": [{"type": "agenda",
                      "items": [{"title": 'The "Nordic" Society',
                                 "discussion": 'A "quoted" phrase.'}]}],
        }
        tex = _render_tex(data)
        assert "The “Nordic” Society" in tex
        assert "A “quoted” phrase." in tex
        assert "”Nordic”" not in tex

    def test_swedish_smart_quotes_by_default(self):
        data = {"body": [{"type": "agenda",
                          "items": [{"title": 'Föreningen "Norden"',
                                     "discussion": 'Om "stadgarna".'}]}]}
        tex = _render_tex(data)
        assert "Föreningen ”Norden”" in tex
        assert "Om ”stadgarna”." in tex

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    @pytest.mark.parametrize("numbering_style", ["section", "decimal"])
    def test_marked_up_agenda_compiles(self, numbering_style):
        from klartex.renderer import render

        data = {"body": [{
            "type": "agenda",
            "numberingStyle": numbering_style,
            "items": [
                {"title": "Val av **justerare** [-och sekreterare-]",
                 "discussion": "Frågan om {+arvode+} diskuterades.",
                 "decision": 'Anna valdes.\nErik valdes till "ersättare".'},
                {"title": "Ekonomi",
                 "subItems": ["**Budget** 2026", "Rapport i `SIE4`-format"]},
            ],
        }]}
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"


class TestHeaderFieldsInlineMarkup:
    """`title_page`, `signatures` and `name_roster` route their text fields
    through the inline filter (#69). Every field lands inside a macro
    argument or a table cell, so newlines collapse to a space (`inline_flat`)
    — except `name_roster.role`, a paragraph-mode X column where a newline
    becomes `\\newline` (`inline_cell`)."""

    def test_title_page_fields_pass_through_inline_markup(self):
        data = {"body": [{
            "type": "title_page",
            "party1": "**Uppdragsgivaren AB**",
            "party2": 'Erik "Eriksson"',
            "title": "Konsultavtal\nmed bilagor",
        }]}
        tex = _render_tex(data)
        assert (r"\makedoctitle{\textbf{Uppdragsgivaren AB}}"
                r"{Erik ”Eriksson”}{Konsultavtal med bilagor}") in tex

    def test_signatures_header_and_party_fields_pass_through_inline_markup(self):
        data = {"body": [{
            "type": "signatures",
            "new_page": False,
            "header": "Underskrifter [-2025-] {+2026+}",
            "parties": [{"name": "**Acme** AB",
                         "signatory": "Anna\nAndersson",
                         "title": "*VD*"}],
        }]}
        tex = _render_tex(data)
        header = r"Underskrifter \kxremoved{2025} \kxadded{2026}"
        assert r"\section*{" + header + "}" in tex
        assert r"\addcontentsline{toc}{section}{" + header + "}" in tex
        assert r"\kxsignaturepane{\textbf{Acme} AB}{Anna Andersson}{\textit{VD}}{}" in tex
        assert r"\{+" not in tex
        assert "[-" not in tex

    def test_signatures_signatory_defaults_to_the_filtered_name(self):
        """\\kxsignatory@line compares party name and signatory token by
        token, so the default must be the same filtered output as `name`."""
        data = {"body": [{"type": "signatures", "new_page": False,
                          "parties": [{"name": "**Acme** AB"}]}]}
        tex = _render_tex(data)
        assert r"\kxsignaturepane{\textbf{Acme} AB}{\textbf{Acme} AB}{}{}" in tex

    def test_name_roster_fields_pass_through_inline_markup(self):
        data = {"body": [{
            "type": "name_roster",
            "title": 'Styrelsen "2026"',
            "people": [{"name": "**Anna** Andersson",
                        "role": "Ordförande\nsedan 2020",
                        "note": "[-omval-] {+nyval+}"}],
        }]}
        tex = _render_tex(data)
        assert r"\namnrollista{Styrelsen ”2026”}{" in tex
        assert (r"\person{\textbf{Anna} Andersson}{Ordförande \newline sedan 2020}"
                r"{\kxremoved{omval} \kxadded{nyval}}") in tex
        assert "**" not in tex

    def test_english_lang_reaches_the_filter(self):
        data = {
            "lang": "en",
            "body": [
                {"type": "title_page", "title": 'The "Nordic" Agreement'},
                {"type": "name_roster", "title": 'Board "2026"',
                 "people": [{"name": "Anna", "role": "Chair"}]},
            ],
        }
        tex = _render_tex(data)
        assert "The “Nordic” Agreement" in tex
        assert "Board “2026”" in tex
        assert "”Nordic”" not in tex

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_marked_up_header_fields_compile(self):
        from klartex.renderer import render

        data = {"body": [
            {"type": "title_page",
             "party1": "**Uppdragsgivaren AB**",
             "party2": 'Erik "Eriksson"',
             "title": "Konsultavtal\nmed bilagor"},
            {"type": "name_roster",
             "title": 'Styrelsen "2026"',
             "people": [{"name": "**Anna** Andersson",
                         "role": "Ordförande\nsedan 2020",
                         "note": "[-omval-] {+nyval+}"},
                        {"name": "Erik Eriksson", "role": "`Kassör`"}]},
            {"type": "signatures", "new_page": False,
             "header": "Underskrifter [-2025-] {+2026+}",
             "parties": [{"name": "**Acme** AB",
                          "signatory": "Anna\nAndersson",
                          "title": "*VD*"},
                         {"name": 'Föreningen "Norden"'}]},
        ]}
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"


GOLDEN = FIXTURES / "golden"


def golden_preamble(tex: str) -> list[str]:
    """The preamble of `tex` as a sorted list of significant lines.

    Normalised so the comparison survives the composition's emission order
    without losing any line: blank lines go, the `\\providecommand` contract
    lines go (they live in `klartex-base.cls`), and `\\makeatletter` /
    `\\makeatother` go (each fragment carries its own pair). Every other line
    must survive verbatim.
    """
    preamble = tex.split(r"\begin{document}")[0]
    kept = []
    for line in preamble.splitlines():
        if not line.strip():
            continue
        if line.startswith(r"\providecommand"):
            continue
        if line.strip() in (r"\makeatletter", r"\makeatother"):
            continue
        kept.append(line)
    return sorted(kept)


class TestPageTemplateGoldens:
    r"""The three aliases must still emit the preamble they emitted before the
    slot model existed. The goldens were captured from `main`.

    One region is not `main`'s text: the letterhead's right-hand contact
    column, where the unconditional `\\` separator was replaced by
    `\kx@hdrline` so a column with empty leading fields compiles. The golden
    output is unaffected — the whole block sits inside `\ifdefempty{\orgname}`,
    which is false for every payload that supplies no header settings. Every
    other line is still `main`'s, verbatim.
    """

    @pytest.mark.parametrize(
        "golden_name,slots",
        [
            ("letterhead_title", {"header": "letterhead", "footer": {"variant": "pagenumber", "title": True}}),
            ("logo", {"header": "logo"}),
            ("empty_header", {"header": None}),
        ],
    )
    def test_slot_combination_preamble_unchanged(self, golden_name, slots):
        data = {
            "page_template": slots,
            "body": [
                {"type": "heading", "text": "Golden"},
                {"type": "text", "text": "x"},
            ],
        }
        golden = (GOLDEN / f"page_template_{golden_name}.tex").read_text(encoding="utf-8")
        assert golden_preamble(_render_tex(data)) == golden_preamble(golden)

    @pytest.mark.parametrize("header", ["letterhead", "logo"])
    def test_header_precedes_footer_and_reclaim_is_last(self, header):
        """Line-set equality is order-blind, so lock the order that matters."""
        tex = _render_tex(
            {
                "page_template": {"header": header},
                "body": [{"type": "heading", "text": "Golden"}],
            }
        ).split(r"\begin{document}")[0]
        assert tex.index(r"\fancyhead") < tex.index(r"\fancyfoot")
        assert tex.index(r"\fancyfoot") < tex.index("includehead=false")

    def test_empty_header_reclaims_unconditionally(self):
        tex = _render_tex(
            {"page_template": {"header": None}, "body": [{"type": "heading", "text": "G"}]}
        )
        assert r"\geometry{top=\kxreclaimtop, headheight=0pt, headsep=0pt, includehead=false}" in tex
        assert r"\ifdefempty{\orgname}" not in tex


#: Sentinel for "no page_template key at all" in the slot helper below.
_MISSING_PT = object()


class TestPageTemplateSlots:
    """Tex-level composition locks for the header/footer slot model."""

    @staticmethod
    def _tex(page_template=None, **sources):
        data = {"body": [{"type": "heading", "text": "Rubrik"}]}
        if page_template is not _MISSING_PT:
            data["page_template"] = page_template
        return _render_tex(data, **sources)

    # --- defaults ----------------------------------------------------------

    def test_missing_page_template_equals_block_defaults(self):
        assert self._tex(_MISSING_PT) == self._tex({"header": None, "footer": "pagenumber"})

    def test_only_a_title_footer_prints_the_title(self):
        assert r"\doctitle\ \textbullet\ " in self._tex({"footer": {"variant": "pagenumber", "title": True}})
        assert r"\doctitle\ \textbullet\ " not in self._tex({"header": "logo"})
        assert r"\doctitle\ \textbullet\ " not in self._tex({"header": None})

    # --- header-space reclaim ----------------------------------------------

    def test_empty_header_reclaims_unconditionally(self):
        tex = self._tex({"header": None})
        assert "includehead=false" in tex
        assert r"\ifdefempty{\orgname}" not in tex

    def test_letterhead_reclaims_only_when_empty(self):
        tex = self._tex({"header": "letterhead"})
        assert (
            "\\ifdefempty{\\orgname}{\\ifdefempty{\\brandlogo}{%\n"
            "  \\geometry{top=\kxreclaimtop, headheight=0pt, headsep=0pt, includehead=false}%"
        ) in tex

    def test_logo_header_reclaims_only_when_the_logo_is_empty(self):
        tex = self._tex({"header": "logo"})
        assert "\\ifdefempty{\\brandlogo}{%\n  \\geometry{top=\kxreclaimtop" in tex
        assert "\\ifdefempty{\\orgname}{\\ifdefempty" not in tex

    def test_custom_header_owns_its_geometry(self):
        tex = self._tex({"header": "letterhead"}, header_source=r"\fancyhead[L]{Egen}")
        assert "includehead=false" not in tex

    # --- header fields -----------------------------------------------------

    def test_header_fields_emit_contract_macros(self):
        tex = self._tex(
            {
                "header": {
                    "variant": "letterhead",
                    "fields": {"org_name": "Föreningen X", "logo": "logo.pdf"},
                }
            }
        )
        assert r"\renewcommand{\orgname}{Föreningen X}" in tex
        assert r"\renewcommand{\brandlogo}{logo.pdf}" in tex
        assert tex.index(r"\renewcommand{\orgname}") < tex.index(r"\fancyhead[L]")

    def test_unset_header_fields_are_not_emitted(self):
        tex = self._tex({"header": {"variant": "letterhead", "fields": {"org_name": "X"}}})
        assert r"\renewcommand{\orgphone}" not in tex

    # --- footer fields vs. settings ----------------------------------------

    def test_title_alone_is_not_a_fields_footer(self):
        tex = self._tex({"footer": {"variant": "pagenumber", "title": True}})
        assert r"\usepackage{klartex-footer}" not in tex
        assert r"\fancyfoot[C]" in tex

    def test_footer_fields_emit_kxfooter(self):
        tex = self._tex({"footer": {"variant": "columns", "fields": {"company": "Bolaget AB"}}})
        assert r"\usepackage{klartex-footer}" in tex
        assert "company={Bolaget AB}" in tex

    def test_custom_header_keeps_the_predefined_fields_footer(self):
        tex = self._tex(
            {"footer": {"variant": "columns", "fields": {"company": "Bolaget AB"}}},
            header_source=r"\fancyhead[L]{Egen}",
        )
        assert r"\fancyhead[L]{Egen}" in tex
        assert r"\usepackage{klartex-footer}" in tex
        assert r"\fancyhead[L]{%" not in tex

    def test_custom_footer_keeps_the_predefined_header(self):
        tex = self._tex(
            {"header": "letterhead", "first_page_header": False},
            footer_source=r"\fancyfoot[C]{\thepage}",
        )
        assert r"\fancyhead[L]{%" in tex
        assert r"\fancyfoot[C]{\thepage}" in tex
        assert r"\thispagestyle{plain}" in tex

    def test_custom_footer_owns_page_numbers(self):
        tex = self._tex(
            {"header": "letterhead", "page_numbers": False},
            footer_source=r"\fancyfoot[C]{\thepage}",
        )
        assert r"\fancyfoot[C]{}" not in tex
