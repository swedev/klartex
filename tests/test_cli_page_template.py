"""Tests for the CLI's slot-template flags and asset-dir handling."""

import json
import shutil

import pytest
from typer.testing import CliRunner

from klartex.cli import app

HAS_XELATEX = shutil.which("xelatex") is not None

runner = CliRunner()

BLOCK_DATA = {"body": [{"type": "heading", "text": "Asset dir test"}]}


@pytest.fixture
def cwd(tmp_path, monkeypatch):
    """Run each test in a clean temporary cwd."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def captured(monkeypatch):
    """Monkeypatch klartex.cli.render and capture its kwargs."""
    calls = {}

    def fake_render(template_name, data, **kwargs):
        calls.update(kwargs)
        calls["template_name"] = template_name
        return b"%PDF-1.5 fake"

    monkeypatch.setattr("klartex.cli.render", fake_render)
    return calls


def _bundle(cwd, header="% header", footer="% footer"):
    branding = cwd / "branding"
    branding.mkdir()
    (branding / "head.tex.jinja").write_text(header)
    (branding / "foot.tex.jinja").write_text(footer)
    data = cwd / "report.json"
    data.write_text(json.dumps(BLOCK_DATA))
    return branding, data


class TestSlotTemplateFlags:
    """--header-template / --footer-template own one slot each and set
    asset_dir to their shared directory."""

    def test_both_slot_flags_reach_render(self, cwd, captured):
        branding, data = _bundle(cwd)
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
        assert captured["asset_dir"] == branding.resolve()

    def test_header_flag_alone_leaves_the_footer_slot_to_the_data(self, cwd, captured):
        branding, data = _bundle(cwd)
        result = runner.invoke(
            app, ["-d", str(data), "--header-template", str(branding / "head.tex.jinja")]
        )
        assert result.exit_code == 0
        assert captured["header_source"] == "% header"
        assert captured["footer_source"] is None

    def test_relative_slot_path_is_absolutised(self, cwd, captured):
        """A relative flag value must still yield an absolute asset_dir."""
        branding, _ = _bundle(cwd)
        result = runner.invoke(
            app, ["-d", "report.json", "--header-template", "branding/head.tex.jinja"]
        )
        assert result.exit_code == 0
        asset_dir = captured["asset_dir"]
        assert asset_dir.is_absolute()
        assert asset_dir == branding.resolve()

    def test_no_flag_and_nothing_to_detect_leaves_asset_dir_none(self, cwd, captured):
        data = cwd / "report.json"
        data.write_text(json.dumps(BLOCK_DATA))
        result = runner.invoke(app, ["-d", str(data)])
        assert result.exit_code == 0
        assert captured["asset_dir"] is None
        assert captured["header_source"] is None
        assert captured["footer_source"] is None

    def test_slot_flags_suppress_autodetection(self, cwd, captured):
        """A slot flag is explicit, so a detectable sibling is left alone."""
        branding, data = _bundle(cwd)
        (cwd / "report.tex.jinja").write_text("% sibling")
        result = runner.invoke(
            app, ["-d", str(data), "--header-template", str(branding / "head.tex.jinja")]
        )
        assert result.exit_code == 0
        assert captured["page_template_source"] is None
        assert captured["header_source"] == "% header"
        assert captured["asset_dir"] == branding.resolve()

    def test_slot_files_in_different_directories_are_rejected(self, cwd, captured):
        branding, data = _bundle(cwd)
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
        _, data = _bundle(cwd)
        result = runner.invoke(
            app, ["-d", str(data), "--header-template", "nope.tex.jinja"]
        )
        assert result.exit_code == 1
        assert "not found" in result.output


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
class TestAssetDirEndToEnd:
    """End-to-end: assets next to the slot file resolve from any cwd."""

    @staticmethod
    def _header() -> str:
        return (
            r"\input{brand-colors}"
            "\n"
            r"\fancyhead[L]{\color{brandprimary}Test}"
            "\n"
        )

    @staticmethod
    def _layout(cwd, header_text, asset_text=None):
        branding = cwd / "branding"
        branding.mkdir()
        if asset_text is not None:
            (branding / "brand-colors.tex").write_text(asset_text)
        (branding / "head.tex.jinja").write_text(header_text)
        build = cwd / "build"
        build.mkdir()
        data = build / "report.json"
        data.write_text(json.dumps(BLOCK_DATA))
        return branding, build, data

    def _run(self, build, data, branding, monkeypatch):
        monkeypatch.chdir(build)
        out = build / "report.pdf"
        result = runner.invoke(
            app,
            ["-d", str(data), "--header-template", str(branding / "head.tex.jinja"),
             "-o", str(out)],
        )
        assert result.exit_code == 0, result.output
        assert out.read_bytes()[:5] == b"%PDF-"

    def test_asset_next_to_template_resolves_from_other_cwd(self, cwd, monkeypatch):
        """Issue #37 repro: template + asset in one dir, build from elsewhere."""
        branding, build, data = self._layout(
            cwd, self._header(), r"\definecolor{brandprimary}{HTML}{2E5A1C}"
        )
        self._run(build, data, branding, monkeypatch)

    def test_cwd_remains_fallback_when_asset_not_beside_template(self, cwd, monkeypatch):
        """Asset only in cwd must still resolve — cwd stays on TEXINPUTS."""
        branding, build, data = self._layout(cwd, self._header())
        (build / "brand-colors.tex").write_text(
            r"\definecolor{brandprimary}{HTML}{2E5A1C}"
        )
        self._run(build, data, branding, monkeypatch)

    def test_explicitly_relative_logo_resolves_from_other_cwd(self, cwd, monkeypatch):
        r"""Issue #37 round 2: the reported primitive, \includegraphics{./logo.pdf}.

        The slot file addresses its sibling asset with an explicit ./ prefix —
        which Kpathsea never searches for on TEXINPUTS. It resolves because
        xelatex runs with cwd=template dir.
        """
        from klartex.renderer import render

        branding, build, data = self._layout(
            cwd, r"\fancyhead[L]{\includegraphics[width=2cm]{./logo.pdf}}" "\n"
        )
        # A real (if tiny) PDF to include, produced by klartex itself.
        (branding / "logo.pdf").write_bytes(
            render("_block", {"body": [{"type": "heading", "text": "LOGO"}]})
        )
        self._run(build, data, branding, monkeypatch)

    def test_template_dir_takes_precedence_over_cwd(self, cwd, monkeypatch):
        """Same asset filename in both places: the template's copy wins."""
        branding, build, data = self._layout(
            cwd, self._header(), r"\definecolor{brandprimary}{HTML}{2E5A1C}"
        )
        # A same-named copy that halts xelatex if it is the one picked up:
        # a missing \input target is fatal even under -interaction=nonstopmode.
        # So a successful compile proves the template dir's copy won.
        (build / "brand-colors.tex").write_text(
            r"\definecolor{brandprimary}{HTML}{FF0000}"
            "\n"
            r"\input{this-file-does-not-exist-37}"
        )
        self._run(build, data, branding, monkeypatch)


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
                        "header": {"variant": "letterhead", "fields": {"org_name": "Föreningen X"}}
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


