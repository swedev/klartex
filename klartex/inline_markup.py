"""Inline markup → LaTeX for prose-bearing fields.

Runs *after* `escape_data()`. The escape pass leaves our markers (``*``,
``**``, `` ` ``, ``"``) untouched, so we can detect them here without
fighting the escape state machine.

Markers (deliberately narrow — see issue #25):

- ``**bold**``      → ``\\textbf{...}``
- ``*italic*``      → ``\\textit{...}``
- `` `code` ``      → ``\\texttt{...}``
- ``"..."``         → locale-aware smart quotes (sv: ``”…”``, en: ``“…”``)
- ``{+added+}``     → ``\\kxadded{...}`` — change marking (#40)
- ``{-removed-}``   → ``\\kxremoved{...}`` — change marking (#40)

Out of scope: links, headings-in-text, lists-in-text, blockquotes, *generic*
strikethrough (``~~text~~``), escape hatches (``\\*`` to print a literal ``*``
etc.). Semantic change marking is in scope; arbitrary strikethrough is not.

Change-marker semantics:

- The markers arrive here in *escaped* form (``\\{+…+\\}``), because
  ``escape_data()`` has already turned ``{`` and ``}`` into ``\\{`` / ``\\}``.
  Both the opener and its matching closer must be present.
- Markup inside marker content still renders: ``{+**viktigt** tillägg+}`` →
  ``\\kxadded{\\textbf{viktigt} tillägg}``.
- Mixed nesting renders nested: ``{-gammal {+ny+} gammal-}`` puts a
  ``\\kxadded`` group inside the ``\\kxremoved`` argument. Same-type nesting is
  undefined — the non-greedy match closes at the first closer.
- Adjacent markers stay separate spans, mirroring adjacent bold.
- Empty (``{++}``), unmatched, or lone markers stay literal and print as
  visible text.
- Markers may span literal newlines; the newline pass converts those inside
  the macro argument, which both ``\\textcolor`` and ulem's ``\\sout`` accept.
- Caveat: the grammar is narrow but not free of false positives — literal
  text shaped like ``{-1-}`` converts. Both delimiters are required, so
  ordinary brace prose (``intervallet {-5, 5}``) does not.
"""

import re

# Code spans first so * / ** inside backticks aren't treated as markup.
_CODE_RE = re.compile(r"`([^`]+)`")
# Bold must run before italic (longer marker wins). Non-greedy so adjacent
# pairs don't merge: ``**a** **b**`` → two bolds, not one.
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
# Italic: a single * not adjacent to another *.
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")

# Change marking (#40). Matched in escaped form: ``{+x+}`` reaches this
# function as ``\{+x+\}``. Non-greedy so adjacent markers stay separate;
# DOTALL so a marked span may cross a literal newline.
_ADDED_RE = re.compile(r"\\\{\+(.+?)\+\\\}", re.DOTALL)
_REMOVED_RE = re.compile(r"\\\{-(.+?)-\\\}", re.DOTALL)

# (open, close) for paired double quotes per language.
_QUOTE_PAIRS = {
    "sv": ("”", "”"),  # ”…” — Språkrådet style
    "en": ("“", "”"),  # “…”
}

_CODE_PLACEHOLDER = "\x00KX_CODE_{}\x00"


def render_inline(text: str, lang: str = "sv", newlines: str = "break") -> str:
    """Convert inline markup to LaTeX. ``text`` is assumed pre-escaped.

    ``newlines`` selects how literal ``\\n`` characters render:

    - ``"break"`` (default): ``\\\\`` — paragraph line break. NOT safe inside
      tabular cells, where ``\\\\`` ends the table row instead.
    - ``"cell"``: ``\\newline`` — in-cell line break for paragraph-mode
      columns (``p{...}``/``X``).
    - ``"space"``: collapse to a space — for LR-mode cells (``l`` columns)
      where no in-cell line break exists.
    """
    if not text:
        return text

    code_spans: list[str] = []

    def stash(match: re.Match) -> str:
        code_spans.append(match.group(1))
        return _CODE_PLACEHOLDER.format(len(code_spans) - 1)

    text = _CODE_RE.sub(stash, text)
    # Change markers run after the code stash (a marker inside backticks stays
    # literal) and before bold/italic, so markup inside marker content is still
    # reached by the later global passes.
    text = _ADDED_RE.sub(r"\\kxadded{\1}", text)
    text = _REMOVED_RE.sub(r"\\kxremoved{\1}", text)
    text = _BOLD_RE.sub(r"\\textbf{\1}", text)
    text = _ITALIC_RE.sub(r"\\textit{\1}", text)
    text = _smart_quotes(text, lang)

    for i, code in enumerate(code_spans):
        text = text.replace(_CODE_PLACEHOLDER.format(i), f"\\texttt{{{code}}}")

    # Literal newlines in JSON strings ("line 1\nline 2") become LaTeX line
    # breaks within the current paragraph. For separate paragraphs, use
    # separate text blocks. Done last so it doesn't interfere with the regex
    # passes above that operate within a single line.
    if newlines == "cell":
        text = text.replace("\n", " \\newline ")
    elif newlines == "space":
        text = text.replace("\n", " ")
    else:
        text = text.replace("\n", " \\\\ ")

    return text


def _smart_quotes(text: str, lang: str) -> str:
    open_q, close_q = _QUOTE_PAIRS.get(lang, _QUOTE_PAIRS["sv"])
    if open_q == close_q:
        return text.replace('"', open_q)
    out: list[str] = []
    in_quote = False
    for ch in text:
        if ch == '"':
            out.append(close_q if in_quote else open_q)
            in_quote = not in_quote
        else:
            out.append(ch)
    return "".join(out)
