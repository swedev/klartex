"""Tests for the page template system."""

import pytest

from klartex.page_templates import (
    BLOCK_DEFAULT_SLOTS,
    CONTACT_BREAKS,
    HEADER_BAND_BOTTOM,
    RECIPE_DEFAULT_SLOTS,
    allow_breaks,
    font_files,
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


class TestFontSetup:
    """The fontspec commands the two font forms emit."""

    def test_name_form_setups(self):
        pt = load_page_template({"font": "Futura", "header_font": "Georgia"})
        assert pt.font_setup == r"\setmainfont{Futura}"
        assert pt.header_font_setup == (
            "\\newfontfamily\\kxheaderfontfamily{Georgia}\n"
            "\\renewcommand{\\kxheaderfont}{\\kxheaderfontfamily}"
        )

    def test_unset_fonts_emit_nothing(self):
        pt = load_page_template({})
        assert pt.font_setup == ""
        assert pt.header_font_setup == ""

    def test_file_form_emits_every_supplied_face(self):
        pt = load_page_template({
            "font": {
                "file": "Inter-Regular.ttf",
                "bold": "Inter-Bold.ttf",
                "italic": "Inter-Italic.ttf",
                "bold_italic": "Inter-BoldItalic.ttf",
            }
        })
        assert pt.font_setup == (
            r"\setmainfont{Inter-Regular.ttf}[Path=./, "
            r"BoldFont=Inter-Bold.ttf, ItalicFont=Inter-Italic.ttf, "
            r"BoldItalicFont=Inter-BoldItalic.ttf]"
        )

    def test_file_form_omits_the_faces_not_supplied(self):
        """An absent face is left to fontspec, which falls back to the regular
        face — no BoldFont option, and nothing synthesised."""
        pt = load_page_template({"font": {"file": "Inter-Regular.ttf"}})
        assert pt.font_setup == r"\setmainfont{Inter-Regular.ttf}[Path=./]"
        assert "BoldFont" not in pt.font_setup
        assert "AutoFakeBold" not in pt.font_setup

    def test_header_font_reuses_the_font_files(self):
        pt = load_page_template({
            "font": {"file": "Inter-Regular.ttf", "bold": "Inter-Bold.ttf"}
        })
        assert pt.header_font == pt.font
        assert pt.header_font_setup.startswith(
            r"\newfontfamily\kxheaderfontfamily{Inter-Regular.ttf}"
            r"[Path=./, BoldFont=Inter-Bold.ttf]"
        )

    def test_the_two_forms_mix(self):
        pt = load_page_template({
            "font": "Georgia", "header_font": {"file": "Inter-Regular.ttf"}
        })
        assert pt.font_setup == r"\setmainfont{Georgia}"
        assert r"\kxheaderfontfamily{Inter-Regular.ttf}[Path=./]" in pt.header_font_setup


class TestFontFileValidation:
    """The loader states the file form's contract itself, for callers that
    reach it without the JSON Schema."""

    def test_file_is_required(self):
        with pytest.raises(ValueError, match="requires 'file'"):
            load_page_template({"font": {"bold": "Inter-Bold.ttf"}})

    def test_unknown_face_key_is_rejected(self):
        with pytest.raises(ValueError, match="Unknown font key"):
            load_page_template({"font": {"file": "a.ttf", "black": "b.ttf"}})

    @pytest.mark.parametrize(
        "filename",
        [
            "Inter_Regular.ttf",   # underscore is a LaTeX special
            "fonts/Inter.ttf",     # no directory part
            "../Inter.ttf",
            "Inter.TTF",           # lowercase extension only
            "Inter.woff2",
            "Inter",
            "-Inter.ttf",          # must start alphanumeric
            "Inter.ttf\n",         # a trailing newline is not a name
        ],
    )
    def test_rejected_filenames(self, filename):
        with pytest.raises(ValueError, match="must be a font file name"):
            load_page_template({"font": {"file": filename}})

    def test_wrong_type_is_rejected(self):
        with pytest.raises(ValueError, match="header_font must be"):
            load_page_template({"header_font": 7})


class TestFontFiles:
    """font_files() is what the renderer preflights."""

    def test_no_files_for_the_name_form(self):
        assert font_files({"font": "Georgia", "header_font": "Arial"}) == []
        assert font_files(None) == []

    def test_every_referenced_face_once_in_reference_order(self):
        files = font_files({
            "font": {"file": "Reg.ttf", "bold": "Bold.ttf"},
            "header_font": {"file": "Reg.ttf", "italic": "It.otf"},
        })
        assert files == ["Reg.ttf", "Bold.ttf", "It.otf"]


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


class TestWholePageSource:
    """page_template_source owns both slots — one source for the design."""

    def test_both_slots_carry_the_source_and_the_footer_is_shared(self):
        pt = load_page_template({}, page_template_source="% whole")
        assert pt.header.is_custom
        assert pt.footer.is_custom
        assert pt.header.source == pt.footer.source == "% whole"
        assert pt.footer.shared_source is True
        assert pt.header.shared_source is False

    def test_a_per_slot_source_is_not_shared(self):
        pt = load_page_template({}, header_source="% h", footer_source="% f")
        assert pt.header.shared_source is False
        assert pt.footer.shared_source is False

    def test_payload_slots_are_not_read_for_composition(self):
        pt = load_page_template(LETTERHEAD_TITLE, page_template_source="% whole")
        assert pt.header.variant is None
        assert pt.footer.variant is None
        assert pt.header.source == "% whole"

    def test_document_level_settings_still_apply(self):
        pt = load_page_template(
            {
                "font": "Futura",
                "header_font": "Helvetica",
                "diff_style": "underline",
                "margins": {"top": "1cm"},
            },
            page_template_source="% whole",
        )
        assert pt.font == "Futura"
        assert pt.header_font == "Helvetica"
        assert pt.diff_style == "underline"
        assert pt.margins["top"] == "1cm"

    def test_the_source_owns_its_geometry_so_a_small_top_is_allowed(self):
        """_check_margin_top only guards a rendering predefined header."""
        pt = load_page_template({"margins": {"top": "1cm"}}, page_template_source="% w")
        assert pt.margins["top"] == "1cm"

    def test_header_reclaim_is_empty(self):
        pt = load_page_template({}, page_template_source="% whole")
        assert not pt.header_reclaim

    @pytest.mark.parametrize("slot", ["header_source", "footer_source"])
    def test_cannot_be_combined_with_a_slot_source(self, slot):
        with pytest.raises(ValueError, match="cannot be combined"):
            load_page_template({}, page_template_source="% w", **{slot: "% s"})


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


class TestLogoFileName:
    """The logo name is emitted verbatim into \\renewcommand{\\brandlogo}{…},
    so the loader states the contract the schema states."""

    @pytest.mark.parametrize(
        "logo",
        [
            "my_logo.pdf", "a&b.pdf", "logo%.pdf", "",
            # Python's `$` also matches before a final newline, and the
            # negated class would otherwise swallow the newline itself.
            "logo.pdf\n", "logo.pdf\r", "logo.pdf x", " logo.pdf",
            2.5, None, True,
        ],
    )
    def test_unsafe_names_are_rejected(self, logo):
        with pytest.raises(ValueError, match="fields.logo"):
            load_page_template({"header": {"variant": "logo", "fields": {"logo": logo}}})

    @pytest.mark.parametrize(
        "logo",
        ["logo.pdf", "../delat/logo.pdf", "branding/logo.pdf", "logotyp-åäö.pdf"],
    )
    def test_safe_names_pass(self, logo):
        pt = load_page_template({"header": {"variant": "logo", "fields": {"logo": logo}}})
        assert pt.header_macros == [("brandlogo", logo)]

    def test_the_letterhead_logo_is_checked_too(self):
        with pytest.raises(ValueError, match="fields.logo"):
            load_page_template(
                {
                    "header": {
                        "variant": "letterhead",
                        "fields": {"org_name": "X", "logo": "logo.pdf\n"},
                    }
                }
            )


class TestAddressBreaks:
    """The letterhead's contact column forbids hyphenation, so a web or email
    address — one unspaced token — gets explicit break opportunities."""

    LONG_EMAIL = "styrelsen@bostadsrattsforeningenekbacken.se"
    LONG_WEB = "www.bostadsrattsforeningenekbacken.se"

    @pytest.mark.parametrize(
        "value,expected",
        [
            (
                LONG_EMAIL,
                "styrelsen@\\allowbreak{}bostadsrattsforeningenekbacken.\\allowbreak{}se",
            ),
            (
                LONG_WEB,
                "www.\\allowbreak{}bostadsrattsforeningenekbacken.\\allowbreak{}se",
            ),
            # A run breaks as a whole: https:// must not split into "https:/".
            (
                "https://example.se/a",
                "https://\\allowbreak{}example.\\allowbreak{}se/\\allowbreak{}a",
            ),
        ],
    )
    def test_breaks_go_after_each_run_of_separators(self, value, expected):
        assert allow_breaks(value, CONTACT_BREAKS) == expected

    @pytest.mark.parametrize("value", ["https://", "slutar.", "a//", "utan separator"])
    def test_a_trailing_run_gets_no_insertion(self, value):
        assert allow_breaks(value, CONTACT_BREAKS) == value

    def test_escape_sequences_survive(self):
        """The value is already LaTeX-escaped, and the separator set never
        appears in an escape sequence, so none can be split."""
        assert allow_breaks("a\\_b@x.se", CONTACT_BREAKS) == (
            "a\\_b@\\allowbreak{}x.\\allowbreak{}se"
        )
        assert allow_breaks("100\\%@x.se", CONTACT_BREAKS) == "100\\%@\\allowbreak{}x.\\allowbreak{}se"

    def test_empty_separator_set_is_the_identity(self):
        assert allow_breaks(self.LONG_EMAIL, "") == self.LONG_EMAIL

    def test_header_macros_annotates_web_and_email_only(self):
        pt = load_page_template(
            {
                "header": {
                    "variant": "letterhead",
                    "fields": {
                        "org_name": "Brf Ekbacken",
                        "address": "Storgatan 1, 123 45 Stad",
                        "web": self.LONG_WEB,
                        "email": self.LONG_EMAIL,
                        "phone": "070-123 45 67",
                        "logo": "logo.pdf",
                    },
                }
            }
        )
        assert pt.header_macros == [
            ("orgname", "Brf Ekbacken"),
            ("orgaddress", "Storgatan 1, 123 45 Stad"),
            ("orgwebsite", allow_breaks(self.LONG_WEB, CONTACT_BREAKS)),
            ("orgemail", allow_breaks(self.LONG_EMAIL, CONTACT_BREAKS)),
            ("orgphone", "070-123 45 67"),
            ("brandlogo", "logo.pdf"),
        ]

    def test_the_logo_field_is_never_annotated(self):
        """LOGO is shared by both header variants and carries no separators
        flag, so the file name reaches \\includegraphics verbatim."""
        pt = load_page_template({"header": {"variant": "logo", "fields": {"logo": "a.b.pdf"}}})
        assert pt.header_macros == [("brandlogo", "a.b.pdf")]


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

    @pytest.mark.parametrize(
        "value",
        [
            "2,5cm", "2.5", "2.5em", "2.5 cm", "-2cm", 2.5, True,
            # Python's `$` also matches before a final newline, so an
            # unanchored check would let this through into \geometry.
            "2cm\n", "2cm\r", "2cm\nx", " 2cm", "2cm ",
        ],
    )
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
