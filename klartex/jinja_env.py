"""LaTeX-safe Jinja2 environment construction.

The delimiters are chosen so a template is valid LaTeX source: ``\\BLOCK{…}``
for statements, ``\\VAR{…}`` for expressions, ``\\#{…}`` for comments. Shared
by the document templates (``klartex.renderer``) and the page-template
fragments (``klartex.page_templates``).

This module deliberately imports nothing from the rest of the package so both
can use it without an import cycle.
"""

import jinja2

# Delimiter and whitespace options every klartex Jinja environment uses.
LATEX_JINJA_OPTIONS: dict = {
    "block_start_string": r"\BLOCK{",
    "block_end_string": r"}",
    "variable_start_string": r"\VAR{",
    "variable_end_string": r"}",
    "comment_start_string": r"\#{",
    "comment_end_string": r"}",
    "line_statement_prefix": "%%",
    "line_comment_prefix": "%#",
    "trim_blocks": True,
    "lstrip_blocks": True,
    "autoescape": False,
}


def make_env(loader: jinja2.BaseLoader | None = None) -> jinja2.Environment:
    """Build a Jinja2 environment with the LaTeX-safe delimiters.

    Args:
        loader: Optional Jinja2 loader for template lookup by name.

    Returns:
        A configured ``jinja2.Environment``. Filters are registered by the
        caller.
    """
    return jinja2.Environment(loader=loader, **LATEX_JINJA_OPTIONS)
