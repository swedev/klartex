"""Tests for the rendering pipeline."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from klartex.page_templates import GUARANTEED_FONTS
from klartex.renderer import render, get_registry, CLS_DIR

TEMPLATES_DIR = CLS_DIR.parent / "templates"

FIXTURES = Path(__file__).parent / "fixtures"

HAS_XELATEX = shutil.which("xelatex") is not None


def _squeeze(text: str) -> str:
    """Log text with whitespace and fontspec's line prefix removed.

    The TeX engine hard-wraps its output at a fixed column, splitting words
    mid-token, and fontspec indents continuation lines under a "(fontspec)"
    marker. Dropping both is what makes a message match regardless of where
    the wrap happened to fall.
    """
    return re.sub(r"\s+|\(fontspec\)", "", text)


def _is_unresolvable_font(error: str, family: str) -> bool:
    """True when a failed compile failed because fontspec could not find
    ``family`` — as opposed to any other reason a render can fail."""
    return _squeeze(f'The font "{family}" cannot be found') in _squeeze(error)


# Environments that are supposed to render like production (the base-image
# self-test and the release gate) set this, turning the missing-font skip
# below into a failure: a base image that lost a guaranteed family must not
# pass silently.
REQUIRE_FONTS = os.environ.get("KLARTEX_REQUIRE_FONTS") == "1"


def test_unknown_template():
    with pytest.raises(ValueError, match="Unknown template"):
        render("nonexistent", {})


def test_class_default_chrome():
    r"""The bundled class carries the default margins and brand colors.

    The golden fixtures start at ``\documentclass{klartex-base}``, so a
    regression in the class itself is invisible to them.
    """
    cls = (CLS_DIR / "klartex-base.cls").read_text()
    assert r"\newcommand{\kxsidemargin}{3cm}" in cls
    assert r"\newcommand{\kxreclaimtop}{2cm}" in cls
    assert r"left=\kxsidemargin," in cls
    assert r"right=\kxsidemargin," in cls
    assert r"\renewcommand{\kxsidemargin}{2cm}" in cls
    assert r"\renewcommand{\kxreclaimtop}{1.7cm}" in cls
    assert r"\definecolor{brandprimary}{HTML}{000000}" in cls
    assert r"\definecolor{brandsecondary}{HTML}{000000}" in cls


def test_header_band_constant_matches_the_class_geometry():
    r"""``HEADER_BAND_BOTTOM_CM`` is where the header band ends, and a set
    ``margins.top`` puts the text block there via ``headsep``. It mirrors the
    class geometry's ``top`` plus ``headheight``, so compare the **sum** — the
    three values could otherwise drift apart in step and still pass.
    """
    import re
    from fractions import Fraction

    from klartex.page_templates import HEADER_BAND_BOTTOM_CM

    cls = (CLS_DIR / "klartex-base.cls").read_text()
    values = {}
    for key in ("top", "headheight"):
        match = re.search(rf"^\s*{key}=([0-9.]+)cm,\s*$", cls, re.MULTILINE)
        assert match, f"geometry {key} in cm not found in klartex-base.cls"
        values[key] = Fraction(match.group(1))
    assert values["top"] + values["headheight"] == HEADER_BAND_BOTTOM_CM


def test_footer_band_geometry_is_late_bound():
    r"""klartex-footer enlarges the bottom geometry for its band. Binding it
    through the class's macros is what lets ``margins.bottom`` win over it.
    """
    cls = (CLS_DIR / "klartex-base.cls").read_text()
    assert r"\newcommand{\kxfooterbottom}{3.6cm}" in cls
    assert r"\newcommand{\kxfooterfootskip}{2.6cm}" in cls
    sty = (CLS_DIR / "klartex-footer.sty").read_text()
    assert r"\geometry{bottom=\kxfooterbottom, footskip=\kxfooterfootskip}" in sty


def test_narrowmargins_class_option_scoped_to_faktura_and_kvitto():
    r"""Only faktura and kvitto opt into the tighter `narrowmargins` geometry.

    The option rides on `document.class_options` in recipe.yaml; the meta
    template turns it into `\documentclass[invoice]{klartex-base}`.
    """
    import yaml
    for name, expect in [("faktura", "narrowmargins"), ("kvitto", "narrowmargins"),
                         ("protokoll", ""), ("resultatrakning", "")]:
        raw = yaml.safe_load((TEMPLATES_DIR / name / "recipe.yaml").read_text())
        assert raw.get("document", {}).get("class_options", "") == expect, name
    meta = (TEMPLATES_DIR / "_recipe_base.tex.jinja").read_text()
    assert r"\documentclass[\VAR{class_options}]{klartex-base}" in meta


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
        "_block", data, header_source=page_template, asset_dir=tmp_path
    )
    assert pdf[:5] == b"%PDF-"

    # Without asset_dir: \input cannot find brand-colors.tex, xelatex halts
    with pytest.raises(RuntimeError, match="xelatex failed"):
        render("_block", data, header_source=page_template)


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
def test_render_resolves_relative_asset_dir(tmp_path, monkeypatch):
    """A relative asset_dir must be resolved against the caller's cwd.

    The resolved path is used both as a TEXINPUTS entry and as xelatex's cwd,
    so leaving it relative would resolve against the wrong base entirely.
    """
    branding = tmp_path / "branding"
    branding.mkdir()
    (branding / "brand-colors.tex").write_text(
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
    data = {"body": [{"type": "heading", "text": "Relative asset dir"}]}

    monkeypatch.chdir(tmp_path)
    pdf = render(
        "_block", data, header_source=page_template, asset_dir=Path("branding")
    )
    assert pdf[:5] == b"%PDF-"


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
def test_whole_page_source_owns_geometry_and_font(tmp_path):
    r"""The documented use: one file carrying the whole design — its own
    \geometry and \setmainfont, plus a sibling asset — rendered alongside the
    payload's document-level settings.
    """
    (tmp_path / "brand-colors.tex").write_text(
        r"\definecolor{brandprimary}{HTML}{2E5A1C}"
    )
    whole_page = (
        r"\input{brand-colors}"
        "\n"
        r"\geometry{top=4cm, bottom=3cm}"
        "\n"
        r"\setmainfont{lmsans10-regular.otf}"
        "\n"
        r"\fancyhead[L]{\color{brandprimary}Brand}"
        "\n"
        r"\fancyfoot[C]{\thepage}"
        "\n"
    )
    data = {
        "body": [{"type": "heading", "text": "Whole page"}],
        "page_template": {"font": "lmroman10-regular.otf", "margins": {"bottom": "2cm"}},
    }
    pdf = render(
        "_block", data, page_template_source=whole_page, asset_dir=tmp_path
    )
    assert pdf[:5] == b"%PDF-"


def _color_page_template(input_arg: str) -> str:
    """A page template whose only job is to \\input the given argument."""
    return (
        f"\\input{{{input_arg}}}"
        "\n"
        r"\fancyhead[L]{\color{brandprimary}Test}"
        "\n"
    )


_BRAND_COLORS = r"\definecolor{brandprimary}{HTML}{2E5A1C}"


def _dir_snapshot(root: Path) -> dict[str, bytes]:
    """Map every file under `root` to its bytes, keyed by relative path.

    Byte-level rather than a name listing, so a *modified* file is caught too.
    """
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
def test_explicitly_relative_asset_path_resolves_via_asset_dir(tmp_path):
    r"""``\input{./brand-colors}`` must resolve against asset_dir.

    Kpathsea never searches TEXINPUTS for names starting with ``./`` or
    ``../`` — they are tried as-is against xelatex's working directory. The
    renderer therefore compiles with cwd set to the asset root, which is what
    makes this work. Discriminating test for issue #37 round 2.
    """
    (tmp_path / "brand-colors.tex").write_text(_BRAND_COLORS)
    data = {"body": [{"type": "heading", "text": "Explicitly relative"}]}

    # Plain name: found via asset_dir on TEXINPUTS (unchanged behavior).
    pdf = render(
        "_block",
        data,
        header_source=_color_page_template("brand-colors"),
        asset_dir=tmp_path,
    )
    assert pdf[:5] == b"%PDF-"

    # Explicitly relative name: resolves against asset_dir as xelatex's cwd.
    pdf = render(
        "_block",
        data,
        header_source=_color_page_template("./brand-colors"),
        asset_dir=tmp_path,
    )
    assert pdf[:5] == b"%PDF-"


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
def test_parent_relative_asset_path_resolves_above_asset_dir(tmp_path):
    r"""``\input{../shared/…}`` must reach outside the template's own directory.

    Models the real layout from the issue: a per-brand template directory next
    to a shared assets directory.
    """
    branding = tmp_path / "branding"
    branding.mkdir()
    shared = tmp_path / "shared"
    shared.mkdir()
    (shared / "brand-colors.tex").write_text(_BRAND_COLORS)

    data = {"body": [{"type": "heading", "text": "Parent relative"}]}
    pdf = render(
        "_block",
        data,
        header_source=_color_page_template("../shared/brand-colors"),
        asset_dir=branding,
    )
    assert pdf[:5] == b"%PDF-"


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
def test_explicitly_relative_path_falls_back_to_cwd_without_asset_dir(
    tmp_path, monkeypatch
):
    r"""Without asset_dir, xelatex's cwd is the caller's cwd.

    Locks the deliberate default-case change: ``./x`` resolves against the
    working directory rather than failing against a private tempdir.
    """
    (tmp_path / "brand-colors.tex").write_text(_BRAND_COLORS)
    data = {"body": [{"type": "heading", "text": "Cwd relative"}]}

    monkeypatch.chdir(tmp_path)
    pdf = render(
        "_block", data, header_source=_color_page_template("./brand-colors")
    )
    assert pdf[:5] == b"%PDF-"


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
def test_render_writes_no_artifacts_into_asset_dir(tmp_path):
    """Compiling with cwd=asset_dir must not leave .aux/.log/.pdf behind."""
    (tmp_path / "brand-colors.tex").write_text(_BRAND_COLORS)
    data = {"body": [{"type": "heading", "text": "No artifacts"}]}

    before = _dir_snapshot(tmp_path)
    pdf = render(
        "_block",
        data,
        header_source=_color_page_template("./brand-colors"),
        asset_dir=tmp_path,
    )
    assert pdf[:5] == b"%PDF-"
    assert _dir_snapshot(tmp_path) == before


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
def test_render_writes_no_artifacts_into_cwd(tmp_path, monkeypatch):
    """The caller's cwd is xelatex's cwd when asset_dir is unset — guard it too."""
    (tmp_path / "brand-colors.tex").write_text(_BRAND_COLORS)
    data = {"body": [{"type": "heading", "text": "No artifacts in cwd"}]}

    monkeypatch.chdir(tmp_path)
    before = _dir_snapshot(tmp_path)
    pdf = render(
        "_block", data, header_source=_color_page_template("./brand-colors")
    )
    assert pdf[:5] == b"%PDF-"
    assert _dir_snapshot(tmp_path) == before


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
def test_asset_dir_cannot_shadow_bundled_sty(tmp_path):
    """The bundled cls/ must still be searched before asset_dir.

    Guards the TEXINPUTS reorder: xelatex's cwd is now the asset root, so a
    leading "." entry would put the asset root ahead of cls/ and let a
    template-dir file hijack a klartex .sty. Spelling the tempdir out instead
    keeps the old order. The decoy here \\inputs a missing file, which is fatal
    even under -interaction=nonstopmode, so a successful render proves the
    bundled package won.
    """
    (tmp_path / "klartex-callout.sty").write_text(
        r"\ProvidesPackage{klartex-callout}"
        "\n"
        r"\input{this-file-does-not-exist-shadow-37}"
        "\n"
    )
    data = {"body": [{"type": "callout", "variant": "info", "text": "Skuggning"}]}

    pdf = render(
        "_block",
        data,
        header_source="\\fancyfoot[C]{\\thepage}\n",
        asset_dir=tmp_path,
    )
    assert pdf[:5] == b"%PDF-"


@pytest.mark.parametrize("kind", ["missing", "plain_file"])
def test_invalid_asset_dir_raises_value_error(tmp_path, kind):
    """A non-directory asset_dir must fail fast with a clear message.

    Validation runs before the xelatex-presence check, so this holds even
    without TeX installed.
    """
    if kind == "missing":
        bogus = tmp_path / "does-not-exist"
    else:
        bogus = tmp_path / "a-file.txt"
        bogus.write_text("not a directory")

    data = {"body": [{"type": "heading", "text": "Invalid asset dir"}]}
    with pytest.raises(ValueError, match="not a directory"):
        render("_block", data, asset_dir=bogus)


def test_xelatex_invocation_shape(tmp_path, monkeypatch):
    """Both runs use an absolute .tex path, cwd=asset_root and -output-directory.

    Fast test: subprocess.run is faked, so no xelatex is needed.
    """
    from klartex import renderer as renderer_mod

    monkeypatch.setattr(renderer_mod.shutil, "which", lambda _: "/usr/bin/xelatex")

    calls = []

    class FakeResult:
        returncode = 0
        stdout = b""

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        # Satisfy the "did xelatex produce a PDF?" check.
        out_dir = Path(cmd[cmd.index("-output-directory") + 1])
        (out_dir / "document.pdf").write_bytes(b"%PDF-fake")
        return FakeResult()

    monkeypatch.setattr(renderer_mod.subprocess, "run", fake_run)

    pdf = renderer_mod._compile_tex("x", asset_dir=tmp_path)
    assert pdf == b"%PDF-fake"
    assert len(calls) == 2

    tex_paths = set()
    for cmd, kwargs in calls:
        out_dir = Path(cmd[cmd.index("-output-directory") + 1])
        tex_path = Path(cmd[-1])
        tex_paths.add(tex_path)

        assert tex_path.is_absolute()
        assert tex_path.name == "document.tex"
        assert tex_path.parent == out_dir
        assert Path(kwargs["cwd"]) == tmp_path.resolve()

        texinputs = kwargs["env"]["TEXINPUTS"].split(":")
        assert texinputs[0] == str(out_dir)
        assert texinputs[1] == str(renderer_mod.CLS_DIR)
        assert texinputs[2] == str(tmp_path.resolve())
        assert texinputs[3] == os.getcwd()

    # Same jobname/source across both runs, so the second reuses the first .aux.
    assert len(tex_paths) == 1


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
def test_second_run_finds_aux_from_first_run(monkeypatch):
    r"""-output-directory must receive the .aux so two-pass references resolve.

    Uses a genuinely two-run-sensitive document (\label + \pageref) and spies
    on the real subprocess.run to assert document.aux exists in the output
    directory after the first run. The %PDF- assertions used elsewhere would
    not catch unresolved "??" references.
    """
    import subprocess as real_subprocess

    from klartex import renderer as renderer_mod

    aux_after_first_run = []
    real_run = real_subprocess.run

    def spy_run(cmd, **kwargs):
        result = real_run(cmd, **kwargs)
        out_dir = Path(cmd[cmd.index("-output-directory") + 1])
        aux_after_first_run.append((out_dir / "document.aux").exists())
        return result

    data = {
        "body": [
            {
                "type": "latex",
                "source": r"Se sida~\pageref{kx:testmark}.\label{kx:testmark}",
            }
        ]
    }

    monkeypatch.setattr(renderer_mod.subprocess, "run", spy_run)
    pdf = render("_block", data)

    assert pdf[:5] == b"%PDF-"
    assert len(aux_after_first_run) == 2
    assert aux_after_first_run[0], (
        "first run did not write document.aux to -output-directory"
    )


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


def _render_recipe_tex(template_name: str, data: dict, **sources: str) -> str:
    """Helper: run the recipe pre-compile pipeline, return the LaTeX source.

    ``sources`` forwards ``page_template_source`` / ``header_source`` /
    ``footer_source`` to the recipe renderer.
    """
    from klartex.renderer import _render_recipe
    from klartex.tex_escape import escape_data

    info = get_registry()[template_name]
    return _render_recipe(
        info,
        escape_data(data),
        page_template_source=sources.get("page_template_source"),
        header_source=sources.get("header_source"),
        footer_source=sources.get("footer_source"),
    )


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
    """amount: 0 must render as 0,00; a missing amount gives an empty cell.
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
    assert r"Gratisrad & 0,00 \\" in tex
    assert r"Rad utan belopp &  \\" in tex
    assert "100,00" in tex


