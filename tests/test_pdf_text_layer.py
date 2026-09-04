"""Round-trip guard: characters that go in must come out of the PDF.

The escape pass, the smart-quote pass and fontspec's glyph coverage all sit
between a JSON string and the text a reader can select in the finished PDF.
None of them announce a character they drop. These tests render real
documents, pull the text layer back out with ``pdftotext``, and assert the
characters survived — so a silently swallowed glyph fails CI instead of
reaching a finished document.

The battery deliberately covers what Swedish association and legal paperwork
actually contains: quotation marks (which klartex generates itself, from
plain ``"``), section signs, dashes, ellipsis, currency, accented letters.
"""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from klartex.block_engine import BLOCK_ENGINE_TEMPLATE
from klartex.renderer import render

HAS_XELATEX = shutil.which("xelatex") is not None
HAS_PDFTOTEXT = shutil.which("pdftotext") is not None

requires_tools = pytest.mark.skipif(
    not (HAS_XELATEX and HAS_PDFTOTEXT),
    reason="needs xelatex and pdftotext (poppler-utils)",
)

# Each entry is rendered on its own line and must come back verbatim.
BATTERY = [
    "sektion § 12 och § 7",
    "sid. 5–7 och 2020–2024",
    "en paus — mitt i satsen",
    "ellips… och slut",
    "hundra % av 2,5 kr",
    "grader 21° och euro 40 €",
    "åäö ÅÄÖ éüøæ",
    "gåsögon «citat» slut",
]


