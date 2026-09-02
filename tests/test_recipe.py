"""Tests for recipe loading, validation, and rendering."""

import json
import shutil
from pathlib import Path

import pytest
import jsonschema

from klartex.recipe import load_recipe, prepare_recipe_context, Recipe

FIXTURES = Path(__file__).parent / "fixtures"
TEMPLATES_DIR = Path(__file__).parent.parent / "klartex" / "templates"
SCHEMAS_DIR = Path(__file__).parent.parent / "klartex" / "schemas"

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
        assert "agenda" in component_types

    def test_partial_page_template_falls_back_per_slot(self, tmp_path):
        """A recipe.yaml naming only one slot must get the recipe default for
        the other, not crash at render with a KeyError (PR #80 review)."""
        import shutil as _shutil

        from klartex.page_templates import RECIPE_DEFAULT_SLOTS

        recipe_dir = tmp_path / "budgetrapport"
        _shutil.copytree(TEMPLATES_DIR / "budgetrapport", recipe_dir)
        yaml_path = recipe_dir / "recipe.yaml"
        text = yaml_path.read_text()
        assert "\ndocument:\n" in text
        yaml_path.write_text(text.replace(
            "\ndocument:\n",
            "\ndocument:\n  page_template: {header: null}\n",
        ))
        recipe = load_recipe(yaml_path)
        assert recipe.document.page_template == {
            "header": None,
            "footer": RECIPE_DEFAULT_SLOTS["footer"],
        }

    def test_recipe_document_section(self):
        recipe = load_recipe(TEMPLATES_DIR / "protokoll" / "recipe.yaml")
        from klartex.page_templates import RECIPE_DEFAULT_SLOTS

        assert recipe.document.page_template == RECIPE_DEFAULT_SLOTS
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