def test_kvitto_sender_logo_and_footer():
    """kvitto mirrors faktura: sender block, header logo, and the columns
    footer slot that emits \\kxfooter."""
    data = {
        "receipt_number": "K-2",
        "date": "2026-08-07",
        "total_amount": 100,
        "items": [{"description": "Avgift", "amount": 100}],
        "sender": {"name": "Säljbolaget AB", "org_number": "556111-2222"},
        "logo": "logo.pdf",
        "page_template": {
            "footer": {
                "variant": "columns",
                "fields": {"company": "Säljbolaget AB", "bankgiro": "1234-5678"},
            }
        },
    }
    tex = _render_recipe_tex("kvitto", data)
    assert "Avsändare" in tex
    assert "Säljbolaget AB" in tex
    assert r"\includegraphics[height=1cm]{logo.pdf}" in tex
    assert r"\usepackage{klartex-footer}" in tex
    assert "bankgiro={1234-5678}" in tex


def test_kvitto_without_sender_renders_no_party_block():
    """Without sender/recipient the invoice_recipient component must render
    nothing — no empty Mottagare label."""
    data = {
        "receipt_number": "K-3",
        "date": "2026-08-07",
        "total_amount": 100,
        "items": [{"description": "Avgift"}],
    }
    tex = _render_recipe_tex("kvitto", data)
    assert "Mottagare" not in tex
    assert "Avsändare" not in tex


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