def _raw_text_layer(pdf: bytes) -> str:
    """The untouched ``pdftotext`` output, page separators (\\f) intact."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "doc.pdf"
        path.write_bytes(pdf)
        out = subprocess.run(
            ["pdftotext", "-q", str(path), "-"],
            capture_output=True,
            check=True,
            timeout=60,
        )
    return out.stdout.decode("utf-8")


def _text_layer(pdf: bytes) -> str:
    # pdftotext wraps lines at the rendered line breaks; join so a phrase
    # that wrapped in the PDF is still found as one string.
    return " ".join(_raw_text_layer(pdf).split())


def _pages(pdf: bytes) -> list[str]:
    """Text-layer pages, whitespace-normalized, trailing empties dropped."""
    pages = [" ".join(page.split()) for page in _raw_text_layer(pdf).split("\f")]
    while pages and not pages[-1]:
        pages.pop()
    return pages


@requires_tools
def test_battery_survives_plain_text():
    data = {
        "lang": "sv",
        "body": [{"type": "text", "text": phrase} for phrase in BATTERY],
    }
    text = _text_layer(render(BLOCK_ENGINE_TEMPLATE, data))
    for phrase in BATTERY:
        assert phrase in text, f"dropped from plain text: {phrase!r}"


@requires_tools
def test_battery_survives_change_markers():
    """Marked spans go through inline_markup and the change macros, which is
    where a styling mechanism would corrupt them."""
    data = {
        "lang": "sv",
        "body": [
            {"type": "text", "text": f"före {{+{phrase}+}} efter"} for phrase in BATTERY
        ]
        + [{"type": "text", "text": f"före [-{phrase}-] efter"} for phrase in BATTERY],
    }
    text = _text_layer(render(BLOCK_ENGINE_TEMPLATE, data))
    for phrase in BATTERY:
        assert phrase in text, f"dropped from a change marker: {phrase!r}"


@requires_tools
def test_battery_survives_underlined_additions():
    data = {
        "lang": "sv",
        "page_template": {"header": "logo", "diff_style": "underline"},
        "body": [
            {"type": "text", "text": f"före {{+{phrase}+}} efter"} for phrase in BATTERY
        ],
    }
    text = _text_layer(render(BLOCK_ENGINE_TEMPLATE, data))
    for phrase in BATTERY:
        assert phrase in text, f"dropped under diff_style=underline: {phrase!r}"


@requires_tools
def test_generated_quotation_marks_survive():
    """klartex turns "citat" into ”citat” itself, so the quotation marks are
    the pipeline's own output rather than the author's input."""
    data = {
        "lang": "sv",
        "body": [
            {"type": "text", "text": 'styrelsen beslutade om "avgiften" i mars'},
            {"type": "text", "text": 'tillagt {+enligt "§ 12" i stadgarna+} här'},
        ],
    }
    text = _text_layer(render(BLOCK_ENGINE_TEMPLATE, data))
    assert "”avgiften”" in text
    assert "”§ 12”" in text


LOREM = (
    "Föreningens medlemmar samlas till ordinarie stämma för att behandla "
    "de ärenden som stadgarna föreskriver och de förslag som styrelsen lagt fram. "
)


@requires_tools
def test_paragraph_longer_than_a_page_breaks_onto_next_page():
    """A paragraph taller than the text block must break across pages.

    With a penalty array whose last value repeats for every remaining line,
    every interline break inside a paragraph is forbidden, xelatex reports an
    overfull \\vbox and clips the tail below the bottom margin. The clipped
    text is still absent from the text layer, so the marker word closing the
    paragraph is the decisive assertion — the page count alone is not, since
    the clipped render also produces two pages.
    """
    data = {
        "lang": "sv",
        "body": [{"type": "text", "text": LOREM * 60 + "SLUTMARKÖR"}],
    }
    pages = _pages(render(BLOCK_ENGINE_TEMPLATE, data))
    assert len(pages) >= 2, f"expected a multi-page render, got {len(pages)}"
    assert "SLUTMARKÖR" in pages[-1], "paragraph tail clipped instead of broken"


@requires_tools
def test_widow_and_orphan_penalties_keep_the_two_line_policy():
    """The 1- and 2-line widow/orphan protection must survive the fix.

    Dropping the penalty arrays entirely would also let long paragraphs break,
    so assert the actual values: forbidden (10000) for the first two lines from
    either edge, free (0) beyond them.
    """
    probe = (
        r"W1=\the\widowpenalties 1. "
        r"W2=\the\widowpenalties 2. "
        r"W3=\the\widowpenalties 3. "
        r"C1=\the\clubpenalties 1. "
        r"C2=\the\clubpenalties 2. "
        r"C3=\the\clubpenalties 3."
    )
    data = {"lang": "sv", "body": [{"type": "latex", "source": probe}]}
    text = _text_layer(render(BLOCK_ENGINE_TEMPLATE, data))
    assert "W1=10000." in text
    assert "W2=10000." in text
    assert "W3=0." in text
    assert "C1=10000." in text
    assert "C2=10000." in text
    assert "C3=0." in text


def _two_page_body(heading: str) -> list[dict]:
    """A body long enough to be paginated, so `Sida 1 av 2` is meaningful."""
    return [
        {"type": "heading", "text": heading},
        {"type": "text", "text": LOREM * 30},
    ]


@requires_tools
def test_title_footer_carries_the_title_and_page_count():
    data = {
        "lang": "sv",
        "page_template": {"footer": {"variant": "pagenumber", "title": True}},
        "body": _two_page_body("Kallelse till stämma"),
    }
    pages = _pages(render(BLOCK_ENGINE_TEMPLATE, data))
    assert len(pages) >= 2, f"expected a multi-page render, got {len(pages)}"
    assert "Kallelse till stämma • Sida 1 av 2" in pages[0]


def _one_page_body() -> list[dict]:
    return [{"type": "heading", "text": "Kallelse"}, {"type": "text", "text": LOREM}]


def _footer_pages(footer, body):
    data = {"lang": "sv", "page_template": {"footer": footer}, "body": body}
    return _pages(render(BLOCK_ENGINE_TEMPLATE, data))


COLUMNS_FIELDS = {"company": "Bolaget AB", "org_number": "556123-4567"}


@requires_tools
@pytest.mark.parametrize(
    "footer,body,expected",
    [
        # pagenumber — auto is the default and prints nothing on one page.
        ("pagenumber", _one_page_body(), None),
        ({"variant": "pagenumber", "page_numbers": "auto"}, _one_page_body(), None),
        ({"variant": "pagenumber", "page_numbers": "on"}, _one_page_body(), "Sida 1 av 1"),
        ({"variant": "pagenumber", "page_numbers": "off"}, _two_page_body("Kallelse"), None),
        ({"variant": "pagenumber", "page_numbers": "auto"}, _two_page_body("Kallelse"), "Sida 1 av 2"),
        # columns — the same three modes on the multi-column footer.
        ({"variant": "columns", "fields": COLUMNS_FIELDS}, _one_page_body(), None),
        ({"variant": "columns", "fields": COLUMNS_FIELDS}, _two_page_body("Kallelse"), "Sida 1 av 2"),
        (
            {"variant": "columns", "page_numbers": "off", "fields": COLUMNS_FIELDS},
            _two_page_body("Kallelse"),
            None,
        ),
        (
            {"variant": "columns", "page_numbers": "on", "fields": COLUMNS_FIELDS},
            _one_page_body(),
            "Sida 1 av 1",
        ),
    ],
)
def test_page_number_modes_on_both_footer_variants(footer, body, expected):
    """auto/on/off decide the page number at LaTeX time, on the slot that
    carries it. `None` means no page number anywhere in the document."""
    pages = _footer_pages(footer, body)
    if expected is None:
        for page in pages:
            assert "Sida" not in page
    else:
        assert expected in pages[0]


@requires_tools
def test_title_footer_prints_the_title_alone_on_a_one_page_document():
    """The mode governs the page number, not the footer: under `auto` a
    one-page titled document keeps its title and drops the number and its
    separator."""
    data = {
        "lang": "sv",
        "page_template": {"footer": {"variant": "pagenumber", "title": True}},
        "body": _one_page_body(),
    }
    pages = _pages(render(BLOCK_ENGINE_TEMPLATE, data))
    assert len(pages) == 1
    assert "Kallelse" in pages[0]
    assert "Sida" not in pages[0]
    assert "•" not in pages[0]


@requires_tools
def test_faktura_footer_page_numbers_survive_the_derived_fields():
    """The recipe's columns footer derives its fields from the payload; a
    `page_numbers` the payload sets on that slot must survive the merge."""
    data = {
        "invoice_number": "F-1",
        "date": "2026-08-06",
        "due_date": "2026-09-05",
        "sender": {"name": "Säljbolaget AB", "org_number": "556123-4567"},
        "recipient": {"name": "Kund AB"},
        "lines": [{"description": "Tjänst", "quantity": 1, "unit_price": 100.0}],
        "page_template": {"footer": {"variant": "columns", "page_numbers": "on"}},
    }
    pages = _pages(render("faktura", data))
    assert len(pages) == 1
    assert "Sida 1 av 1" in pages[0]


@requires_tools
def test_letterhead_settings_reach_the_printed_page():
    """Structured header content is what the slot model adds: no custom LaTeX,
    and the organisation still ends up in the header's text layer."""
    data = {
        "lang": "sv",
        "page_template": {
            "header": {
                "variant": "letterhead",
                "fields": {
                    "org_name": "Föreningen Klartex",
                    "address": "Storgatan 1, 123 45 Stad",
                    "web": "klartex.se",
                    "email": "info@klartex.se",
                },
            }
        },
        "body": _two_page_body("Kallelse"),
    }
    pages = _pages(render(BLOCK_ENGINE_TEMPLATE, data))
    assert "Föreningen Klartex" in pages[0]
    assert "Storgatan 1, 123 45 Stad" in pages[0]
    assert "info@klartex.se" in pages[0]


