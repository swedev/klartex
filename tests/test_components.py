"""Tests for the component registry."""

import pytest

from klartex.components import (
    get_component,
    list_components,
    resolve_data_path,
    extract_component_data,
)


class TestComponentRegistry:
    """Tests for component lookup and listing."""

    def test_get_known_component(self):
        spec = get_component("klausuler")
        assert spec.name == "klausuler"
        assert spec.sty_package == "klartex-klausuler"

    def test_get_signaturblock(self):
        spec = get_component("signaturblock")
        assert spec.sty_package == "klartex-signaturblock"

    def test_get_heading_no_sty(self):
        spec = get_component("heading")
        assert spec.sty_package is None

    def test_unknown_component_raises(self):
        with pytest.raises(ValueError, match="Unknown component"):
            get_component("nonexistent")

    def test_list_components_returns_all(self):
        components = list_components()
        assert "klausuler" in components
        assert "signaturblock" in components
        assert "titelsida" in components
        assert "heading" in components
        assert len(components) >= 5


class TestResolveDataPath:
    """Tests for dot-notation data path resolution."""

    def test_simple_path(self):
        data = {"name": "Alice"}
        assert resolve_data_path(data, "name") == "Alice"

    def test_nested_path(self):
        data = {"party1": {"name": "Acme", "org_number": "123"}}
        assert resolve_data_path(data, "party1.name") == "Acme"

    def test_missing_path_returns_none(self):
        data = {"name": "Alice"}
        assert resolve_data_path(data, "missing") is None

    def test_missing_nested_path_returns_none(self):
        data = {"party1": {"name": "Acme"}}
        assert resolve_data_path(data, "party1.missing") is None

    def test_deeply_nested_missing_returns_none(self):
        data = {"a": {"b": {"c": 1}}}
        assert resolve_data_path(data, "a.b.missing.deep") is None


class TestExtractComponentData:
    """Tests for extracting component data via data_map."""

    def test_basic_extraction(self):
        data = {"meeting_type": "Styrelsemote", "date": "2026-01-01"}
        data_map = {"title": "meeting_type", "subtitle": "date"}
        result = extract_component_data("heading", data_map, data)
        assert result == {"title": "Styrelsemote", "subtitle": "2026-01-01"}

    def test_empty_data_map(self):
        result = extract_component_data("heading", None, {"a": 1})
        assert result == {}

    def test_missing_field_in_data(self):
        data = {"name": "Alice"}
        data_map = {"title": "missing_field"}
        result = extract_component_data("heading", data_map, data)
        assert result == {"title": None}