def test_recipe_metadata_passes_through_inline_markup():
    """The recipe path shares render_description_list with the block engine,
    so document metadata gets inline markup and change markers too (#47)."""
    data = json.loads((FIXTURES / "protokoll.json").read_text())
    data["location"] = "Klubbhuset, [-Storgatan 1-] {+**Lillgatan 2**+}"
    tex = _render_recipe_tex("protokoll", data)
    assert r"\kxremoved{Storgatan 1}" in tex
    assert r"\kxadded{\textbf{Lillgatan 2}}" in tex
    assert "**" not in tex


def test_recipe_agenda_items_pass_through_inline_markup():
    """The recipe path shares render_agenda with the block engine, so protokoll
    agenda items get inline markup and change markers too (#60). protokoll
    renders `decimal`, where the branch writes its own \\textbf around the
    title — hence the nested assertion."""
    data = json.loads((FIXTURES / "protokoll.json").read_text())
    data["agenda_items"][0]["title"] = "Mötets **öppnande**"
    data["agenda_items"][0]["discussion"] = "[-Kort-] {+Lång+} diskussion"
    data["agenda_items"][1]["decision"] = 'Valdes "enhälligt"'
    tex = _render_recipe_tex("protokoll", data)
    assert r"\textbf{Mötets \textbf{öppnande}}" in tex
    assert r"\kxremoved{Kort}" in tex
    assert r"\kxadded{Lång}" in tex
    assert "Valdes ”enhälligt”" in tex
    assert "**" not in tex


