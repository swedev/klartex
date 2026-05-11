"""Tests for the rendering pipeline."""

import json
import shutil
from pathlib import Path

import pytest

from klartex.renderer import render, get_registry

FIXTURES = Path(__file__).parent / "fixtures"

HAS_XELATEX = shutil.which("xelatex") is not None


def test_unknown_template():
    with pytest.raises(ValueError, match="Unknown template"):
        render("nonexistent", {})


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
@pytest.mark.parametrize("template_name", [
    "protokoll", "faktura",
    "resultatrakning", "balansrakning", "budgetrapport", "sie-exportrapport",
])
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


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
def test_render_resolves_asset_dir(tmp_path):
    """Files in asset_dir should be resolvable by xelatex via TEXINPUTS."""
    # Put a snippet only findable through asset_dir
    (tmp_path / "brand-colors.tex").write_text(
        r"\definecolor{brandprimary}{HTML}{2E5A1C}"
    )
    page_template = (
        r"\input{brand-colors}"
        "\n"
        r"\fancyhead[L]{\color{brandprimary}Test}"
        "\n"
        r"\fancyfoot[C]{\thepage}"
        "\n"
    )
    data = {"body": [{"type": "heading", "text": "Asset dir test"}]}

    # With asset_dir: \input resolves, render succeeds
    pdf = render(
        "_block", data, page_template_source=page_template, asset_dir=tmp_path
    )
    assert pdf[:5] == b"%PDF-"

    # Without asset_dir: \input cannot find brand-colors.tex, xelatex halts
    with pytest.raises(RuntimeError, match="xelatex failed"):
        render("_block", data, page_template_source=page_template)


class TestDiscovery:
    """Tests for template discovery."""

    def test_protokoll_discovered(self):
        registry = get_registry()
        assert "protokoll" in registry
        info = registry["protokoll"]
        assert info.recipe_path is not None

    def test_faktura_discovered(self):
        registry = get_registry()
        assert "faktura" in registry
        info = registry["faktura"]
        assert info.recipe_path is not None

    def test_financial_templates_discovered(self):
        registry = get_registry()
        for name in ["resultatrakning", "balansrakning", "budgetrapport", "sie-exportrapport"]:
            assert name in registry, f"{name} not discovered"
            assert registry[name].recipe_path is not None

    def test_block_engine_discovered(self):
        registry = get_registry()
        assert "_block" in registry
        assert registry["_block"].is_block_engine
