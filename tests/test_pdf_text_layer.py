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


def _text_layer(pdf: bytes) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "doc.pdf"
        path.write_bytes(pdf)
        out = subprocess.run(
            ["pdftotext", "-q", str(path), "-"],
            capture_output=True,
            check=True,
            timeout=60,
        )
    # pdftotext wraps lines at the rendered line breaks; join so a phrase
    # that wrapped in the PDF is still found as one string.
    return " ".join(out.stdout.decode("utf-8").split())


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
        "page_template": {"name": "clean", "diff_style": "underline"},
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
