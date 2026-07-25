"""Tests for CLI page-template auto-discovery in cwd."""

import json
import os
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from klartex.cli import _autodetect_page_template, DEFAULT_PAGE_TEMPLATE_FILENAME, app

HAS_XELATEX = shutil.which("xelatex") is not None

runner = CliRunner()


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


BLOCK_DATA = {"body": [{"type": "heading", "text": "Asset dir test"}]}


class TestAssetDirKwarg:
    """The CLI must pass the page template's own directory as asset_dir."""

    @pytest.fixture
    def captured(self, monkeypatch):
        """Monkeypatch klartex.cli.render and capture its kwargs."""
        calls = {}

        def fake_render(template_name, data, **kwargs):
            calls.update(kwargs)
            calls["template_name"] = template_name
            return b"%PDF-1.5 fake"

        monkeypatch.setattr("klartex.cli.render", fake_render)
        return calls

    def test_explicit_absolute_page_template(self, cwd, captured):
        branding = cwd / "branding"
        branding.mkdir()
        pt = branding / "mall.tex.jinja"
        pt.write_text("% mall")
        data = cwd / "report.json"
        data.write_text(json.dumps(BLOCK_DATA))

        result = runner.invoke(app, ["-d", str(data), "--page-template", str(pt)])
        assert result.exit_code == 0
        assert captured["asset_dir"] == branding.resolve()

    def test_explicit_relative_page_template_is_absolutised(self, cwd, captured):
        """A relative --page-template must still yield an absolute asset_dir."""
        branding = cwd / "branding"
        branding.mkdir()
        (branding / "mall.tex.jinja").write_text("% mall")
        data = cwd / "report.json"
        data.write_text(json.dumps(BLOCK_DATA))

        result = runner.invoke(
            app, ["-d", "report.json", "--page-template", "branding/mall.tex.jinja"]
        )
        assert result.exit_code == 0
        asset_dir = captured["asset_dir"]
        assert asset_dir.is_absolute()
        assert asset_dir == branding.resolve()

    def test_autodetected_sibling_in_subdir(self, cwd, captured):
        """Sibling auto-detect must point asset_dir at the data file's dir."""
        docs = cwd / "docs"
        docs.mkdir()
        data = docs / "report.json"
        data.write_text(json.dumps(BLOCK_DATA))
        (docs / "report.tex.jinja").write_text("% sibling")

        result = runner.invoke(app, ["-d", str(data), "-o", str(cwd / "out.pdf")])
        assert result.exit_code == 0
        assert captured["asset_dir"] == docs.resolve()

    def test_autodetected_cwd_default(self, cwd, captured):
        """The ./page_template.tex.jinja branch yields the resolved cwd."""
        (cwd / DEFAULT_PAGE_TEMPLATE_FILENAME).write_text("% cwd")
        data = cwd / "report.json"
        data.write_text(json.dumps(BLOCK_DATA))

        result = runner.invoke(app, ["-d", str(data)])
        assert result.exit_code == 0
        assert captured["asset_dir"] == cwd.resolve()

    def test_no_external_template_leaves_asset_dir_none(self, cwd, captured):
        data = cwd / "report.json"
        data.write_text(json.dumps(BLOCK_DATA))

        result = runner.invoke(app, ["-d", str(data)])
        assert result.exit_code == 0
        assert captured["asset_dir"] is None


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
class TestAssetDirEndToEnd:
    """End-to-end: assets next to the template resolve from any cwd."""

    @staticmethod
    def _page_template() -> str:
        return (
            r"\input{brand-colors}"
            "\n"
            r"\fancyhead[L]{\color{brandprimary}Test}"
            "\n"
            r"\fancyfoot[C]{\thepage}"
            "\n"
        )

    def test_asset_next_to_template_resolves_from_other_cwd(self, cwd, monkeypatch):
        """Issue #37 repro: template + asset in one dir, build from elsewhere."""
        branding = cwd / "branding"
        branding.mkdir()
        (branding / "brand-colors.tex").write_text(
            r"\definecolor{brandprimary}{HTML}{2E5A1C}"
        )
        (branding / "mall.tex.jinja").write_text(self._page_template())

        build = cwd / "build"
        build.mkdir()
        data = build / "report.json"
        data.write_text(json.dumps(BLOCK_DATA))

        monkeypatch.chdir(build)
        out = build / "report.pdf"
        result = runner.invoke(
            app,
            ["-d", str(data), "--page-template", str(branding / "mall.tex.jinja"),
             "-o", str(out)],
        )
        assert result.exit_code == 0, result.output
        assert out.read_bytes()[:5] == b"%PDF-"

    def test_cwd_remains_fallback_when_asset_not_beside_template(self, cwd, monkeypatch):
        """Asset only in cwd must still resolve — cwd stays on TEXINPUTS."""
        branding = cwd / "branding"
        branding.mkdir()
        (branding / "mall.tex.jinja").write_text(self._page_template())

        build = cwd / "build"
        build.mkdir()
        (build / "brand-colors.tex").write_text(
            r"\definecolor{brandprimary}{HTML}{2E5A1C}"
        )
        data = build / "report.json"
        data.write_text(json.dumps(BLOCK_DATA))

        monkeypatch.chdir(build)
        out = build / "report.pdf"
        result = runner.invoke(
            app,
            ["-d", str(data), "--page-template", str(branding / "mall.tex.jinja"),
             "-o", str(out)],
        )
        assert result.exit_code == 0, result.output
        assert out.read_bytes()[:5] == b"%PDF-"

    def test_template_dir_takes_precedence_over_cwd(self, cwd, monkeypatch):
        """Same asset filename in both places: the template's copy wins."""
        branding = cwd / "branding"
        branding.mkdir()
        (branding / "brand-colors.tex").write_text(
            r"\definecolor{brandprimary}{HTML}{2E5A1C}"
        )
        (branding / "mall.tex.jinja").write_text(self._page_template())

        build = cwd / "build"
        build.mkdir()
        # A same-named copy that halts xelatex if it is the one picked up:
        # a missing \input target is fatal even under -interaction=nonstopmode.
        # So a successful compile proves the template dir's copy won.
        (build / "brand-colors.tex").write_text(
            r"\definecolor{brandprimary}{HTML}{FF0000}"
            "\n"
            r"\input{this-file-does-not-exist-37}"
        )
        data = build / "report.json"
        data.write_text(json.dumps(BLOCK_DATA))

        monkeypatch.chdir(build)
        out = build / "report.pdf"
        result = runner.invoke(
            app,
            ["-d", str(data), "--page-template", str(branding / "mall.tex.jinja"),
             "-o", str(out)],
        )
        assert result.exit_code == 0, result.output
        assert out.read_bytes()[:5] == b"%PDF-"
