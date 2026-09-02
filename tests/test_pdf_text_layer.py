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

_WORD_BOX = re.compile(
    r'<word xMin="([0-9.]+)" yMin="([0-9.]+)" xMax="[0-9.]+" yMax="[0-9.]+">([^<]*)</word>'
)


def _word_box(pdf: bytes, word: str) -> tuple[float, float]:
    """``(xMin, yMin)`` of ``word`` on the first page, in PDF units."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "doc.pdf"
        path.write_bytes(pdf)
        out = subprocess.run(
            ["pdftotext", "-q", "-bbox", "-f", "1", "-l", "1", str(path), "-"],
            capture_output=True,
            check=True,
            timeout=60,
        )
    for x_min, y_min, text in _WORD_BOX.findall(out.stdout.decode("utf-8")):
        if text == word:
            return float(x_min), float(y_min)
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
