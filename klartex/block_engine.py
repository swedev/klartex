"""Universal block engine — renders body[] blocks to LaTeX.

The block engine is a rendering path where the agent composes ``body[]``
freely from typed blocks. The document type emerges from what blocks the
agent places in the body, not from which template it selects.

Usage via the API: ``POST /render`` with ``template: "_block"``.

Data shape::

    {
        "page_template": {"header": "logo", "footer": {"variant": "columns", "fields": {"company": "AB"}}},
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
from klartex.page_templates import BLOCK_DEFAULT_SLOTS, load_page_template

# Block types recognized by the block engine template
KNOWN_BLOCK_TYPES = {
    name for name, spec in _COMPONENTS.items() if spec.block_schema_path
}

# The sentinel template name used to invoke the block engine
BLOCK_ENGINE_TEMPLATE = "_block"


def prepare_block_context(
    data: dict,
    *,
    header_source: str | None = None,
    footer_source: str | None = None,
) -> dict[str, Any]:
    """Build the Jinja context for the block engine meta-template.

    Args:
        data: User data with ``page_template``, ``lang``, and ``body[]``.
              Data should already be escaped via ``escape_data()`` before
              calling this function.
        header_source: Optional raw .tex.jinja content owning the header slot.
        footer_source: Optional raw .tex.jinja content owning the footer slot.

    Returns:
        Context dict for rendering ``_block_engine.tex.jinja``.

    Raises:
        ValueError: If the data is missing required fields or the page
                    template is unknown.
    """
    if "body" not in data:
        raise ValueError("Block engine data must include a 'body' array")

    # Resolve page template. The loader owns the slot model; a slot the
    # payload leaves out gets the block engine's default.
    page_tmpl = load_page_template(
        data.get("page_template"),
        defaults=BLOCK_DEFAULT_SLOTS,
        header_source=header_source,
        footer_source=footer_source,
    )

    # Extract document title from body blocks (first heading or title_page)
    doc_title = _extract_doc_title(data["body"])

    return {
        "body": data["body"],
        "lang": data.get("lang", "sv"),
        "block_settings": data.get("block_settings") or {},
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
