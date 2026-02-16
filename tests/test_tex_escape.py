"""Tests for LaTeX escaping."""

from klartex.tex_escape import tex_escape, escape_data


def test_plain_text_unchanged():
    assert tex_escape("Hello world") == "Hello world"


def test_special_chars():
    assert tex_escape("$100") == r"\$100"
    assert tex_escape("50%") == r"50\%"
    assert tex_escape("A & B") == r"A \& B"
    assert tex_escape("foo_bar") == r"foo\_bar"
    assert tex_escape("#1") == r"\#1"


def test_braces():
    assert tex_escape("{test}") == r"\{test\}"


def test_backslash():
    assert tex_escape("a\\b") == r"a\textbackslash{}b"


def test_tilde_and_caret():
    assert tex_escape("~") == r"\textasciitilde{}"
    assert tex_escape("^") == r"\textasciicircum{}"


def test_escape_data_recursive():
    data = {
        "name": "A & B",
        "items": ["$10", "20%"],
        "count": 42,
        "active": True,
        "note": None,
    }
    result = escape_data(data)
    assert result["name"] == r"A \& B"
    assert result["items"] == [r"\$10", r"20\%"]
    assert result["count"] == 42
    assert result["active"] is True
    assert result["note"] is None
