"""Tests for the page template system."""

import pytest

from klartex.page_templates import (
    PageTemplate,
    list_page_templates,
    load_page_template,
    reset_cache,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Reset the page template cache before each test."""
    reset_cache()
    yield
    reset_cache()


class TestLoadPageTemplate:
    """Tests for loading page templates."""

    def test_load_formal(self):
        pt = load_page_template("formal")
        assert pt.name == "formal"
        assert pt.include == "_header_standard.jinja"
        assert pt.page_numbers is True

    def test_load_clean(self):
        pt = load_page_template("clean")
        assert pt.name == "clean"
        assert pt.include == "_header_minimal.jinja"

    def test_load_none(self):
        pt = load_page_template("none")
        assert pt.name == "none"
        assert pt.include == "_header_none.jinja"

    def test_load_branded(self):
        pt = load_page_template("branded")
        assert pt.name == "branded"
        assert pt.include == "_header_standard.jinja"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown page template"):
            load_page_template("nonexistent")


class TestPageTemplateOverrides:
    """Tests for page template object-form with overrides."""

    def test_string_shorthand(self):
        pt = load_page_template("formal")
        assert pt.page_numbers is True
        assert pt.first_page_header is True

    def test_object_with_overrides(self):
        pt = load_page_template({"name": "formal", "page_numbers": False})
        assert pt.name == "formal"
        assert pt.page_numbers is False
        assert pt.first_page_header is True  # default preserved

    def test_object_override_first_page_header(self):
        pt = load_page_template(
            {"name": "formal", "first_page_header": False}
        )
        assert pt.first_page_header is False
        assert pt.page_numbers is True  # default preserved

    def test_object_multiple_overrides(self):
        pt = load_page_template(
            {"name": "clean", "page_numbers": False, "first_page_header": False}
        )
        assert pt.page_numbers is False
        assert pt.first_page_header is False


class TestListPageTemplates:
    """Tests for listing available page templates."""

    def test_returns_all(self):
        templates = list_page_templates()
        names = [t["name"] for t in templates]
        assert "formal" in names
        assert "clean" in names
        assert "branded" in names
        assert "none" in names

    def test_includes_description(self):
        templates = list_page_templates()
        formal = next(t for t in templates if t["name"] == "formal")
        assert formal["description"]

    def test_includes_defaults(self):
        templates = list_page_templates()
        formal = next(t for t in templates if t["name"] == "formal")
        assert "page_numbers" in formal["defaults"]