class TestAutodetectHelper:
    """_autodetect_page_template's resolution order, as a unit."""

    def test_sibling_of_the_data_file_wins(self, cwd):
        from klartex.cli import _autodetect_page_template

        data = cwd / "report.json"
        data.write_text(json.dumps(BLOCK_DATA))
        sibling = cwd / "report.tex.jinja"
        sibling.write_text("% sibling")
        (cwd / "page_template.tex.jinja").write_text("% cwd default")
        assert _autodetect_page_template(data) == sibling

    def test_cwd_default_is_the_fallback(self, cwd):
        from klartex.cli import _autodetect_page_template

        data = cwd / "report.json"
        data.write_text(json.dumps(BLOCK_DATA))
        default = cwd / "page_template.tex.jinja"
        default.write_text("% cwd default")
        assert _autodetect_page_template(data) == default

    def test_cwd_default_applies_without_a_data_file(self, cwd):
        from klartex.cli import _autodetect_page_template

        default = cwd / "page_template.tex.jinja"
        default.write_text("% cwd default")
        assert _autodetect_page_template(None) == default

    def test_nothing_to_detect_returns_none(self, cwd):
        from klartex.cli import _autodetect_page_template

        data = cwd / "report.json"
        data.write_text(json.dumps(BLOCK_DATA))
        assert _autodetect_page_template(data) is None

    def test_a_directory_candidate_is_not_a_template(self, cwd):
        """Only a regular file counts — a directory of that name is skipped."""
        from klartex.cli import _autodetect_page_template

        data = cwd / "report.json"
        data.write_text(json.dumps(BLOCK_DATA))
        (cwd / "report.tex.jinja").mkdir()
        (cwd / "page_template.tex.jinja").mkdir()
        assert _autodetect_page_template(data) is None