@requires_tools
def test_both_slots_empty_leaves_no_chrome():
    data = {
        "lang": "sv",
        "page_template": {"header": None, "footer": None},
        "body": _two_page_body("Kallelse"),
    }
    pages = _pages(render(BLOCK_ENGINE_TEMPLATE, data))
    assert len(pages) >= 2
    for page in pages:
        assert "Sida" not in page


@requires_tools
@pytest.mark.parametrize(
    "contact",
    [
        {"email": "info@klartex.se"},
        {"phone": "070-123 45 67"},
        {"email": "info@klartex.se", "phone": "070-123 45 67"},
        {"web": "klartex.se", "phone": "070-123 45 67"},
    ],
)
def test_letterhead_contact_column_survives_empty_leading_fields(contact):
    """The contact column separator must be emitted only between lines that
    render. An unconditional one makes a column whose leading field is empty
    fail with "There's no line here to end", so this asserts both that the
    render succeeds and that the value reaches the page."""
    data = {
        "lang": "sv",
        "page_template": {
            "header": {"variant": "letterhead", "fields": {"org_name": "Föreningen X", **contact}}
        },
        "body": _two_page_body("Kallelse"),
    }
    pages = _pages(render(BLOCK_ENGINE_TEMPLATE, data))
    assert "Föreningen X" in pages[0]
    for value in contact.values():
        assert value in pages[0]


