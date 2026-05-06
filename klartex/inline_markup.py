"""Inline markup → LaTeX for prose-bearing fields.

Runs *after* `escape_data()`. The escape pass leaves our markers (``*``,
``**``, `` ` ``, ``"``) untouched, so we can detect them here without
fighting the escape state machine.

Markers (deliberately narrow — see issue #25):

- ``**bold**``      → ``\\textbf{...}``
- ``*italic*``      → ``\\textit{...}``
- `` `code` ``      → ``\\texttt{...}``
- ``"..."``         → locale-aware smart quotes (sv: ``”…”``, en: ``“…”``)

Out of scope for v1: links, headings-in-text, lists-in-text, blockquotes,
strikethrough, escape hatches (``\\*`` to print a literal ``*`` etc.).
"""

import re

# Code spans first so * / ** inside backticks aren't treated as markup.
_CODE_RE = re.compile(r"`([^`]+)`")
# Bold must run before italic (longer marker wins). Non-greedy so adjacent
# pairs don't merge: ``**a** **b**`` → two bolds, not one.
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
# Italic: a single * not adjacent to another *.
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")

# (open, close) for paired double quotes per language.
_QUOTE_PAIRS = {
    "sv": ("”", "”"),  # ”…” — Språkrådet style
    "en": ("“", "”"),  # “…”
}

_CODE_PLACEHOLDER = "\x00KX_CODE_{}\x00"


def render_inline(text: str, lang: str = "sv") -> str:
    """Convert inline markup to LaTeX. ``text`` is assumed pre-escaped."""
    if not text:
        return text

    code_spans: list[str] = []

    def stash(match: re.Match) -> str:
        code_spans.append(match.group(1))
        return _CODE_PLACEHOLDER.format(len(code_spans) - 1)

    text = _CODE_RE.sub(stash, text)
    text = _BOLD_RE.sub(r"\\textbf{\1}", text)
    text = _ITALIC_RE.sub(r"\\textit{\1}", text)
    text = _smart_quotes(text, lang)

    for i, code in enumerate(code_spans):
        text = text.replace(_CODE_PLACEHOLDER.format(i), f"\\texttt{{{code}}}")

    # Literal newlines in JSON strings ("line 1\nline 2") become LaTeX line
    # breaks within the current paragraph. For separate paragraphs, use
    # separate text blocks. Done last so it doesn't interfere with the regex
    # passes above that operate within a single line.
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