class TestWholePageTemplateFlag:
    """--page-template owns both slots and sets asset_dir to its own dir."""

    def test_explicit_flag_reaches_render(self, cwd, captured):
        _, data = _bundle(cwd)
        whole = cwd / "branding" / "page.tex.jinja"
        whole.write_text("% whole page")
        result = runner.invoke(app, ["-d", str(data), "--page-template", str(whole)])
        assert result.exit_code == 0
        assert captured["page_template_source"] == "% whole page"
        assert captured["header_source"] is None
        assert captured["footer_source"] is None
        assert captured["asset_dir"] == whole.parent.resolve()

    def test_relative_flag_value_is_absolutised(self, cwd, captured):
        branding, _ = _bundle(cwd)
        (branding / "page.tex.jinja").write_text("% whole page")
        result = runner.invoke(
            app, ["-d", "report.json", "--page-template", "branding/page.tex.jinja"]
        )
        assert result.exit_code == 0
        asset_dir = captured["asset_dir"]
        assert asset_dir.is_absolute()
        assert asset_dir == branding.resolve()

    def test_explicit_flag_wins_over_a_detectable_sibling(self, cwd, captured):
        branding, data = _bundle(cwd)
        (cwd / "report.tex.jinja").write_text("% sibling")
        whole = branding / "page.tex.jinja"
        whole.write_text("% explicit")
        result = runner.invoke(app, ["-d", str(data), "--page-template", str(whole)])
        assert result.exit_code == 0
        assert captured["page_template_source"] == "% explicit"
        assert captured["asset_dir"] == branding.resolve()

    def test_missing_file_is_reported(self, cwd, captured):
        _, data = _bundle(cwd)
        result = runner.invoke(app, ["-d", str(data), "--page-template", "nope.tex.jinja"])
        assert result.exit_code == 1
        assert "not found" in result.output

    @pytest.mark.parametrize("slot_flag", ["--header-template", "--footer-template"])
    def test_conflict_with_a_slot_flag_is_rejected(self, cwd, captured, slot_flag):
        branding, data = _bundle(cwd)
        whole = branding / "page.tex.jinja"
        whole.write_text("% whole page")
        result = runner.invoke(
            app,
            [
                "-d", str(data),
                "--page-template", str(whole),
                slot_flag, str(branding / "head.tex.jinja"),
            ],
        )
        assert result.exit_code == 1
        assert "cannot be combined" in result.output
        assert slot_flag in result.output


class TestWholePageAutodetection:
    """A sibling <data-stem>.tex.jinja, or ./page_template.tex.jinja, is
    picked up when no template flag is given."""

    def test_sibling_next_to_the_data_file_is_used(self, cwd, captured):
        sub = cwd / "reports"
        sub.mkdir()
        data = sub / "report.json"
        data.write_text(json.dumps(BLOCK_DATA))
        (sub / "report.tex.jinja").write_text("% sibling")
        result = runner.invoke(app, ["-d", str(data)])
        assert result.exit_code == 0
        assert captured["page_template_source"] == "% sibling"
        assert captured["asset_dir"] == sub.resolve()
        assert "Using page template" in result.output

    def test_cwd_default_is_used(self, cwd, captured):
        data = cwd / "report.json"
        data.write_text(json.dumps(BLOCK_DATA))
        (cwd / "page_template.tex.jinja").write_text("% cwd default")
        result = runner.invoke(app, ["-d", str(data)])
        assert result.exit_code == 0
        assert captured["page_template_source"] == "% cwd default"
        assert captured["asset_dir"] == cwd.resolve()

    def test_the_notice_goes_to_stderr(self, cwd, captured):
        """The notice must not pollute a piped PDF on stdout."""
        data = cwd / "report.json"
        data.write_text(json.dumps(BLOCK_DATA))
        (cwd / "page_template.tex.jinja").write_text("% cwd default")
        result = CliRunner().invoke(app, ["-d", str(data)])
        assert result.exit_code == 0
        assert "Using page template" in result.stderr
        assert "Using page template" not in result.stdout


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
def test_autodetected_template_finds_its_sibling_asset_from_another_cwd(
    tmp_path, monkeypatch
):
    """The user-shaped case: data + template + logo in one directory,
    rendered from somewhere else."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    data = bundle / "report.json"
    data.write_text(json.dumps(BLOCK_DATA))
    (bundle / "brand.tex").write_text("\\newcommand{\\kxbrand}{Brandname}")
    (bundle / "report.tex.jinja").write_text(
        "\\input{brand}\n\\fancyhead[L]{\\kxbrand}"
    )
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    out = elsewhere / "out.pdf"
    result = runner.invoke(app, ["-d", str(data), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert out.read_bytes().startswith(b"%PDF")
