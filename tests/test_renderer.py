"""Tests for the rendering pipeline."""

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from klartex.renderer import render, get_registry

FIXTURES = Path(__file__).parent / "fixtures"

HAS_XELATEX = shutil.which("xelatex") is not None


def test_unknown_template():
    with pytest.raises(ValueError, match="Unknown template"):
        render("nonexistent", {})


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
@pytest.mark.parametrize("template_name", ["protokoll", "faktura", "avtal"])
def test_render_pdf(template_name):
    data = json.loads((FIXTURES / f"{template_name}.json").read_text())
    pdf_bytes = render(template_name, data)
    assert pdf_bytes[:5] == b"%PDF-"
    assert len(pdf_bytes) > 1000


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
def test_render_with_special_chars():
    """Ensure LaTeX special chars in data don't break rendering."""
    data = json.loads((FIXTURES / "protokoll.json").read_text())
    data["agenda_items"][0]["discussion"] = "Budget: 50% of $1000 for A & B"
    pdf_bytes = render("protokoll", data)
    assert pdf_bytes[:5] == b"%PDF-"