# --- margins: where the body text actually lands ---------------------------

#: PDF user-space units per centimetre (a unit is 1/72 in).
_PT_PER_CM = 72 / 2.54

#: A word's box in the ``pdftotext -bbox`` output. The coordinates are
#: signed: a glyph that hangs off an edge of the page gets a negative
#: ordinate, and that is exactly the case the containment tests below are
#: written to catch — an unsigned pattern would drop such a word from the
#: list instead, and the assertion would never see it.
_WORD_BOX = re.compile(
    r'<word xMin="(-?[0-9.]+)" yMin="(-?[0-9.]+)" '
    r'xMax="(-?[0-9.]+)" yMax="(-?[0-9.]+)">([^<]*)</word>'
)

#: One first-page word: ``(xMin, yMin, xMax, yMax, text)``. y grows downwards
#: from the top of the page, so a smaller yMin is higher up.
WordBox = tuple[float, float, float, float, str]


def _word_boxes(pdf: bytes) -> list[WordBox]:
    """Every word on the first page, in reading order, in PDF units."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "doc.pdf"
        path.write_bytes(pdf)
        out = subprocess.run(
            ["pdftotext", "-q", "-bbox", "-f", "1", "-l", "1", str(path), "-"],
            capture_output=True,
            check=True,
            timeout=60,
        )
    return [
        (float(x_min), float(y_min), float(x_max), float(y_max), text)
        for x_min, y_min, x_max, y_max, text in _WORD_BOX.findall(out.stdout.decode("utf-8"))
    ]


def _word_box(pdf: bytes, word: str) -> tuple[float, float]:
    """``(xMin, yMin)`` of ``word`` on the first page, in PDF units."""
    for x_min, y_min, _x_max, _y_max, text in _word_boxes(pdf):
        if text == word:
            return x_min, y_min
    raise AssertionError(f"{word!r} not found in the first page's bbox output")


def _anchor_payload(header, margins=None) -> dict:
    page_template: dict = {"header": header}
    if margins is not None:
        page_template["margins"] = margins
    return {
        "lang": "sv",
        "page_template": page_template,
        "body": [{"type": "text", "text": "Ankarord i brödtexten."}],
    }


LETTERHEAD = {"variant": "letterhead", "fields": {"org_name": "Föreningen X"}}


@requires_tools
@pytest.mark.parametrize(
    "header, top, expected_shift_cm",
    [
        # Header renders: the band stays put at 0.9cm + 1.2cm headheight and
        # the 1.3cm header-text gap absorbs the change, from 3.4cm.
        (LETTERHEAD, "5cm", 5 - 3.4),
        # Header reclaimed: \kxreclaimtop carries the value, from 2cm.
        (None, "4cm", 4 - 2),
    ],
    ids=["header renders", "header reclaimed"],
)
def test_margin_top_moves_the_body_text_down_by_the_delta(header, top, expected_shift_cm):
    """Both top regimes must put the first line of body text where the
    text-block contract says — not merely compile."""
    base_y = _word_box(render(BLOCK_ENGINE_TEMPLATE, _anchor_payload(header)), "Ankarord")[1]
    moved_y = _word_box(
        render(BLOCK_ENGINE_TEMPLATE, _anchor_payload(header, {"top": top})), "Ankarord"
    )[1]
    assert moved_y - base_y == pytest.approx(expected_shift_cm * _PT_PER_CM, abs=0.5)


@requires_tools
def test_margin_left_moves_the_body_text_by_the_delta():
    """The side margin is measured to the body text, from the class's 3cm."""
    base_x = _word_box(render(BLOCK_ENGINE_TEMPLATE, _anchor_payload(None)), "Ankarord")[0]
    moved_x = _word_box(
        render(BLOCK_ENGINE_TEMPLATE, _anchor_payload(None, {"left": "2cm"})), "Ankarord"
    )[0]
    assert moved_x - base_x == pytest.approx((2 - 3) * _PT_PER_CM, abs=0.5)


