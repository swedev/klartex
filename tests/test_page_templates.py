"""Tests for the page template system."""

import pytest

from klartex.page_templates import (
    PageTemplate,
    list_page_templates,
    list_slot_variants,
    load_page_template,
    read_page_template_source,
    read_slot_source,
    render_fragment,
)


class TestLoadPageTemplate:
    """Tests for loading page templates."""

    def test_load_formal(self):
        pt = load_page_template("formal")
        assert pt.name == "formal"
        assert pt.page_numbers is True

    def test_load_clean(self):
        pt = load_page_template("clean")
        assert pt.name == "clean"

    def test_load_none(self):
        pt = load_page_template("none")
        assert pt.name == "none"
        assert pt.first_page_header is False

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown page template"):
            load_page_template("nonexistent")


class TestPageTemplateOverrides:
    """Tests for page template object-form with overrides."""

    def test_string_shorthand(self):
        pt = load_page_template("formal")
        assert pt.page_numbers is True
        assert pt.first_page_header is True

    def test_object_with_overrides(self):
        pt = load_page_template({"name": "formal", "page_numbers": False})
        assert pt.name == "formal"
        assert pt.page_numbers is False
        assert pt.first_page_header is True  # default preserved

    def test_object_override_first_page_header(self):
        pt = load_page_template(
            {"name": "formal", "first_page_header": False}
        )
        assert pt.first_page_header is False
        assert pt.page_numbers is True  # default preserved

    def test_object_multiple_overrides(self):
        pt = load_page_template(
            {"name": "clean", "page_numbers": False, "first_page_header": False}
        )
        assert pt.page_numbers is False
        assert pt.first_page_header is False


class TestReadPageTemplateSource:
    """Tests for reading page template file content."""

    def test_read_formal(self):
        source = read_page_template_source("formal")
        assert "fancyhead" in source or "fancyfoot" in source

    def test_read_clean(self):
        source = read_page_template_source("clean")
        assert len(source) > 0

    def test_read_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            read_page_template_source("nonexistent")


class TestListPageTemplates:
    """Tests for listing available page templates."""

    def test_returns_all(self):
        templates = list_page_templates()
        names = [t["name"] for t in templates]
        assert "formal" in names
        assert "clean" in names
        assert "none" in names

    def test_does_not_include_branded(self):
        templates = list_page_templates()
        names = [t["name"] for t in templates]
        assert "branded" not in names

    def test_includes_description(self):
        templates = list_page_templates()
        formal = next(t for t in templates if t["name"] == "formal")
        assert formal["description"]

    def test_includes_defaults(self):
        templates = list_page_templates()
        formal = next(t for t in templates if t["name"] == "formal")
        assert "page_numbers" in formal["defaults"]


class TestFontAndFooterOverrides:
    """font/header_font/footer page-template options."""

    def test_defaults_empty(self):
        pt = load_page_template("formal")
        assert pt.font is None
        assert pt.header_font is None
        assert pt.footer.fields == {}
        assert pt.footer.has_fields is False
        assert pt.footer_has_payment is False

    def test_font_and_header_font(self):
        pt = load_page_template(
            {"name": "formal", "font": "Futura", "header_font": "Georgia"}
        )
        assert pt.font == "Futura"
        assert pt.header_font == "Georgia"

    def test_header_font_defaults_to_font(self):
        pt = load_page_template({"name": "formal", "font": "Futura"})
        assert pt.header_font == "Futura"

    def test_footer_has_payment(self):
        pt = load_page_template(
            {"name": "formal", "footer": {"bankgiro": "1234-5678"}}
        )
        assert pt.footer_has_payment is True

    def test_footer_without_payment_fields(self):
        pt = load_page_template(
            {"name": "formal", "footer": {"company": "Bolaget AB"}}
        )
        assert pt.footer.fields == {"company": "Bolaget AB"}
        assert pt.footer.has_fields is True
        assert pt.footer_has_payment is False


class TestDiffStyle:
    """diff_style page-template option (how an addition is marked)."""

    def test_defaults_to_color(self):
        assert load_page_template("formal").diff_style == "color"

    def test_underline_override_is_carried(self):
        pt = load_page_template({"name": "clean", "diff_style": "underline"})
        assert pt.diff_style == "underline"


class TestAliases:
    """The three legacy names resolve to slot combinations."""

    def test_formal(self):
        pt = load_page_template("formal")
        assert pt.header.variant == "letterhead"
        assert pt.footer.variant == "standard"
        assert pt.footer.settings["title"] is True
        assert pt.footer.has_fields is False
        assert pt.first_page_header is True
        assert pt.name == "formal"

    def test_clean(self):
        pt = load_page_template("clean")
        assert pt.header.variant == "logo"
        assert pt.footer.variant == "standard"
        assert pt.footer.settings.get("title", False) is False
        assert pt.first_page_header is True

    def test_none(self):
        pt = load_page_template("none")
        assert pt.header.is_empty
        assert pt.footer.variant == "standard"
        assert pt.first_page_header is False


