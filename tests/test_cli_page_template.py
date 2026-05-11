"""Tests for CLI page-template auto-discovery in cwd."""

import os
from pathlib import Path

import pytest

from klartex.cli import _autodetect_page_template, DEFAULT_PAGE_TEMPLATE_FILENAME


@pytest.fixture
def cwd(tmp_path, monkeypatch):
    """Run each test in a clean temporary cwd."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_no_data_no_default_returns_none(cwd):
    assert _autodetect_page_template(None) is None


def test_data_file_with_sibling_template_wins(cwd):
    data = cwd / "report.json"
    data.write_text("{}")
    sibling = cwd / "report.tex.jinja"
    sibling.write_text("% sibling")
    # also drop a cwd default to confirm sibling has priority
    (cwd / DEFAULT_PAGE_TEMPLATE_FILENAME).write_text("% cwd")
    assert _autodetect_page_template(data) == sibling


def test_falls_back_to_cwd_default_when_no_sibling(cwd):
    data = cwd / "report.json"
    data.write_text("{}")
    default = cwd / DEFAULT_PAGE_TEMPLATE_FILENAME
    default.write_text("% cwd")
    assert _autodetect_page_template(data) == default


def test_picks_cwd_default_when_no_data_path(cwd):
    default = cwd / DEFAULT_PAGE_TEMPLATE_FILENAME
    default.write_text("% cwd")
    assert _autodetect_page_template(None) == default


def test_returns_none_when_nothing_present(cwd):
    data = cwd / "report.json"
    data.write_text("{}")
    assert _autodetect_page_template(data) is None


def test_sibling_resolved_relative_to_data_dir(cwd):
    """Sibling lookup must use the data file's directory, not cwd."""
    subdir = cwd / "docs"
    subdir.mkdir()
    data = subdir / "report.json"
    data.write_text("{}")
    sibling = subdir / "report.tex.jinja"
    sibling.write_text("% sibling")
    assert _autodetect_page_template(data) == sibling


def test_data_path_can_be_relative(cwd):
    """Auto-detect must work when data is given as a relative Path."""
    (cwd / "report.json").write_text("{}")
    sibling = cwd / "report.tex.jinja"
    sibling.write_text("% sibling")
    relative = Path("report.json")
    found = _autodetect_page_template(relative)
    assert found is not None
    assert found.resolve() == sibling.resolve()