# --- the letterhead's contact column: a long address must stay inside it ---

#: A4 in PDF units, and the class geometry's side margin (\kxsidemargin).
_A4_WIDTH_PT = 595.276
_SIDE_MARGIN_PT = 3 * _PT_PER_CM

#: The contact column's edges, as fractions of \textwidth. The letterhead
#: fragment lays the header out as a 0.30 details column, a 0.03 gap and a
#: 0.25 contact column, so the contact column runs from 0.33 to 0.58 across
#: the text block.
_TEXT_WIDTH_PT = _A4_WIDTH_PT - 2 * _SIDE_MARGIN_PT
_CONTACT_LEFT_PT = _SIDE_MARGIN_PT + 0.33 * _TEXT_WIDTH_PT
_CONTACT_RIGHT_PT = _SIDE_MARGIN_PT + 0.58 * _TEXT_WIDTH_PT

_LONG_EMAIL = "styrelsen@bostadsrattsforeningenekbacken.se"
_LONG_WEB = "www.bostadsrattsforeningenekbacken.se"
_LONG_URL = "https://www.bostadsrattsforeningenekbacken.se/styrelsen"

#: The words of ``_anchor_payload``'s body, and the anchor itself.
_ANCHOR = "Ankarord"
_BODY_WORDS = frozenset({_ANCHOR, "i", "brödtexten."})


def _letterhead_payload(fields: dict) -> dict:
    """The anchor payload with a letterhead and no footer. With the bottom of
    the page empty, every word that is not the body is a header word — which
    is what lets the tests below find the header without looking at where it
    landed vertically."""
    data = _anchor_payload({"variant": "letterhead", "fields": fields})
    data["page_template"]["footer"] = None
    return data


def _letterhead_columns(pdf: bytes) -> tuple[list[WordBox], list[WordBox], float]:
    """``(details column, contact column, the body anchor's yMin)``, each
    column in reading order.

    A header word is identified by *not* being body text, and the two columns
    are told apart by x — never by height on the page. A filter like "above
    the anchor" would hide the one word a containment test needs to see: the
    header line that descended into the body.
    """
    boxes = _word_boxes(pdf)
    anchor_y = next(b[1] for b in boxes if b[4] == _ANCHOR)
    header = sorted((b for b in boxes if b[4] not in _BODY_WORDS), key=lambda b: (b[1], b[0]))
    return (
        [b for b in header if b[0] < _CONTACT_LEFT_PT],
        [b for b in header if b[0] >= _CONTACT_LEFT_PT],
        anchor_y,
    )


def _unspaced(*values: str) -> str:
    """The values with all whitespace removed — the shape a wrapped column
    comes back as, since a break replaces no character and adds none."""
    return "".join("".join(v.split()) for v in values)


@requires_tools
@pytest.mark.parametrize(
    "field_name, address",
    [("email", _LONG_EMAIL), ("web", _LONG_WEB), ("web", _LONG_URL)],
    ids=["email", "www", "https"],
)
def test_a_long_letterhead_address_wraps_inside_the_contact_column(field_name, address):
    """The column forbids hyphenation, so without break opportunities the
    address is one unbreakable word that runs out over the logo and off the
    page. Unpatched, the email's xMax is 368.7 against a 331.7 edge."""
    data = _letterhead_payload({"org_name": "Brf Ekbacken", field_name: address})
    details, contact, _ = _letterhead_columns(render(BLOCK_ENGINE_TEMPLATE, data))
    assert contact, "no words found in the contact column"
    for x_min, _y_min, x_max, _y_max, text in details + contact:
        assert x_max <= _CONTACT_RIGHT_PT + 0.5, f"{text!r} overruns the contact column"
    # The breaks land at separators only, and nothing was clipped off the
    # page: the pieces reassemble to the address exactly.
    assert "".join(b[4] for b in contact) == address