class TestSlotForm:
    """The header/footer slot object form."""

    def test_header_variant_string(self):
        pt = load_page_template({"header": "logo"}, default="none")
        assert pt.header.variant == "logo"
        assert pt.footer.variant == "standard"
        assert pt.first_page_header is True

    def test_null_header_is_empty(self):
        pt = load_page_template({"header": None}, default="none")
        assert pt.header.is_empty
        assert pt.first_page_header is False

    def test_null_footer_is_empty(self):
        pt = load_page_template({"footer": None}, default="none")
        assert pt.footer.is_empty

    def test_header_settings(self):
        pt = load_page_template(
            {
                "header": {
                    "variant": "letterhead",
                    "org_name": "Föreningen",
                    "logo": "logo.pdf",
                }
            },
            default="none",
        )
        assert pt.header.variant == "letterhead"
        assert pt.header.settings == {
            "org_name": "Föreningen",
            "logo": "logo.pdf",
        }

    def test_footer_fields_without_variant(self):
        pt = load_page_template({"footer": {"company": "Bolaget AB"}}, default="none")
        assert pt.footer.variant == "standard"
        assert pt.footer.fields == {"company": "Bolaget AB"}
        assert pt.footer.has_fields is True

    def test_footer_title_is_not_a_field(self):
        pt = load_page_template(
            {"footer": {"title": True, "company": "X"}}, default="none"
        )
        assert pt.footer.fields == {"company": "X"}
        assert pt.footer.settings["title"] is True

    def test_title_only_footer_has_no_fields(self):
        pt = load_page_template({"footer": {"title": True}}, default="none")
        assert pt.footer.has_fields is False

    def test_alias_then_slot_override(self):
        pt = load_page_template({"name": "clean", "footer": None})
        assert pt.header.variant == "logo"
        assert pt.footer.is_empty

    def test_formal_equals_its_slot_spelling(self):
        alias = load_page_template("formal")
        slots = load_page_template(
            {"header": "letterhead", "footer": {"title": True}}, default="none"
        )
        assert slots.header == alias.header
        assert slots.footer == alias.footer
        assert slots.page_numbers == alias.page_numbers
        assert slots.first_page_header == alias.first_page_header


class TestSlotErrors:
    """Unknown variants and settings are rejected by the loader."""

    def test_footer_variant_in_header_slot(self):
        with pytest.raises(ValueError, match="header") as exc:
            load_page_template({"header": "standard"}, default="none")
        assert "letterhead, logo" in str(exc.value)

    def test_header_variant_in_footer_slot(self):
        with pytest.raises(ValueError, match="footer"):
            load_page_template({"footer": "letterhead"}, default="none")

    def test_header_object_requires_variant(self):
        with pytest.raises(ValueError, match="variant"):
            load_page_template({"header": {"org_name": "X"}}, default="none")

    def test_setting_not_allowed_by_variant(self):
        with pytest.raises(ValueError, match="org_name"):
            load_page_template(
                {"header": {"variant": "logo", "org_name": "X"}}, default="none"
            )

    def test_footer_page_numbers_is_reserved(self):
        with pytest.raises(ValueError, match="page_numbers"):
            load_page_template({"footer": {"page_numbers": True}}, default="none")

    def test_unknown_alias(self):
        with pytest.raises(ValueError, match="Unknown page template"):
            load_page_template({"name": "bogus"})


class TestCustomSources:
    """Per-slot and monolithic custom sources."""

    def test_header_source_only(self):
        pt = load_page_template("formal", header_source="% h")
        assert pt.header.is_custom
        assert pt.header.source == "% h"
        assert pt.footer.variant == "standard"
        assert pt.footer.settings["title"] is True

    def test_both_sources(self):
        pt = load_page_template("formal", header_source="% h", footer_source="% f")
        assert pt.header.is_custom
        assert pt.footer.is_custom

    def test_monolithic_tolerates_unknown_name(self):
        pt = load_page_template("bogus", page_template_source="% m")
        assert pt.header.is_custom
        assert pt.footer.is_custom
        assert pt.footer.shared_source is True
        assert pt.name == "custom"

    def test_monolithic_tolerates_missing_name(self):
        pt = load_page_template(None, page_template_source="% m")
        assert pt.header.is_custom
        assert pt.name == "custom"

    def test_monolithic_keeps_document_level_settings(self):
        pt = load_page_template(
            {"name": "bogus", "font": "Futura", "footer": {"company": "X"}},
            page_template_source="% m",
        )
        assert pt.font == "Futura"
        assert pt.footer.is_custom
        assert pt.footer.fields == {}


class TestSlotListing:
    """list_slot_variants() for agent discovery."""

    def test_lists_both_slots(self):
        variants = list_slot_variants()
        assert [v["name"] for v in variants["header"]] == ["letterhead", "logo"]
        assert [v["name"] for v in variants["footer"]] == ["standard"]

    def test_variants_have_descriptions(self):
        variants = list_slot_variants()
        for slot_variants in variants.values():
            for variant in slot_variants:
                assert variant["description"]


class TestSlotSources:
    """Reading and rendering the fragment sources."""

    def test_composed_alias_source(self):
        source = read_page_template_source("formal")
        assert "fancyhead" in source
        assert "fancyfoot" in source
        assert "includehead=false" in source

    def test_read_header_fragment(self):
        assert r"\fancyhead[L]" in read_slot_source("header", "letterhead")

    def test_read_footer_fragment(self):
        assert r"\fancyfoot[C]" in read_slot_source("footer", "standard")

    def test_render_fragment_with_title(self):
        assert r"\doctitle" in render_fragment("footer", "standard", {"title": True})

    def test_render_fragment_without_title(self):
        assert r"\doctitle" not in render_fragment("footer", "standard", {})

    def test_unknown_fragment_raises(self):
        with pytest.raises(FileNotFoundError):
            read_slot_source("header", "nonexistent")
