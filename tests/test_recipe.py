"""Tests for recipe loading, validation, and rendering."""

import json
import shutil
from pathlib import Path

import pytest
import jsonschema

from klartex.recipe import load_recipe, prepare_recipe_context, Recipe

FIXTURES = Path(__file__).parent / "fixtures"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"

HAS_XELATEX = shutil.which("xelatex") is not None


class TestLoadRecipe:
    """Tests for recipe loading and validation."""

    def test_load_protokoll_recipe(self):
        recipe = load_recipe(TEMPLATES_DIR / "protokoll" / "recipe.yaml")
        assert recipe.name == "protokoll"
        assert recipe.lang == "sv"
        assert len(recipe.components) > 0
        assert recipe.schema_path == "schema.json"

    def test_recipe_has_expected_components(self):
        recipe = load_recipe(TEMPLATES_DIR / "protokoll" / "recipe.yaml")
        component_types = [c.type for c in recipe.components]
        assert "heading" in component_types
        assert "klausuler" in component_types

    def test_recipe_document_section(self):
        recipe = load_recipe(TEMPLATES_DIR / "protokoll" / "recipe.yaml")
        assert "formal" in recipe.document.page_template
        assert len(recipe.document.metadata) > 0

    def test_recipe_component_specs_resolved(self):
        recipe = load_recipe(TEMPLATES_DIR / "protokoll" / "recipe.yaml")
        for comp in recipe.components:
            assert comp.spec is not None, f"Component '{comp.type}' has no resolved spec"

    def test_invalid_recipe_rejected(self, tmp_path):
        """A recipe missing required fields should fail validation."""
        bad_recipe = tmp_path / "recipe.yaml"
        bad_recipe.write_text("components: []\n")
        with pytest.raises(jsonschema.ValidationError):
            load_recipe(bad_recipe)

    def test_unknown_component_rejected(self, tmp_path):
        """A recipe with an unknown component type should fail."""
        recipe_yaml = tmp_path / "recipe.yaml"
        recipe_yaml.write_text(
            """
template:
  name: test
  description: test
document: {}
components:
  - type: nonexistent_component
"""
        )
        with pytest.raises(ValueError, match="Unknown component"):
            load_recipe(recipe_yaml)

    def test_recipe_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_recipe(Path("/nonexistent/recipe.yaml"))


class TestPrepareRecipeContext:
    """Tests for recipe context preparation."""

    def test_context_has_required_keys(self):
        recipe = load_recipe(TEMPLATES_DIR / "protokoll" / "recipe.yaml")
        data = json.loads((FIXTURES / "protokoll.json").read_text())
        ctx = prepare_recipe_context(recipe, data)
        assert "recipe" in ctx
        assert "data" in ctx
        assert "title" in ctx
        assert "components" in ctx
        assert "metadata" in ctx

    def test_title_rendered_from_data(self):
        recipe = load_recipe(TEMPLATES_DIR / "protokoll" / "recipe.yaml")
        data = json.loads((FIXTURES / "protokoll.json").read_text())
        ctx = prepare_recipe_context(recipe, data)
        assert "Styrelsemöte" in ctx["title"]
        assert "2026-02-10" in ctx["title"]

    def test_metadata_resolved(self):
        recipe = load_recipe(TEMPLATES_DIR / "protokoll" / "recipe.yaml")
        data = json.loads((FIXTURES / "protokoll.json").read_text())
        ctx = prepare_recipe_context(recipe, data)
        labels = [m["label"] for m in ctx["metadata"]]
        assert "Datum:" in labels

    def test_optional_metadata_skipped_when_missing(self):
        recipe = load_recipe(TEMPLATES_DIR / "protokoll" / "recipe.yaml")
        data = json.loads((FIXTURES / "protokoll.json").read_text())
        del data["location"]  # This is optional in the recipe
        ctx = prepare_recipe_context(recipe, data)
        labels = [m["label"] for m in ctx["metadata"]]
        assert "Plats:" not in labels

    def test_component_data_extracted(self):
        recipe = load_recipe(TEMPLATES_DIR / "protokoll" / "recipe.yaml")
        data = json.loads((FIXTURES / "protokoll.json").read_text())
        ctx = prepare_recipe_context(recipe, data)
        # Find the klausuler component
        klausuler = [c for c in ctx["components"] if c["type"] == "klausuler"]
        assert len(klausuler) == 1
        assert klausuler[0]["data"]["items"] == data["agenda_items"]


class TestRecipeEscaping:
    """Tests for LaTeX escaping safety in recipe rendering."""

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_special_chars_in_recipe_data(self):
        """LaTeX special characters in data should be escaped in recipe output."""
        from klartex.renderer import render

        data = json.loads((FIXTURES / "protokoll.json").read_text())
        data["agenda_items"][0]["discussion"] = "Budget: 50% of $1000 for A & B"
        pdf_bytes = render("protokoll", data)
        assert pdf_bytes[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_injection_like_input_neutralized(self):
        """Injection-like input should be escaped and rendered as literal text."""
        from klartex.renderer import render

        data = json.loads((FIXTURES / "protokoll.json").read_text())
        data["agenda_items"][0]["title"] = r"\input{/etc/passwd}"
        pdf_bytes = render("protokoll", data)
        assert pdf_bytes[:5] == b"%PDF-"

    @pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
    def test_braces_in_recipe_data(self):
        """Braces in data should be escaped in recipe output."""
        from klartex.renderer import render

        data = json.loads((FIXTURES / "protokoll.json").read_text())
        data["attendees"][0] = "Name {with} braces"
        pdf_bytes = render("protokoll", data)
        assert pdf_bytes[:5] == b"%PDF-"
