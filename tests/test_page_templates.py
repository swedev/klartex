"""Tests for the page template system."""

import pytest

from klartex.page_templates import (
    BLOCK_DEFAULT_SLOTS,
    HEADER_BAND_BOTTOM,
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


class TestMargins:
    """`margins` is the text-block geometry: paper edge to body text."""

    def test_absent_null_and_empty_all_mean_no_margins(self):
        for spec in ({}, {"margins": None}, {"margins": {}}):
            pt = load_page_template(spec)
            assert pt.margins == {}
            assert pt.margin_setup == ""

    def test_non_object_is_rejected(self):
        with pytest.raises(ValueError, match="margins must be an object"):
            load_page_template({"margins": "2cm"})

    def test_unknown_key_is_rejected(self):
        with pytest.raises(ValueError, match="Unknown margins key 'inner'"):
            load_page_template({"margins": {"inner": "2cm"}})

    @pytest.mark.parametrize("value", ["2,5cm", "2.5", "2.5em", "2.5 cm", "-2cm", 2.5, True])
    def test_values_must_be_latex_dimensions(self, value):
        with pytest.raises(ValueError, match="margins.left must be a LaTeX dimension"):
            load_page_template({"margins": {"left": value}})

    @pytest.mark.parametrize("value", ["2cm", "25mm", "0cm", "1in", "72.27pt"])
    def test_supported_units_and_zero(self, value):
        assert load_page_template({"margins": {"left": value}}).margins["left"] == value

    def test_geometry_keys_pass_through_verbatim(self):
        setup = load_page_template({"margins": {"left": "2cm", "right": "3cm", "bottom": "25mm"}}).margin_setup
        assert r"\geometry{left=2cm, right=3cm, bottom=25mm}" in setup

    def test_side_margin_syncs_the_header_band_width(self):
        """fancyhdr's \\headwidth does not track a later \\textwidth."""
        assert r"\setlength{\headwidth}{\textwidth}" in load_page_template(
            {"margins": {"left": "2cm"}}
        ).margin_setup
        assert r"\setlength{\headwidth}{\textwidth}" in load_page_template(
            {"margins": {"right": "2cm"}}
        ).margin_setup
        assert r"\headwidth" not in load_page_template({"margins": {"bottom": "2cm"}}).margin_setup

    def test_top_is_emitted_for_both_regimes(self):
        """Which top regime applies is decided at LaTeX time by the reclaim's
        \\ifdefempty tests, so both pieces are always emitted."""
        setup = load_page_template({"header": None, "margins": {"top": "3cm"}}).margin_setup
        assert r"\renewcommand{\kxreclaimtop}{3cm}" in setup
        assert r"\geometry{headsep=\dimexpr 3cm-" + HEADER_BAND_BOTTOM + r"\relax}" in setup

    def test_bottom_moves_the_columns_footer_geometry(self):
        """\\kxfooter enlarges the bottom geometry for its band; the renewals
        make the user's bottom the value it enlarges to, band clearance kept."""
        setup = load_page_template({"margins": {"bottom": "3cm"}}).margin_setup
        assert r"\renewcommand{\kxfooterbottom}{3cm}" in setup
        assert r"\renewcommand{\kxfooterfootskip}{\dimexpr 3cm-1cm\relax}" in setup

    def test_no_footer_renewals_without_bottom(self):
        assert "kxfooterbottom" not in load_page_template({"margins": {"top": "4cm"}}).margin_setup

    def test_full_setup_output(self):
        pt = load_page_template(
            {"header": None, "margins": {"top": "3.5cm", "bottom": "2cm", "left": "2cm", "right": "2cm"}}
        )
        assert pt.margin_setup == "\n".join([
            r"\renewcommand{\kxreclaimtop}{3.5cm}",
            r"\renewcommand{\kxfooterbottom}{2cm}",
            r"\renewcommand{\kxfooterfootskip}{\dimexpr 2cm-1cm\relax}",
            r"\geometry{left=2cm, right=2cm, bottom=2cm, headsep=\dimexpr 3.5cm-2.1cm\relax}",
            r"\setlength{\headwidth}{\textwidth}",
        ])


class TestMarginTopMinimum:
    """A top at or below the header band's bottom edge leaves no header–text
    gap — rejected wherever Python can tell the header renders."""

    LETTERHEAD = {"variant": "letterhead", "fields": {"org_name": "Föreningen X"}}
    LOGO = {"variant": "logo", "fields": {"logo": "logo.pdf"}}

    @pytest.mark.parametrize("header", [LETTERHEAD, LOGO])
    @pytest.mark.parametrize("top", ["2.1cm", "21mm", "1cm", "0cm"])
    def test_rejected_with_a_rendering_header(self, header, top):
        with pytest.raises(ValueError, match="margins.top must be greater"):
            load_page_template({"header": header, "margins": {"top": top}})

    @pytest.mark.parametrize("header", [LETTERHEAD, LOGO])
    def test_accepted_just_above_the_band(self, header):
        pt = load_page_template({"header": header, "margins": {"top": "2.11cm"}})
        assert pt.margins["top"] == "2.11cm"

    @pytest.mark.parametrize(
        "header",
        [None, "letterhead", "logo"],
        ids=["empty", "content-less letterhead", "content-less logo"],
    )
    def test_reclaimed_header_takes_any_positive_top(self, header):
        """narrowmargins reclaims to 1.7cm, so small values are legitimate."""
        pt = load_page_template({"header": header, "margins": {"top": "1.7cm"}})
        assert r"\renewcommand{\kxreclaimtop}{1.7cm}" in pt.margin_setup

    def test_custom_header_source_owns_its_geometry(self):
        pt = load_page_template({"margins": {"top": "1cm"}}, header_source="% custom")
        assert pt.margins["top"] == "1cm"
