"""Tests for the `klartex validate` subcommand: exit codes and error shape."""

import json
from pathlib import Path

from typer.testing import CliRunner

from klartex.cli import app

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE = str(FIXTURES / "block_kallelse.json")

runner = CliRunner()


def _all_output(result) -> str:
    """stdout + stderr regardless of click version (mix_stderr or not)."""
    out = result.output
    try:
        out += result.stderr
    except (ValueError, AttributeError):
        pass
    return out


def test_valid_fixture_exits_zero_and_prints_nothing():
    result = runner.invoke(app, ["validate", "-d", FIXTURE])
    assert result.exit_code == 0
    assert result.stdout == ""


def test_valid_payload_from_stdin():
    payload = json.dumps({"body": [{"type": "text", "text": "hej"}]})
    result = runner.invoke(app, ["validate"], input=payload)
    assert result.exit_code == 0


def test_valid_recipe_payload_with_template_flag():
    result = runner.invoke(
        app, ["validate", "-t", "protokoll", "-d", str(FIXTURES / "protokoll.json")]
    )
    assert result.exit_code == 0


def test_unknown_block_type_reports_the_block_path(tmp_path):
    data = tmp_path / "doc.json"
    data.write_text(json.dumps({"body": [{"type": "nope"}]}), encoding="utf-8")
    result = runner.invoke(app, ["validate", "-d", str(data)])
    assert result.exit_code == 1
    assert "Unknown block type 'nope' at body[0]" in _all_output(result)


def test_schema_violation_exits_one(tmp_path):
    data = tmp_path / "doc.json"
    data.write_text(json.dumps({"body": "not a list"}), encoding="utf-8")
    result = runner.invoke(app, ["validate", "-d", str(data)])
    assert result.exit_code == 1
    assert "Error:" in _all_output(result)


def test_unknown_template_exits_one():
    result = runner.invoke(app, ["validate", "-t", "nonexistent", "-d", FIXTURE])
    assert result.exit_code == 1
    assert "Unknown template 'nonexistent'" in _all_output(result)


def test_malformed_json_exits_one(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{trasig", encoding="utf-8")
    result = runner.invoke(app, ["validate", "-d", str(bad)])
    assert result.exit_code == 1
    assert "invalid JSON" in _all_output(result)


def test_missing_data_file_exits_one(tmp_path):
    result = runner.invoke(app, ["validate", "-d", str(tmp_path / "nope.json")])
    assert result.exit_code == 1
    assert "not found" in _all_output(result)