@requires_tools
def test_the_tallest_realistic_contact_column_clears_the_page_and_the_body():
    """Break opportunities buy horizontal containment with vertical growth.
    The worst realistic letterhead — a three-line web address, a three-line
    email and a phone — must still sit inside the header band."""
    fields = {
        "org_name": "Brf Ekbacken",
        "address": "Storgatan 1, 123 45 Stad",
        "web": _LONG_URL,
        "email": _LONG_EMAIL,
        "phone": "070-123 45 67",
    }
    details, contact, anchor_y = _letterhead_columns(
        render(BLOCK_ENGINE_TEMPLATE, _letterhead_payload(fields))
    )
    # Every field came back whole. A word pushed off the page edge is missing
    # from the text layer entirely, so this is what makes the bounds below
    # assertions about the whole header rather than about its survivors.
    assert "".join(b[4] for b in details) == _unspaced(fields["org_name"], fields["address"])
    assert "".join(b[4] for b in contact) == _unspaced(
        fields["web"], fields["email"], fields["phone"]
    )
    for x_min, y_min, x_max, y_max, text in details + contact:
        assert y_min > 0, f"{text!r} runs off the top of the page"
        assert y_max < anchor_y, f"{text!r} reaches into the body text"


# --- the columns footer's company column: a long address must stay inside it ---

#: The footer's Företag column edges, as fractions of \textwidth.
#: klartex-footer lays the footer out as a 0.34 Adress column, a 0.30
#: Företag column and a 0.36 Betalning column, so Företag — which carries
#: phone, email and web — runs from 0.34 to 0.64 across the text block.
_COMPANY_LEFT_PT = _SIDE_MARGIN_PT + 0.34 * _TEXT_WIDTH_PT
_COMPANY_RIGHT_PT = _SIDE_MARGIN_PT + 0.64 * _TEXT_WIDTH_PT

#: A4 height in PDF units, for the footer's bottom edge.
_A4_HEIGHT_PT = 841.89


def _footer_payload(fields: dict) -> dict:
    """The anchor payload with a columns footer and no header."""
    data = _anchor_payload(None)
    data["page_template"]["footer"] = {"variant": "columns", "fields": fields}
    return data


def _footer_company_column(pdf: bytes) -> list[WordBox]:
    """The words of the footer's Företag column, in reading order.

    A word belongs to the column when it *starts* inside it, never when it
    fits inside it — the one word a containment test has to see is the one
    that started in the column and ran out of it.
    """
    boxes = _word_boxes(pdf)
    column = [b for b in boxes if _COMPANY_LEFT_PT - 0.5 <= b[0] < _COMPANY_RIGHT_PT - 0.5]
    return sorted(column, key=lambda b: (b[1], b[0]))


@requires_tools
@pytest.mark.parametrize(
    "field_name, address",
    [("email", _LONG_EMAIL), ("web", _LONG_WEB), ("web", _LONG_URL)],
    ids=["email", "www", "https"],
)
def test_a_long_footer_address_wraps_inside_the_company_column(field_name, address):
    """The footer's contact lines are tabular cells — a single unbreakable
    line each — so without a wrapping box a long address is set straight
    through the Betalning column and off the page."""
    data = _footer_payload({"org_number": "556123-4567", field_name: address})
    column = _footer_company_column(render(BLOCK_ENGINE_TEMPLATE, data))
    assert column, "no words found in the footer's company column"
    for x_min, _y_min, x_max, _y_max, text in column:
        assert x_max <= _COMPANY_RIGHT_PT + 0.5, f"{text!r} overruns the company column"
    # The label row above it aside, the pieces reassemble to the address
    # exactly: the breaks land at separators and nothing was clipped.
    assert "".join(b[4] for b in column) == _unspaced("Företag", "Org.nr", "556123-4567", address)


@requires_tools
def test_the_tallest_realistic_footer_column_clears_the_page_and_the_body():
    """Break opportunities buy horizontal containment with vertical growth,
    and the footer grows upwards from the foot baseline. The worst realistic
    company column must still sit between the body text and the page edge."""
    fields = {
        "company": "Brf Ekbacken",
        "address": ["Storgatan 1", "123 45 Stad"],
        "org_number": "556123-4567",
        "phone": "070-123 45 67",
        "email": _LONG_EMAIL,
        "web": _LONG_URL,
        "bankgiro": "1234-5678",
    }
    pdf = render(BLOCK_ENGINE_TEMPLATE, _footer_payload(fields))
    boxes = _word_boxes(pdf)
    anchor_bottom = next(b[3] for b in boxes if b[4] == _ANCHOR)
    column = _footer_company_column(pdf)
    assert "".join(b[4] for b in column) == _unspaced(
        "Företag",
        "Org.nr",
        fields["org_number"],
        fields["phone"],
        fields["email"],
        fields["web"],
    )
    for x_min, y_min, x_max, y_max, text in column:
        assert y_min > anchor_bottom, f"{text!r} reaches into the body text"
        assert y_max < _A4_HEIGHT_PT, f"{text!r} runs off the bottom of the page"


