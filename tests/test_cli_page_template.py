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

    def test_explicitly_relative_logo_resolves_from_other_cwd(self, cwd, monkeypatch):
        r"""Issue #37 round 2: the reported primitive, \includegraphics{./logo.pdf}.

        Same layout as the repro above, but the template addresses its sibling
        asset with an explicit ./ prefix — which Kpathsea never searches for on
        TEXINPUTS. It resolves because xelatex now runs with cwd=template dir.
        """
        from klartex.renderer import render

        branding = cwd / "branding"
        branding.mkdir()
        # A real (if tiny) PDF to include, produced by klartex itself.
        (branding / "logo.pdf").write_bytes(
            render("_block", {"body": [{"type": "heading", "text": "LOGO"}]})
        )
        (branding / "mall.tex.jinja").write_text(
            r"\fancyhead[L]{\includegraphics[width=2cm]{./logo.pdf}}"
            "\n"
            r"\fancyfoot[C]{\thepage}"
            "\n"
        )

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


class TestSlotTemplateFlags:
    """--header-template / --footer-template own one slot each."""

    @pytest.fixture
    def captured(self, monkeypatch):
        calls = {}

        def fake_render(template_name, data, **kwargs):
            calls.update(kwargs)
            calls["template_name"] = template_name
            return b"%PDF-1.5 fake"

        monkeypatch.setattr("klartex.cli.render", fake_render)
        return calls

    @staticmethod
    def _bundle(cwd, header="% header", footer="% footer"):
        branding = cwd / "branding"
        branding.mkdir()
        (branding / "head.tex.jinja").write_text(header)
        (branding / "foot.tex.jinja").write_text(footer)
        data = cwd / "report.json"
        data.write_text(json.dumps(BLOCK_DATA))
        return branding, data

    def test_both_slot_flags_reach_render(self, cwd, captured):
        branding, data = self._bundle(cwd)
        result = runner.invoke(
            app,
            [
                "-d", str(data),
                "--header-template", str(branding / "head.tex.jinja"),
                "--footer-template", str(branding / "foot.tex.jinja"),
            ],
        )
        assert result.exit_code == 0
        assert captured["header_source"] == "% header"
        assert captured["footer_source"] == "% footer"
        assert captured["page_template_source"] is None
        assert captured["asset_dir"] == branding.resolve()

    def test_header_flag_alone_leaves_the_footer_slot_to_the_data(self, cwd, captured):
        branding, data = self._bundle(cwd)
        result = runner.invoke(
            app, ["-d", str(data), "--header-template", str(branding / "head.tex.jinja")]
        )
        assert result.exit_code == 0
        assert captured["header_source"] == "% header"
        assert captured["footer_source"] is None

    def test_slot_flag_suppresses_autodetection(self, cwd, captured):
        branding, data = self._bundle(cwd)
        (cwd / DEFAULT_PAGE_TEMPLATE_FILENAME).write_text("% monolithic")
        result = runner.invoke(
            app, ["-d", str(data), "--header-template", str(branding / "head.tex.jinja")]
        )
        assert result.exit_code == 0
        assert "Using page template:" not in result.output
        assert captured["page_template_source"] is None

    def test_page_template_and_slot_flag_conflict(self, cwd, captured):
        branding, data = self._bundle(cwd)
        (branding / "mall.tex.jinja").write_text("% mall")
        result = runner.invoke(
            app,
            [
                "-d", str(data),
                "--page-template", str(branding / "mall.tex.jinja"),
                "--header-template", str(branding / "head.tex.jinja"),
            ],
        )
        assert result.exit_code == 1
        assert "--page-template" in result.output
        assert "--header-template" in result.output

    def test_slot_files_in_different_directories_are_rejected(self, cwd, captured):
        branding, data = self._bundle(cwd)
        other = cwd / "other"
        other.mkdir()
        (other / "foot.tex.jinja").write_text("% footer")
        result = runner.invoke(
            app,
            [
                "-d", str(data),
                "--header-template", str(branding / "head.tex.jinja"),
                "--footer-template", str(other / "foot.tex.jinja"),
            ],
        )
        assert result.exit_code == 1
        assert "same directory" in result.output

    def test_missing_slot_file_is_reported(self, cwd, captured):
        _, data = self._bundle(cwd)
        result = runner.invoke(
            app, ["-d", str(data), "--header-template", "nope.tex.jinja"]
        )
        assert result.exit_code == 1
        assert "not found" in result.output


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
class TestSlotTemplateFlagsRender:
    """End-to-end: a custom footer replaces only the footer."""

    def test_footer_template_replaces_only_the_footer(self, cwd):
        branding = cwd / "branding"
        branding.mkdir()
        (branding / "foot.tex.jinja").write_text(
            "\\fancyfoot[C]{EGEN SIDFOT}\n"
        )
        data = cwd / "report.json"
        data.write_text(
            json.dumps(
                {
                    "page_template": {
                        "header": {"variant": "letterhead", "org_name": "Föreningen X"}
                    },
                    "body": [{"type": "heading", "text": "Rubrik"}],
                }
            )
        )
        result = runner.invoke(
            app,
            [
                "-d", str(data),
                "--footer-template", str(branding / "foot.tex.jinja"),
                "-o", str(cwd / "out.pdf"),
            ],
        )
        assert result.exit_code == 0, result.output
        assert (cwd / "out.pdf").read_bytes()[:5] == b"%PDF-"
