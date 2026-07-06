"""Tests for CLI error handling: invalid JSON, directory input, unwritable output."""

import json
import shutil

import pytest
from typer.testing import CliRunner

from klartex.cli import app

HAS_XELATEX = shutil.which("xelatex") is not None

runner = CliRunner()


def _all_output(result) -> str:
    """stdout + stderr regardless of click version (mix_stderr or not)."""
    out = result.output
    try:
        out += result.stderr
    except (ValueError, AttributeError):
        pass
    return out


def test_invalid_json_stdin_gives_friendly_error():
    result = runner.invoke(app, [], input="{not json")
    assert result.exit_code == 1
    assert "invalid JSON" in _all_output(result)


def test_invalid_json_file_gives_friendly_error(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{trasig", encoding="utf-8")
    result = runner.invoke(app, ["-d", str(bad)])
    assert result.exit_code == 1
    assert "invalid JSON" in _all_output(result)


def test_directory_as_data_path_gives_friendly_error(tmp_path):
    result = runner.invoke(app, ["-d", str(tmp_path)])
    assert result.exit_code == 1
    assert "not a file" in _all_output(result)


@pytest.mark.skipif(not HAS_XELATEX, reason="xelatex not installed")
def test_unwritable_output_reports_error_after_render(tmp_path):
    data = tmp_path / "doc.json"
    data.write_text(json.dumps({"body": [{"type": "text", "text": "hej"}]}), encoding="utf-8")
    out = tmp_path / "finns-inte" / "ut.pdf"
    result = runner.invoke(app, ["-d", str(data), "-o", str(out)])
    assert result.exit_code == 1
    assert "could not write" in _all_output(result)