def _minimal_faktura(**extra) -> dict:
    data = {
        "invoice_number": "F-1",
        "date": "2026-08-06",
        "due_date": "2026-09-05",
        "sender": {"name": "Säljbolaget AB"},
        "recipient": {"name": "Kund AB"},
        "lines": [{"description": "Tjänst", "quantity": 1, "unit_price": 100.0}],
    }
    data.update(extra)
    return data


FOOTER_LABELS = ("Adress saknas", "Org.nr saknas", "Betalningsuppgifter saknas")


@requires_tools
def test_bare_faktura_names_its_footer_gaps_on_one_page():
    """An invoice with nothing but a seller's name still looks like one: the
    name in the header, the three-column footer on the page with its gaps
    named — and the columns footer's taller band does not push it to page two.
    """
    pages = _pages(render("faktura", _minimal_faktura()))
    assert len(pages) == 1, f"expected a one-page invoice, got {len(pages)}"
    assert "Säljbolaget AB" in pages[0]
    for label in FOOTER_LABELS:
        assert label in pages[0]


@requires_tools
def test_a_filled_faktura_footer_names_no_gaps():
    data = _minimal_faktura(
        sender={
            "name": "Säljbolaget AB",
            "address_line1": "Storgatan 1",
            "address_line2": "123 45 Stad",
            "org_number": "556111-2222",
        },
        bankgiro="1234-5678",
    )
    text = _text_layer(render("faktura", data))
    assert "556111-2222" in text
    assert "1234-5678" in text
    for label in FOOTER_LABELS:
        assert label not in text


@requires_tools
def test_label_mode_is_off_outside_the_invoice_recipes():
    """The same columns footer on a block-engine document drops the columns it
    has no content for, exactly as before."""
    data = {
        "lang": "sv",
        "page_template": {
            "footer": {"variant": "columns", "fields": {"company": "Föreningen"}}
        },
        "body": [{"type": "heading", "text": "Kallelse"}],
    }
    text = _text_layer(render(BLOCK_ENGINE_TEMPLATE, data))
    assert "Föreningen" in text
    for label in FOOTER_LABELS:
        assert label not in text


# --- the invoice recipes' own margins --------------------------------------

FIXTURES = Path(__file__).parent / "fixtures"

#: A word from each invoice fixture's body — not from the page-chrome header
#: or the derived footer, so its box measures the body text block and nothing
#: else — with the (xMin, yMin) it occupies at faktura and kvitto's own
#: margins: 2cm sides, 1.7cm top under a reclaimed header.
_INVOICE_BODY_ANCHORS = {
    "faktura": ("Betalningsvillkor:", 56.693, 253.276),
    "kvitto": ("Betalsätt", 56.693, 311.275),
}


@requires_tools
@pytest.mark.parametrize("template_name", sorted(_INVOICE_BODY_ANCHORS))
def test_invoice_body_text_sits_at_the_recipes_own_margins(template_name):
    """faktura and kvitto declare their geometry as recipe-default margins.
    The committed coordinates are where the body text lands, and the x is the
    2cm side margin itself — so the declaration cannot drift from the design
    without a failing assertion.
    """
    word, expected_x, expected_y = _INVOICE_BODY_ANCHORS[template_name]
    data = json.loads((FIXTURES / f"{template_name}.json").read_text())
    x, y = _word_box(render(template_name, data), word)
    assert x == pytest.approx(2 * _PT_PER_CM, abs=0.5)
    assert x == pytest.approx(expected_x, abs=0.5)
    assert y == pytest.approx(expected_y, abs=0.5)
