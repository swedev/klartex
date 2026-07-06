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
    "protokoll", "faktura", "kvitto",
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

    def test_kvitto_discovered(self):
        registry = get_registry()
        assert "kvitto" in registry
        info = registry["kvitto"]
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


def _render_recipe_tex(template_name: str, data: dict) -> str:
    """Helper: run the recipe pre-compile pipeline, return the LaTeX source."""
    from klartex.renderer import _render_recipe
    from klartex.tex_escape import escape_data

    info = get_registry()[template_name]
    return _render_recipe(info, escape_data(data))


def test_faktura_missing_currency_defaults_to_sek():
    """extract_component_data inserts None for missing data_map paths, so the
    template must not rely on dict-get defaults (the key exists, value None)."""
    import jsonschema

    data = json.loads((FIXTURES / "faktura.json").read_text())
    del data["currency"]
    jsonschema.validate(data, get_registry()["faktura"].get_validation_schema())

    tex = _render_recipe_tex("faktura", data)
    assert " None" not in tex
    assert "SEK" in tex


def test_kvitto_zero_amount_renders_missing_amount_empty():
    """amount: 0 must render as 0.00; a missing amount gives an empty cell.
    total_amount is authoritative and always rendered."""
    data = {
        "receipt_number": "K-1",
        "date": "2026-07-06",
        "total_amount": 100,
        "items": [
            {"description": "Gratisrad", "amount": 0},
            {"description": "Rad utan belopp"},
        ],
    }
    tex = _render_recipe_tex("kvitto", data)
    assert r"Gratisrad & 0.00 \\" in tex
    assert r"Rad utan belopp &  \\" in tex
    assert "100.00" in tex


def test_kvitto_minimal_payload_skips_metadata_list():
    """Without payment_method/paid_by all optional metadata is dropped and the
    description_list component must render nothing (no empty tabularx)."""
    data = {
        "receipt_number": "K-2",
        "date": "2026-07-06",
        "total_amount": 50,
        "items": [{"description": "Avgift"}],
    }
    tex = _render_recipe_tex("kvitto", data)
    assert r"\begin{tabularx}{\linewidth}" not in tex  # description_list table
    assert "Betalsätt" not in tex
    assert " None" not in tex


def test_xelatex_timeout_raises_runtime_error(monkeypatch):
    """TimeoutExpired must be translated to the pipeline's RuntimeError contract."""
    import subprocess

    from klartex import renderer as renderer_mod

    monkeypatch.setattr(renderer_mod.shutil, "which", lambda _: "/usr/bin/xelatex")

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="xelatex", timeout=60)

    monkeypatch.setattr(renderer_mod.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="timed out"):
        renderer_mod._compile_tex("\\documentclass{article}\\begin{document}x\\end{document}")
