"""Tests for inline markup → LaTeX (#25)."""

from klartex.inline_markup import render_inline


def test_plain_text_unchanged():
    assert render_inline("Hello world") == "Hello world"


def test_empty_input():
    assert render_inline("") == ""


def test_bold():
    assert render_inline("a **bold** b") == r"a \textbf{bold} b"


def test_italic():
    assert render_inline("a *italic* b") == r"a \textit{italic} b"


def test_bold_takes_precedence_over_italic():
    # **foo** is bold, not italic-italic.
    assert render_inline("**foo**") == r"\textbf{foo}"


def test_italic_inside_bold():
    # Italic-in-bold is allowed: ``**bold *and* italic**`` → expected nested.
    assert render_inline("**bold *and* italic**") == r"\textbf{bold \textit{and} italic}"


def test_adjacent_bold_pairs_dont_merge():
    # Non-greedy bold: each ** ** pair is its own span.
    assert render_inline("**a** **b**") == r"\textbf{a} \textbf{b}"


def test_code_span():
    assert render_inline("use `foo` here") == r"use \texttt{foo} here"


def test_code_protects_inner_markup():
    assert render_inline("`**not bold**`") == r"\texttt{**not bold**}"


def test_smart_quotes_swedish():
    # sv: both opener and closer are ”
    assert render_inline('say "hi" now', lang="sv") == "say ”hi” now"


def test_smart_quotes_english():
    # en: paired “ and ”
    assert render_inline('say "hi" now', lang="en") == "say “hi” now"


def test_multiple_quote_pairs_english():
    out = render_inline('"a" and "b"', lang="en")
    assert out == "“a” and “b”"


def test_combined_markers():
    out = render_inline('**bold** and *italic* and `code` and "quoted"', lang="sv")
    assert out == r'\textbf{bold} and \textit{italic} and \texttt{code} and ”quoted”'


def test_escaped_text_passes_through():
    # tex_escape already turned `_` into `\_` and `&` into `\&`; markup must
    # not interfere with that.
    assert render_inline(r"foo\_bar \& baz") == r"foo\_bar \& baz"


def test_escaped_underscore_inside_code():
    # `foo_bar` arrives here as `foo\_bar` after escape; \texttt must wrap it.
    assert render_inline(r"`foo\_bar`") == r"\texttt{foo\_bar}"


def test_lang_default_is_sv():
    assert render_inline('"x"') == "”x”"


def test_newline_becomes_latex_line_break():
    assert render_inline("a\nb") == "a \\\\ b"


def test_multiple_newlines():
    assert render_inline("a\nb\nc") == "a \\\\ b \\\\ c"


def test_newline_works_with_other_markup():
    assert render_inline("**bold**\n*italic*") == r"\textbf{bold} \\ \textit{italic}"
