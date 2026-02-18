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


class TestEngineSelection:
    """Tests for the engine selection logic."""

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_auto_uses_legacy_when_both_exist(self):
        """auto mode should use .tex.jinja when both exist (protokoll has both)."""
        data = json.loads((FIXTURES / "protokoll.json").read_text())
        # auto should produce a valid PDF (using legacy path since .tex.jinja exists)
        pdf_auto = render("protokoll", data, engine="auto")
        assert pdf_auto[:5] == b"%PDF-"
        assert len(pdf_auto) > 1000

    def test_auto_selects_legacy_path(self):
        """auto mode should select legacy path when .tex.jinja exists."""
        from klartex.renderer import _select_engine
        from klartex.registry import TemplateInfo

        info = TemplateInfo(
            name="test", description="", schema={},
            template_path=Path("/fake/test.tex.jinja"),
            recipe_path=Path("/fake/recipe.yaml"),
        )
        result = _select_engine(info, "auto")
        assert result is False  # False means use legacy

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_recipe_mode_forces_recipe_path(self):
        """engine='recipe' should use recipe.yaml even when .tex.jinja exists."""
        data = json.loads((FIXTURES / "protokoll.json").read_text())
        pdf = render("protokoll", data, engine="recipe")
        assert pdf[:5] == b"%PDF-"
        assert len(pdf) > 1000

    def test_legacy_mode_errors_without_tex_jinja(self):
        """engine='legacy' should error when no .tex.jinja exists."""
        # faktura has .tex.jinja, so we need a template without one
        # We test via the _select_engine helper
        from klartex.renderer import _select_engine
        from klartex.registry import TemplateInfo

        info = TemplateInfo(
            name="test", description="", schema={},
            template_path=None,
            recipe_path=Path("/fake/recipe.yaml"),
        )
        with pytest.raises(ValueError, match="no .tex.jinja"):
            _select_engine(info, "legacy")

    def test_recipe_mode_errors_without_recipe(self):
        """engine='recipe' should error when no recipe.yaml exists."""
        from klartex.renderer import _select_engine
        from klartex.registry import TemplateInfo

        info = TemplateInfo(
            name="test", description="", schema={},
            template_path=Path("/fake/test.tex.jinja"),
            recipe_path=None,
        )
        with pytest.raises(ValueError, match="no recipe.yaml"):
            _select_engine(info, "recipe")

    def test_invalid_engine_value(self):
        """Invalid engine value should raise."""
        from klartex.renderer import _select_engine
        from klartex.registry import TemplateInfo

        info = TemplateInfo(name="test", description="", schema={})
        with pytest.raises(ValueError, match="Invalid engine"):
            _select_engine(info, "invalid")

    def test_auto_uses_recipe_when_no_legacy(self):
        """auto mode should use recipe when no .tex.jinja exists."""
        from klartex.renderer import _select_engine
        from klartex.registry import TemplateInfo

        info = TemplateInfo(
            name="test", description="", schema={},
            template_path=None,
            recipe_path=Path("/fake/recipe.yaml"),
        )
        result = _select_engine(info, "auto")
        assert result is True  # True means use recipe


class TestDiscovery:
    """Tests for template discovery with recipe support."""

    def test_protokoll_discovered_with_both_engines(self):
        registry = get_registry()
        assert "protokoll" in registry
        info = registry["protokoll"]
        assert info.has_legacy
        assert info.has_recipe

    def test_faktura_legacy_only(self):
        registry = get_registry()
        assert "faktura" in registry
        info = registry["faktura"]
        assert info.has_legacy
        assert not info.has_recipe

    def test_avtal_legacy_only(self):
        registry = get_registry()
        assert "avtal" in registry
        info = registry["avtal"]
        assert info.has_legacy
        assert not info.has_recipe