class TestFooterFieldsFrom:
    r"""`fields_from` on a recipe's footer slot is the recipe's declaration of
    where the footer's default content comes from. It is recipe syntax, not
    payload syntax, so `load_recipe` takes it off the slot object and checks
    it there — a typo must not survive to the first render."""

    def _write(self, tmp_path, document_body):
        recipe_yaml = tmp_path / "recipe.yaml"
        recipe_yaml.write_text(
            "template:\n"
            "  name: test\n"
            "  description: test\n"
            "document:\n" + document_body + "components: []\n"
        )
        return recipe_yaml

    def test_faktura_declares_its_derived_columns_footer(self):
        recipe = load_recipe(TEMPLATES_DIR / "faktura" / "recipe.yaml")
        assert recipe.document.page_template["footer"] == {"variant": "columns"}
        assert recipe.document.footer_fields_from["company"] == "sender.name"
        assert recipe.document.footer_fields_from["address"] == [
            "sender.address_line1",
            "sender.address_line2",
        ]
        assert recipe.document.footer_fields_from["bankgiro"] == "bankgiro"
        assert recipe.document.footer_fields_from_variant == "columns"
        assert recipe.document.label_missing_footer_fields is True

    def test_kvitto_derives_the_sender_fields_only(self):
        recipe = load_recipe(TEMPLATES_DIR / "kvitto" / "recipe.yaml")
        assert set(recipe.document.footer_fields_from) == {
            "company",
            "address",
            "org_number",
        }
        assert recipe.document.label_missing_footer_fields is True

    def test_protokoll_declares_neither(self):
        from klartex.page_templates import RECIPE_DEFAULT_SLOTS

        recipe = load_recipe(TEMPLATES_DIR / "protokoll" / "recipe.yaml")
        assert recipe.document.page_template == RECIPE_DEFAULT_SLOTS
        assert recipe.document.footer_fields_from == {}
        assert recipe.document.label_missing_footer_fields is False

    def test_unknown_destination_field_rejected(self, tmp_path):
        path = self._write(
            tmp_path,
            "  page_template:\n"
            "    footer:\n"
            "      variant: columns\n"
            "      fields_from:\n"
            "        compamy: sender.name\n",
        )
        with pytest.raises(ValueError, match="compamy"):
            load_recipe(path)

    def test_variant_without_fields_rejected(self, tmp_path):
        path = self._write(
            tmp_path,
            "  page_template:\n"
            "    footer:\n"
            "      variant: pagenumber\n"
            "      fields_from:\n"
            "        company: sender.name\n",
        )
        with pytest.raises(ValueError, match="pagenumber"):
            load_recipe(path)

    def test_map_outside_a_footer_slot_object_rejected(self, tmp_path):
        path = self._write(
            tmp_path,
            "  page_template:\n"
            "    footer: columns\n"
            "    fields_from:\n"
            "      company: sender.name\n",
        )
        with pytest.raises(ValueError, match="footer slot object"):
            load_recipe(path)

    def test_empty_path_list_rejected(self, tmp_path):
        path = self._write(
            tmp_path,
            "  page_template:\n"
            "    footer:\n"
            "      variant: columns\n"
            "      fields_from:\n"
            "        address: []\n",
        )
        with pytest.raises(ValueError, match="address"):
            load_recipe(path)

    def test_non_string_path_rejected(self, tmp_path):
        path = self._write(
            tmp_path,
            "  page_template:\n"
            "    footer:\n"
            "      variant: columns\n"
            "      fields_from:\n"
            "        company: 7\n",
        )
        with pytest.raises(ValueError, match="company"):
            load_recipe(path)

    def test_fields_and_fields_from_on_one_slot_rejected(self, tmp_path):
        path = self._write(
            tmp_path,
            "  page_template:\n"
            "    footer:\n"
            "      variant: columns\n"
            "      fields:\n"
            "        company: Bolaget AB\n"
            "      fields_from:\n"
            "        org_number: sender.org_number\n",
        )
        with pytest.raises(ValueError, match="not\n?\\s*both|both"):
            load_recipe(path)


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
        # Find the agenda component (replaced klausuler in v0.10)
        agenda = [c for c in ctx["components"] if c["type"] == "agenda"]
        assert len(agenda) == 1
        assert agenda[0]["data"]["items"] == data["agenda_items"]


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


class TestRecipeLanguageReachesInlineFilters:
    """The inline filters are `pass_context` and read `lang` from the render
    context. `_recipe_base.tex.jinja` must import the shared macros `with
    context`, or every recipe renders Swedish typography regardless of the
    recipe's own language (#47)."""

    RECIPE_YAML = """
template:
  name: entest
  description: English test recipe
  lang: en
document:
  title: "Test"
  metadata:
    - label: "Venue:"
      field: location
components:
  - type: description_list
    options:
      source: document.metadata
"""

    def _render(self, tmp_path, data):
        from klartex.renderer import _jinja_env
        from klartex.tex_escape import escape_data

        recipe_yaml = tmp_path / "recipe.yaml"
        recipe_yaml.write_text(self.RECIPE_YAML)
        recipe = load_recipe(recipe_yaml)
        context = prepare_recipe_context(recipe, escape_data(data))
        return _jinja_env.get_template("_recipe_base.tex.jinja").render(context)

    def test_english_recipe_gets_english_smart_quotes(self, tmp_path):
        tex = self._render(tmp_path, {"location": 'The "Blue" Room'})
        assert "The “Blue” Room" in tex
        assert "The ”Blue” Room" not in tex

    def test_swedish_recipe_keeps_swedish_smart_quotes(self):
        """The shipped sv recipes must be unaffected by the context change."""
        from klartex.renderer import get_registry, _render_recipe
        from klartex.tex_escape import escape_data

        data = json.loads((FIXTURES / "protokoll.json").read_text())
        data["location"] = 'Lokalen "Norden"'
        info = get_registry()["protokoll"]
        tex = _render_recipe(info, escape_data(data))
        assert "Lokalen ”Norden”" in tex
