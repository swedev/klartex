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


# --- Change marking (#40) -------------------------------------------------
#
# Inputs are written in the *escaped* form the filter really receives:
# escape_data() turns "{+x+}" into "\{+x+\}" before render_inline runs.


def test_added_marker():
    assert render_inline(r"ny \{+lydelse+\} här") == r"ny \kxadded{lydelse} här"


def test_removed_marker():
    assert render_inline(r"gammal \{-lydelse-\} här") == r"gammal \kxremoved{lydelse} här"


def test_both_markers_in_one_string():
    assert (
        render_inline(r"\{-gammalt-\} blir \{+nytt+\}")
        == r"\kxremoved{gammalt} blir \kxadded{nytt}"
    )


def test_bold_inside_marker_content():
    assert render_inline(r"\{+**viktigt** tillägg+\}") == r"\kxadded{\textbf{viktigt} tillägg}"


def test_italic_inside_marker_content():
    assert render_inline(r"\{-*struket* ord-\}") == r"\kxremoved{\textit{struket} ord}"


def test_code_span_inside_marker_content():
    assert render_inline(r"\{+kör `foo` nu+\}") == r"\kxadded{kör \texttt{foo} nu}"


def test_marker_inside_code_span_stays_literal():
    # The code stash runs first, so backticked markers are never converted.
    assert render_inline(r"`\{+x+\}`") == r"\texttt{\{+x+\}}"


def test_mixed_nesting_added_inside_removed():
    assert (
        render_inline(r"\{-gammal \{+ny+\} gammal-\}")
        == r"\kxremoved{gammal \kxadded{ny} gammal}"
    )


def test_mixed_nesting_removed_inside_added():
    assert (
        render_inline(r"\{+ny \{-gammal-\} ny+\}")
        == r"\kxadded{ny \kxremoved{gammal} ny}"
    )


def test_adjacent_markers_stay_separate():
    assert render_inline(r"\{+a+\}\{-b-\}") == r"\kxadded{a}\kxremoved{b}"


def test_adjacent_same_type_markers_stay_separate():
    assert render_inline(r"\{+a+\} \{+b+\}") == r"\kxadded{a} \kxadded{b}"


def test_empty_markers_stay_literal():
    assert render_inline(r"\{++\} \{--\}") == r"\{++\} \{--\}"


def test_unmatched_opener_stays_literal():
    assert render_inline(r"en \{+ensam öppnare") == r"en \{+ensam öppnare"


def test_mismatched_delimiters_stay_literal():
    # Opener and closer must be the same kind.
    assert render_inline(r"\{+a-\}") == r"\{+a-\}"


def test_brace_prose_is_not_a_marker():
    # Both delimiters are required — a closing brace without the sign is inert.
    assert render_inline(r"intervallet \{-5, 5\}") == r"intervallet \{-5, 5\}"


def test_escaped_specials_inside_marker_content():
    assert (
        render_inline(r"\{+50 \% av \_summan\_ \& mer+\}")
        == r"\kxadded{50 \% av \_summan\_ \& mer}"
    )


def test_marker_content_spanning_newline():
    assert render_inline("\\{+rad ett\nrad två+\\}") == r"\kxadded{rad ett \\ rad två}"


def test_marker_content_spanning_newline_in_cell_mode():
    assert (
        render_inline("\\{-rad ett\nrad två-\\}", newlines="cell")
        == r"\kxremoved{rad ett \newline rad två}"
    )


def test_marker_with_smart_quotes_inside():
    assert render_inline('\\{+en "citerad" fras+\\}') == "\\kxadded{en ”citerad” fras}"
