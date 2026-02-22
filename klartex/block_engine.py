"""Universal block engine — renders body[] blocks to LaTeX.

The block engine is a rendering path where the agent composes ``body[]``
freely from typed blocks. The document type emerges from what blocks the
agent places in the body, not from which template it selects.

Usage via the API: ``POST /render`` with ``template: "_block"``.

Data shape::

    {
        "page_template": "formal",       # or {"name": "formal", "page_numbers": false}
        "lang": "sv",
        "body": [
            {"type": "heading", "text": "My Document"},
            {"type": "text", "text": "Hello world."},
            {"type": "signatures", "parties": [...]}
        ]
    }
"""

from typing import Any

from klartex.components import _COMPONENTS
from klartex.page_templates import load_page_template, read_page_template_source

# Block types recognized by the block engine template
KNOWN_BLOCK_TYPES = {
    name for name, spec in _COMPONENTS.items() if spec.block_schema_path
}

# The sentinel template name used to invoke the block engine
BLOCK_ENGINE_TEMPLATE = "_block"


def prepare_block_context(
    data: dict,
    page_template_source: str | None = None,
) -> dict[str, Any]:
    """Build the Jinja context for the block engine meta-template.

    Args:
        data: User data with ``page_template``, ``lang``, and ``body[]``.
              Data should already be escaped via ``escape_data()`` before
              calling this function.
        page_template_source: Optional raw .tex.jinja content. When set,
              overrides the built-in page template lookup.

    Returns:
        Context dict for rendering ``_block_engine.tex.jinja``.

    Raises:
        ValueError: If the data is missing required fields or the page
                    template is unknown.
    """
    if "body" not in data:
        raise ValueError("Block engine data must include a 'body' array")

    # Resolve page template
    page_template_spec = data.get("page_template", "formal")
    page_tmpl = load_page_template(page_template_spec)

    # Read template source: caller-provided or built-in file
    if page_template_source is None:
        page_template_source = read_page_template_source(page_tmpl.name)

    # Extract document title from body blocks (first heading or title_page)
    doc_title = _extract_doc_title(data["body"])

    return {
        "body": data["body"],
        "lang": data.get("lang", "sv"),
        "page_template_source": page_template_source,
        "page_template": page_tmpl,
        "doc_title": doc_title,
    }


def _extract_doc_title(body: list[dict]) -> str:
    """Extract a document title from body blocks for PDF metadata.

    Looks for a title_page block with a title, or the first heading block.
    """
    for block in body:
        if block.get("type") == "title_page" and block.get("title"):
            return block["title"]
        if block.get("type") == "heading":
            return block.get("text", "")
    return ""