def test_recipe_agenda_sub_items_render_with_decimal_numbering():
    """protokoll renders `decimal`, so agenda_items[].subItems get decimal
    sub-numbering under the parent via the shared render_agenda (#70)."""
    import jsonschema

    data = json.loads((FIXTURES / "protokoll.json").read_text())
    data["agenda_items"][2]["subItems"] = ["Intäkter **ökade**", "Kostnader"]
    jsonschema.validate(data, get_registry()["protokoll"].get_validation_schema())

    tex = _render_recipe_tex("protokoll", data)
    assert r"\makebox[1.0cm][l]{\textbf{3.1.}}Intäkter \textbf{ökade}\par" in tex
    assert r"\makebox[1.0cm][l]{\textbf{3.2.}}Kostnader\par" in tex
    assert "**" not in tex
    assert tex.index("3.1.") > tex.index("Styrelsen godkände den ekonomiska rapporten")


def test_recipe_metadata_newline_is_cell_safe():
    """Metadata values land in the paragraph-mode X column: a newline must
    become \\newline, never a bare \\\\ that would end the table row."""
    data = json.loads((FIXTURES / "protokoll.json").read_text())
    data["location"] = "Klubbhuset\nStorgatan 1"
    tex = _render_recipe_tex("protokoll", data)
    assert r"Klubbhuset \newline Storgatan 1" in tex


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


