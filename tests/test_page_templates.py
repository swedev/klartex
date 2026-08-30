"""Tests for the page template system."""

import pytest

from klartex.page_templates import (
    BLOCK_DEFAULT_SLOTS,
    RECIPE_DEFAULT_SLOTS,
    list_slot_variants,
    load_page_template,
    read_slot_source,
    render_fragment,
)

LETTERHEAD_TITLE = {"header": "letterhead", "footer": {"variant": "pagenumber", "title": True}}


class TestDefaults:
    """A slot the payload leaves out takes the surface's default."""

    def test_none_spec_uses_block_defaults(self):
        pt = load_page_template(None)
        assert pt.header.is_empty
        assert pt.footer.variant == "pagenumber"
        assert pt.page_numbers is True
        assert pt.first_page_header is False

    def test_empty_object_equals_none_spec(self):
        assert load_page_template({}) == load_page_template(None)

    def test_recipe_defaults(self):
        pt = load_page_template(None, defaults=RECIPE_DEFAULT_SLOTS)
        assert pt.header.variant == "letterhead"
        assert pt.footer.variant == "pagenumber"
        assert pt.footer.settings["title"] is True
        assert pt.footer.has_fields is False
        assert pt.first_page_header is True

    def test_partial_object_keeps_the_default_for_the_other_slot(self):
        pt = load_page_template({"footer": None}, defaults=RECIPE_DEFAULT_SLOTS)
        assert pt.header.variant == "letterhead"
        assert pt.footer.is_empty

    def test_string_spec_is_rejected(self):
        with pytest.raises(ValueError, match="must be an object"):
            load_page_template("formal")

    def test_unknown_key_is_rejected(self):
        with pytest.raises(ValueError, match="name"):
            load_page_template({"name": "formal"})


class TestPageTemplateOverrides:
    """Document-level keys on the page_template object."""

    def test_page_numbers_override(self):
        pt = load_page_template({**LETTERHEAD_TITLE, "page_numbers": False})
        assert pt.page_numbers is False
        assert pt.first_page_header is True  # default preserved

    def test_first_page_header_override(self):
        pt = load_page_template({**LETTERHEAD_TITLE, "first_page_header": False})
        assert pt.first_page_header is False
        assert pt.page_numbers is True  # default preserved

    def test_multiple_overrides(self):
        pt = load_page_template(
            {"header": "logo", "page_numbers": False, "first_page_header": False}
        )
        assert pt.page_numbers is False
        assert pt.first_page_header is False


class TestFontAndFooterOverrides:
    """font/header_font/footer page-template options."""

    def test_defaults_empty(self):
        pt = load_page_template(LETTERHEAD_TITLE)
        assert pt.font is None
        assert pt.header_font is None
        assert pt.footer.fields == {}
        assert pt.footer.has_fields is False
        assert pt.footer_has_payment is False

    def test_font_and_header_font(self):
        pt = load_page_template({"font": "Futura", "header_font": "Georgia"})
        assert pt.font == "Futura"
        assert pt.header_font == "Georgia"

    def test_header_font_defaults_to_font(self):
        pt = load_page_template({"font": "Futura"})
        assert pt.header_font == "Futura"

    def test_footer_has_payment(self):
        pt = load_page_template({"footer": {"variant": "columns", "fields": {"bankgiro": "1234-5678"}}})
        assert pt.footer_has_payment is True

    def test_footer_without_payment_fields(self):
        pt = load_page_template({"footer": {"variant": "columns", "fields": {"company": "Bolaget AB"}}})
        assert pt.footer.fields == {"company": "Bolaget AB"}
        assert pt.footer.has_fields is True
        assert pt.footer_has_payment is False


class TestDiffStyle:
    """diff_style page-template option (how an addition is marked)."""

    def test_defaults_to_color(self):
        assert load_page_template({}).diff_style == "color"

    def test_underline_override_is_carried(self):
        pt = load_page_template({"header": "logo", "diff_style": "underline"})
        assert pt.diff_style == "underline"


