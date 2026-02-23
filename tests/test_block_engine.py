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
            "page_template": "formal",
            "lang": "sv",
            "body": [{"type": "heading", "text": "Test"}],
        }
        ctx = prepare_block_context(data)
        assert "body" in ctx
        assert "lang" in ctx
        assert "page_template_source" in ctx
        assert "doc_title" in ctx

    def test_missing_body_raises(self):
        with pytest.raises(ValueError, match="body"):
            prepare_block_context({"page_template": "formal"})

    def test_default_page_template(self):
        data = {"body": [{"type": "heading", "text": "Test"}]}
        ctx = prepare_block_context(data)
        # page_template_source is now the raw file content
        assert "fancyhead" in ctx["page_template_source"] or "fancyfoot" in ctx["page_template_source"]

    def test_page_template_object(self):
        data = {
            "page_template": {"name": "clean", "page_numbers": False},
            "body": [{"type": "heading", "text": "Test"}],
        }
        ctx = prepare_block_context(data)
        assert isinstance(ctx["page_template_source"], str)
        assert len(ctx["page_template_source"]) > 0
        assert ctx["page_template"].page_numbers is False

    def test_caller_provided_source_overrides(self):
        data = {"body": [{"type": "heading", "text": "Test"}]}
        custom_source = "% custom page template"
        ctx = prepare_block_context(data, page_template_source=custom_source)
        assert ctx["page_template_source"] == custom_source

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
        """A signatures block with only 1 party should fail validation."""
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "signatures", "parties": [{"name": "Solo"}]},
            ],
        }
        with pytest.raises(ValueError, match="Invalid 'signatures' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_underscore_block_types_render(self):
        """Block types with underscores (title_page, metadata_table) must render."""
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "title_page", "title": "Test", "party1": "A", "party2": "B"},
                {"type": "heading", "text": "Test Document"},
                {
                    "type": "metadata_table",
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
    def test_page_template_clean(self):
        """Block engine with clean page template renders."""
        from klartex.renderer import render

        data = {
            "page_template": "clean",
            "body": [
                {"type": "heading", "text": "Clean Template Test"},
                {"type": "text", "text": "This uses the clean page template."},
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_page_template_none(self):
        """Block engine with no page template renders."""
        from klartex.renderer import render

        data = {
            "page_template": "none",
            "body": [
                {"type": "heading", "text": "No Header Test"},
                {"type": "text", "text": "This uses no page template."},
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_metadata_table_block(self):
        """Metadata table block renders."""
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "heading", "text": "Meeting Notes"},
                {
                    "type": "metadata_table",
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
    def test_attendees_block(self):
        """Attendees block renders."""
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "heading", "text": "Meeting"},
                {
                    "type": "attendees",
                    "attendees": ["Alice", "Bob", "Charlie"],
                    "adjusters": ["Alice", "Bob"],
                },
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


class TestSignaturesFeatures:
    """Tests for signatures signatory/title fallback and adjuster_signatures."""

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
    def test_adjuster_signatures_renders(self):
        """Adjuster signatures block should render valid PDF."""
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "heading", "text": "Protokoll"},
                {
                    "type": "adjuster_signatures",
                    "adjusters": ["Anna Andersson", "Erik Eriksson"],
                },
            ],
        }
        pdf = render(BLOCK_ENGINE_TEMPLATE, data)
        assert pdf[:5] == b"%PDF-"

    def test_adjuster_signatures_missing_adjusters_raises(self):
        """Adjuster signatures without adjusters should fail schema validation."""
        from klartex.renderer import render

        data = {
            "body": [
                {"type": "adjuster_signatures"},
            ],
        }
        with pytest.raises(ValueError, match="Invalid 'adjuster_signatures' block"):
            render(BLOCK_ENGINE_TEMPLATE, data)


class TestRecipeTemplatesStillWork:
    """Ensure recipe templates are unaffected by block engine changes."""

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_protokoll_still_works(self):
        from klartex.renderer import render

        data = json.loads((FIXTURES / "protokoll.json").read_text())
        pdf = render("protokoll", data)
        assert pdf[:5] == b"%PDF-"