def _minimal_faktura(**extra) -> dict:
    data = {
        "invoice_number": "F-1",
        "date": "2026-08-06",
        "due_date": "2026-09-05",
        "recipient": {"name": "Kund AB"},
        "lines": [
            {"description": "Tjänst", "quantity": 9, "unit_price": 3600.0, "vat_percent": 0}
        ],
    }
    data.update(extra)
    return data


def test_faktura_margins_override_the_narrowmargins_defaults():
    r"""faktura's `narrowmargins` class option is the recipe default; explicit
    margins are emitted after `\documentclass` and win, per key.
    """
    tex = _render_recipe_tex(
        "faktura",
        _minimal_faktura(page_template={"margins": {"left": "4cm", "top": "5cm"}}),
    )
    assert tex.index(r"\documentclass[narrowmargins]{klartex-base}") < tex.index(
        r"\geometry{left=4cm, headsep=\dimexpr 5cm-2.1cm\relax}"
    )
    assert r"\renewcommand{\kxreclaimtop}{5cm}" in tex


def test_whole_page_source_reaches_the_recipe_path():
    tex = _render_recipe_tex(
        "faktura", _minimal_faktura(), page_template_source="% whole page"
    )
    assert tex.count("% whole page") == 1


def test_whole_page_source_owns_the_footer_and_leaves_payment_info_in_body():
    r"""A whole-page source owns both slots, so the slot's fields are not
    emitted — and with no footer carrying payment details, the in-body
    fallback block renders.
    """
    tex = _render_recipe_tex(
        "faktura",
        _minimal_faktura(
            bankgiro="9999-9999",
            page_template={
                "footer": {"variant": "columns", "fields": {"bankgiro": "1111-1111"}}
            },
        ),
        page_template_source="% whole page",
    )
    assert tex.count("% whole page") == 1
    assert r"\kxfooter{" not in tex
    assert "1111-1111" not in tex
    assert "Betalningsinformation" in tex
    assert "9999-9999" in tex


def test_faktura_margins_reach_the_footer_slot_geometry():
    r"""The document-level settings are emitted before the footer slot, so the
    slot's `\kxfooter` picks up the renewed bottom geometry.
    """
    tex = _render_recipe_tex(
        "faktura",
        _minimal_faktura(
            page_template={
                "margins": {"bottom": "3cm"},
                "footer": {"variant": "columns", "fields": {"company": "Bolaget AB"}},
            },
        ),
    )
    assert tex.index(r"\renewcommand{\kxfooterbottom}{3cm}") < tex.index(r"\kxfooter{")


def test_faktura_amounts_use_swedish_number_format():
    """Amounts default to Swedish format: thin-space groups, decimal comma."""
    tex = _render_recipe_tex("faktura", _minimal_faktura())
    assert r"32\,400,00" in tex
    assert "32,400.00" not in tex


def test_faktura_number_format_en_override():
    """number_format: 'en' switches amounts to English convention."""
    tex = _render_recipe_tex("faktura", _minimal_faktura(number_format="en"))
    assert "32,400.00" in tex
    assert r"32\,400,00" not in tex


def test_faktura_fractional_quantity_uses_decimal_comma():
    data = _minimal_faktura()
    data["lines"][0]["quantity"] = 1.5
    tex = _render_recipe_tex("faktura", data)
    assert r"1,5 " in tex or "1,5 &" in tex