class TestSlotForm:
    """The header/footer slot object form."""

    def test_header_variant_string(self):
        pt = load_page_template({"header": "logo"})
        assert pt.header.variant == "logo"
        assert pt.footer.variant == "pagenumber"
        assert pt.first_page_header is True

    def test_null_header_is_empty(self):
        pt = load_page_template({"header": None})
        assert pt.header.is_empty
        assert pt.first_page_header is False

    def test_null_footer_is_empty(self):
        pt = load_page_template({"footer": None})
        assert pt.footer.is_empty

    def test_header_fields(self):
        pt = load_page_template(
            {
                "header": {
                    "variant": "letterhead",
                    "fields": {"org_name": "Föreningen", "logo": "logo.pdf"},
                }
            }
        )
        assert pt.header.variant == "letterhead"
        assert pt.header.fields == {"org_name": "Föreningen", "logo": "logo.pdf"}
        assert pt.header.has_fields is True

    def test_flat_header_field_is_rejected(self):
        with pytest.raises(ValueError, match="org_name"):
            load_page_template({"header": {"variant": "letterhead", "org_name": "X"}})

    def test_columns_footer(self):
        pt = load_page_template({"footer": {"variant": "columns", "fields": {"company": "Bolaget AB"}}})
        assert pt.footer.variant == "columns"
        assert pt.footer.fields == {"company": "Bolaget AB"}
        assert pt.footer.has_fields is True

    def test_footer_object_requires_variant(self):
        with pytest.raises(ValueError, match="variant"):
            load_page_template({"footer": {"fields": {"company": "X"}}})

    def test_title_is_not_a_columns_setting(self):
        with pytest.raises(ValueError, match="title"):
            load_page_template({"footer": {"variant": "columns", "title": True}})

    def test_fields_is_not_a_pagenumber_setting(self):
        with pytest.raises(ValueError, match="fields"):
            load_page_template({"footer": {"variant": "pagenumber", "fields": {"company": "X"}}})

    def test_flat_footer_field_is_rejected(self):
        with pytest.raises(ValueError, match="company"):
            load_page_template({"footer": {"variant": "columns", "company": "X"}})

    def test_unknown_footer_field_is_rejected(self):
        with pytest.raises(ValueError, match="bogus"):
            load_page_template({"footer": {"variant": "columns", "fields": {"bogus": "X"}}})

    def test_fields_must_be_an_object(self):
        with pytest.raises(ValueError, match="object"):
            load_page_template({"footer": {"variant": "columns", "fields": "X"}})

    def test_title_only_footer_has_no_fields(self):
        pt = load_page_template({"footer": {"variant": "pagenumber", "title": True}})
        assert pt.footer.has_fields is False


class TestSlotErrors:
    """Unknown variants and settings are rejected by the loader."""

    def test_footer_variant_in_header_slot(self):
        with pytest.raises(ValueError, match="header") as exc:
            load_page_template({"header": "standard"})
        assert "letterhead, logo" in str(exc.value)

    def test_header_variant_in_footer_slot(self):
        with pytest.raises(ValueError, match="footer"):
            load_page_template({"footer": "letterhead"})

    def test_header_object_requires_variant(self):
        with pytest.raises(ValueError, match="variant"):
            load_page_template({"header": {"fields": {"org_name": "X"}}})

    def test_field_not_allowed_by_variant(self):
        with pytest.raises(ValueError, match="org_name"):
            load_page_template({"header": {"variant": "logo", "fields": {"org_name": "X"}}})

    def test_footer_page_numbers_is_not_a_setting(self):
        with pytest.raises(ValueError, match="page_numbers"):
            load_page_template({"footer": {"variant": "pagenumber", "page_numbers": True}})


class TestCustomSources:
    """Per-slot custom sources."""

    def test_header_source_only(self):
        pt = load_page_template(LETTERHEAD_TITLE, header_source="% h")
        assert pt.header.is_custom
        assert pt.header.source == "% h"
        assert pt.footer.variant == "pagenumber"
        assert pt.footer.settings["title"] is True

    def test_both_sources(self):
        pt = load_page_template(LETTERHEAD_TITLE, header_source="% h", footer_source="% f")
        assert pt.header.is_custom
        assert pt.footer.is_custom


class TestSlotListing:
    """list_slot_variants() for agent discovery."""

    def test_lists_both_slots(self):
        variants = list_slot_variants()
        assert [v["name"] for v in variants["header"]] == ["letterhead", "logo"]
        assert [v["name"] for v in variants["footer"]] == ["pagenumber", "columns"]

    def test_variants_have_descriptions(self):
        variants = list_slot_variants()
        for slot_variants in variants.values():
            for variant in slot_variants:
                assert variant["description"]


class TestSlotSources:
    """Reading and rendering the fragment sources."""

    def test_read_header_fragment(self):
        assert r"\fancyhead[L]" in read_slot_source("header", "letterhead")

    def test_read_footer_fragment(self):
        assert r"\fancyfoot[C]" in read_slot_source("footer", "pagenumber")

    def test_render_fragment_with_title(self):
        assert r"\doctitle" in render_fragment("footer", "pagenumber", {"title": True})

    def test_render_fragment_without_title(self):
        assert r"\doctitle" not in render_fragment("footer", "pagenumber", {})

    def test_unknown_fragment_raises(self):
        with pytest.raises(FileNotFoundError):
            read_slot_source("header", "nonexistent")


class TestLetterheadRequiresOrgName:
    """The letterhead is built around the organisation name: the fragment and
    the reclaim test both key off \\orgname, so contact details supplied
    without it would be silently dropped."""

    @pytest.mark.parametrize(
        "fields",
        [
            {"email": "info@x.se"},
            {"address": "Storgatan 1"},
            {"web": "x.se", "phone": "070-1234567"},
            {"logo": "logo.pdf"},
            {"org_name": ""},
        ],
    )
    def test_object_form_without_org_name_raises(self, fields):
        with pytest.raises(ValueError, match="org_name"):
            load_page_template({"header": {"variant": "letterhead", "fields": fields}})

    def test_object_form_without_fields_raises(self):
        with pytest.raises(ValueError, match="org_name"):
            load_page_template({"header": {"variant": "letterhead"}})

    def test_variant_name_alone_is_allowed(self):
        """`"letterhead"` on its own carries no settings and resolves — that
        is the recipe default."""
        assert load_page_template({"header": "letterhead"}).header.variant == "letterhead"
        assert BLOCK_DEFAULT_SLOTS["header"] is None