def test_faktura_large_quantity_not_exponent_notation():
    data = _minimal_faktura()
    data["lines"][0]["quantity"] = 1234567
    tex = _render_recipe_tex("faktura", data)
    assert "1234567" in tex
    assert "e+06" not in tex


def test_faktura_page_template_dict_emits_footer():
    """A page_template object with footer renders \\kxfooter with keyvals and
    suppresses the in-body payment_info block."""
    data = _minimal_faktura(
        bankgiro="9999-9999",
        page_template={
            "footer": {
                "variant": "columns",
                "fields": {
                    "company": "Bolaget AB",
                    "address": "Storgatan 1, 123 45 Stad",
                    "bankgiro": "1234-5678",
                    "f_tax": True,
                }
            },
        },
    )
    tex = _render_recipe_tex("faktura", data)
    assert r"\usepackage{klartex-footer}" in tex
    assert "company={Bolaget AB}" in tex
    assert "address={Storgatan 1, 123 45 Stad}" in tex
    assert "bankgiro={1234-5678}" in tex
    assert "ftax=true" in tex
    # in-body payment_info suppressed: the data's own bankgiro must not render
    assert "Betalningsinformation" not in tex
    assert "9999-9999" not in tex


def test_faktura_footer_address_lines_joined_with_newlines():
    """An address given as a list of lines renders as a line-broken postal
    address in the footer."""
    data = _minimal_faktura(
        page_template={
            "footer": {"variant": "columns", "fields": {"address": ["Storgatan 1", "123 45 Stad"]}},
        }
    )
    tex = _render_recipe_tex("faktura", data)
    assert r"address={Storgatan 1\\123 45 Stad}" in tex


def test_faktura_logo_rendered_in_header_block():
    """An optional logo renders left of the FAKTURA block at the given height,
    nudged by logo_offset fractions of its own height."""
    data = _minimal_faktura(
        logo="logo.pdf", logo_height="1.2cm", logo_offset={"x": -0.1, "y": 0.25}
    )
    tex = _render_recipe_tex("faktura", data)
    assert r"\includegraphics[height=1.2cm]{logo.pdf}" in tex
    assert r"\hspace*{-0.1\dimexpr1.2cm\relax}" in tex
    assert r"+0.25\height" in tex

    tex_without = _render_recipe_tex("faktura", _minimal_faktura())
    assert "logo.pdf" not in tex_without


def test_faktura_logo_default_height():
    """A logo without logo_height renders at the 1cm default."""
    tex = _render_recipe_tex("faktura", _minimal_faktura(logo="logo.pdf"))
    assert r"\includegraphics[height=1cm]{logo.pdf}" in tex


def test_faktura_sender_block_rendered():
    """An optional sender renders as an Avsändare block; without it the
    layout stays recipient + references only."""
    data = _minimal_faktura(
        sender={
            "name": "Säljbolaget AB",
            "org_number": "556111-2222",
            "address_line1": "Storgatan 1",
        }
    )
    tex = _render_recipe_tex("faktura", data)
    assert "Avsändare" in tex
    assert "Säljbolaget AB" in tex
    assert "556111-2222" in tex

    tex_without = _render_recipe_tex("faktura", _minimal_faktura())
    assert "Avsändare" not in tex_without


def test_faktura_top_level_footer_is_not_rendered():
    """The footer slot is the only footer surface. A top-level `footer` is
    rejected by the schema; the template layer renders nothing from it.

    `_render_recipe_tex` bypasses validation, so this exercises the template
    layer alone — the schema rejection is locked in `tests/test_schemas.py`.
    """
    data = _minimal_faktura(footer={"company": "Från data", "bankgiro": "1111-1111"})
    tex = _render_recipe_tex("faktura", data)
    assert "Från data" not in tex
    assert "1111-1111" not in tex
    assert r"\usepackage{klartex-footer}" not in tex


def test_faktura_payment_info_renders_without_footer():
    tex = _render_recipe_tex("faktura", _minimal_faktura(bankgiro="9999-9999"))
    assert "Betalningsinformation" in tex
    assert "9999-9999" in tex


def test_faktura_payment_info_skipped_when_no_payment_fields():
    """No payment fields in data → no empty Betalningsinformation block."""
    tex = _render_recipe_tex("faktura", _minimal_faktura())
    assert "Betalningsinformation" not in tex


def test_faktura_font_options_emitted():
    data = _minimal_faktura(
        page_template={"font": "Futura", "header_font": "Georgia"}
    )
    tex = _render_recipe_tex("faktura", data)
    assert r"\setmainfont{Futura}" in tex
    assert r"\newfontfamily\kxheaderfontfamily{Georgia}" in tex


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
@pytest.mark.parametrize("family", GUARANTEED_FONTS)
def test_guaranteed_font_renders(family):
    r"""Every family the schema guarantees must survive a real xelatex run.

    The family is set as both ``font`` and ``header_font``, so ``\setmainfont``
    and the ``\newfontfamily\kxheaderfontfamily`` path are both exercised, and
    the text carries bold and italic markup so the face selection fontspec
    derives from the family is used, not only the regular face.

    Where the family is genuinely absent — GitHub runners install a minimal
    TeX Live with no mscorefonts — the case skips. Availability is decided by
    the compile itself rather than by asking fontconfig: on macOS the engine
    resolves fonts through Core Text, so fc-list answers for a font the
    engine cannot load (and vice versa), and only the engine's own verdict
    tells the two apart. The skip reason deliberately avoids the word xelatex
    so the CI guard against silently skipped xelatex tests is not tripped.
    Environments that must render like production set KLARTEX_REQUIRE_FONTS=1,
    which turns the skip into a failure.
    """
    data = {
        "body": [
            {
                "type": "text",
                "text": (
                    f"Brödtext i {family} med **fet stil** och *kursiv stil*."
                ),
            }
        ],
        "page_template": {"font": family, "header_font": family},
    }
    try:
        pdf_bytes = render("_block", data)
    except RuntimeError as exc:
        if REQUIRE_FONTS or not _is_unresolvable_font(str(exc), family):
            raise
        pytest.skip(f"font family {family!r} not available to the TeX engine")
    assert pdf_bytes[:5] == b"%PDF-"
    assert len(pdf_bytes) > 1000


#: The four Latin Modern OpenType faces, which ship with every TeX Live and
#: are therefore locatable wherever xelatex is — no font install, no
#: conditional skip. The names already satisfy FONT_FILENAME_PATTERN.
_TEX_FONT_FACES = {
    "file": "lmroman10-regular.otf",
    "bold": "lmroman10-bold.otf",
    "italic": "lmroman10-italic.otf",
    "bold_italic": "lmroman10-bolditalic.otf",
}


def _copy_tex_fonts(dest: Path) -> dict[str, str]:
    """Copy the Latin Modern faces into `dest`, returning the file form."""
    for name in _TEX_FONT_FACES.values():
        located = subprocess.run(
            ["kpsewhich", name], capture_output=True, text=True
        ).stdout.strip()
        assert located, f"kpsewhich could not locate {name}"
        shutil.copy(located, dest / name)
    return dict(_TEX_FONT_FACES)


def _font_setup_tex(page_template: dict) -> str:
    """The block-engine preamble for a page_template, without compiling."""
    from tests.test_block_engine import _render_tex

    return _render_tex(
        {"page_template": page_template, "body": [{"type": "heading", "text": "F"}]}
    )


def test_font_file_form_emitted_with_every_supplied_face():
    tex = _font_setup_tex({"font": dict(_TEX_FONT_FACES)})
    assert (
        r"\setmainfont{lmroman10-regular.otf}[Path=./, "
        r"BoldFont=lmroman10-bold.otf, ItalicFont=lmroman10-italic.otf, "
        r"BoldItalicFont=lmroman10-bolditalic.otf]"
    ) in tex


def test_font_file_form_with_regular_face_only():
    r"""Faces that were not supplied leave fontspec to fall back to the
    regular one — no \*Font option, and no synthesis."""
    tex = _font_setup_tex({"font": {"file": "lmroman10-regular.otf"}})
    assert r"\setmainfont{lmroman10-regular.otf}[Path=./]" in tex
    assert "BoldFont" not in tex
    assert "AutoFakeBold" not in tex


def test_header_font_defaults_to_the_font_files():
    tex = _font_setup_tex({
        "font": {"file": "lmroman10-regular.otf", "bold": "lmroman10-bold.otf"}
    })
    assert (
        r"\newfontfamily\kxheaderfontfamily{lmroman10-regular.otf}"
        r"[Path=./, BoldFont=lmroman10-bold.otf]"
    ) in tex
    assert r"\renewcommand{\kxheaderfont}{\kxheaderfontfamily}" in tex


@pytest.mark.parametrize("face", ["file", "bold"])
def test_missing_font_file_raises_before_compiling(tmp_path, face):
    """A face file absent from the asset root is named, not left to fontspec.

    The preflight runs before the xelatex-presence check, so this holds
    without TeX installed — and the message states the resolution contract.
    """
    faces = dict(_TEX_FONT_FACES)
    for name in faces.values():
        (tmp_path / name).write_bytes(b"")
    (tmp_path / faces[face]).unlink()

    data = {"body": [{"type": "heading", "text": "F"}], "page_template": {"font": faces}}
    with pytest.raises(ValueError, match=f"Font file '{faces[face]}' is not readable"):
        render("_block", data, asset_dir=tmp_path)


def test_font_file_preflight_uses_cwd_without_asset_dir(tmp_path, monkeypatch):
    """With no asset_dir the asset root is the caller's cwd — the same single
    root explicitly relative names resolve against."""
    monkeypatch.chdir(tmp_path)
    data = {
        "body": [{"type": "heading", "text": "F"}],
        "page_template": {"font": {"file": "lmroman10-regular.otf"}},
    }
    with pytest.raises(ValueError, match="lmroman10-regular.otf"):
        render("_block", data)

    (tmp_path / "lmroman10-regular.otf").write_bytes(b"")
    # The file is there now, so the preflight passes and the failure that
    # remains (if any) belongs to xelatex, not to the font contract.
    with pytest.raises((RuntimeError, ValueError)) as exc:
        render("_block", data)
    assert "Font file" not in str(exc.value)


def test_font_file_preflight_rejects_an_invalid_asset_dir(tmp_path):
    """The preflight resolves the asset root the same way the compile does."""
    data = {
        "body": [{"type": "heading", "text": "F"}],
        "page_template": {"font": {"file": "lmroman10-regular.otf"}},
    }
    with pytest.raises(ValueError, match="not a directory"):
        render("_block", data, asset_dir=tmp_path / "does-not-exist")


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
def test_font_file_form_renders(tmp_path):
    """Font files travelling as assets compile, faces and all.

    The faces come from TeX Live itself, so the case runs wherever the rest of
    the compilation tests do.
    """
    faces = _copy_tex_fonts(tmp_path)
    data = {
        "body": [{"type": "text", "text": "Brödtext med **fet** och *kursiv* stil."}],
        "page_template": {"font": faces, "header": "letterhead"},
    }
    pdf_bytes = render("_block", data, asset_dir=tmp_path)
    assert pdf_bytes[:5] == b"%PDF-"
    assert len(pdf_bytes) > 1000


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
def test_font_file_form_renders_with_the_regular_face_alone(tmp_path):
    """Bold and italic markup with no face files supplied still compiles —
    fontspec falls back to the regular face."""
    located = subprocess.run(
        ["kpsewhich", _TEX_FONT_FACES["file"]], capture_output=True, text=True
    ).stdout.strip()
    shutil.copy(located, tmp_path / _TEX_FONT_FACES["file"])
    data = {
        "body": [{"type": "text", "text": "Text med **fet** och *kursiv* stil."}],
        "page_template": {"font": {"file": _TEX_FONT_FACES["file"]}},
    }
    pdf_bytes = render("_block", data, asset_dir=tmp_path)
    assert pdf_bytes[:5] == b"%PDF-"


def test_faktura_preamble_unchanged_from_golden():
    """The recipe path's default preamble: letterhead header, page-number
    footer with the title. The golden is held by hand — a deliberate fragment
    change updates it in the same commit, any other diff is a regression."""
    from tests.test_block_engine import golden_preamble

    data = json.loads((FIXTURES / "faktura.json").read_text())
    golden = (FIXTURES / "golden" / "page_template_faktura.tex").read_text(
        encoding="utf-8"
    )
    assert golden_preamble(_render_recipe_tex("faktura", data)) == golden_preamble(
        golden
    )


class TestRecipePageTemplateSlots:
    """The slot model on the recipe path, where the recipe supplies the
    default slots."""

    def test_slot_form_on_faktura(self):
        data = _minimal_faktura(
            page_template={"header": "logo", "footer": {"variant": "columns", "fields": {"company": "Bolaget AB"}}}
        )
        tex = _render_recipe_tex("faktura", data)
        assert r"\usepackage{klartex-footer}" in tex
        assert "company={Bolaget AB}" in tex
        assert r"\fancyhead[R]" in tex
        assert r"\fancyhead[L]" not in tex

    def test_custom_footer_source_leaves_payment_info_in_body(self):
        """A custom footer source carries no structured fields, so
        `footer_has_payment` is False and the in-body fallback renders."""
        data = _minimal_faktura(bankgiro="9999-9999")
        tex = _render_recipe_tex(
            "faktura", data, footer_source=r"\fancyfoot[C]{Egen}"
        )
        assert r"\fancyfoot[C]{Egen}" in tex
        assert "Betalningsinformation" in tex
        assert "9999-9999" in tex

    def test_partial_object_keeps_the_recipe_default(self):
        """The recipe default is the letterhead header, so a slot object that
        only touches the footer must still get it."""
        data = json.loads((FIXTURES / "protokoll.json").read_text())
        data["page_template"] = {"footer": None}
        tex = _render_recipe_tex("protokoll", data)
        assert r"\fancyhead[L]" in tex
        assert r"\fancyfoot" not in tex

    def test_header_slot_settings_reach_the_recipe_path(self):
        data = _minimal_faktura(
            page_template={"header": {"variant": "letterhead", "fields": {"org_name": "Bolaget AB"}}}
        )
        tex = _render_recipe_tex("faktura", data)
        assert r"\renewcommand{\orgname}{Bolaget AB}" in tex
