"""Component registry — maps component type names to LaTeX packages and macros.

Each component defines:
- sty_package: The .sty package to load (or None if no extra package needed)
- block_schema_path: Path to the JSON Schema file for this block type
- description: Human-readable description
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Path to block schema files
_SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas" / "blocks"


@dataclass
class ComponentSpec:
    """Specification for a document component."""

    name: str
    sty_package: str | None = None
    description: str = ""
    block_schema_path: str | None = None

    def get_block_schema(self) -> dict | None:
        """Load and return the JSON Schema for this block type, or None."""
        if not self.block_schema_path:
            return None
        path = _SCHEMAS_DIR / self.block_schema_path
        if not path.exists():
            return None
        return json.loads(path.read_text())


# Registry of known component types
_COMPONENTS: dict[str, ComponentSpec] = {
    "heading": ComponentSpec(
        name="heading",
        sty_package=None,
        description="Large bold heading text",
        block_schema_path="heading.schema.json",
    ),
    "text": ComponentSpec(
        name="text",
        sty_package=None,
        description="Free-form text paragraph",
        block_schema_path="text.schema.json",
    ),
    "title_page": ComponentSpec(
        name="title_page",
        sty_package="klartex-titelsida",
        description="Full-page title with party names and document title",
        block_schema_path="title_page.schema.json",
    ),
    "parties": ComponentSpec(
        name="parties",
        sty_package=None,
        description="Side-by-side display of two contract parties",
        block_schema_path="parties.schema.json",
    ),
    "form": ComponentSpec(
        name="form",
        sty_package=None,
        description="Label/value rows where blank values render as horizontal rules for handwritten signing",
        block_schema_path="form.schema.json",
    ),
    "columns": ComponentSpec(
        name="columns",
        sty_package=None,
        description="Side-by-side layout of 1-4 column-stacks of blocks",
        block_schema_path="columns.schema.json",
    ),
    "clause": ComponentSpec(
        name="clause",
        sty_package="klartex-klausuler",
        description="Numbered legal clause with title and items",
        block_schema_path="clause.schema.json",
    ),
    "signatures": ComponentSpec(
        name="signatures",
        sty_package="klartex-signatureblock",
        description="Signature block for parties",
        block_schema_path="signatures.schema.json",
    ),
    "description_list": ComponentSpec(
        name="description_list",
        sty_package=None,
        description="Label/value definition list (HTML <dl>) for meeting metadata, party info, key-value displays",
        block_schema_path="description_list.schema.json",
    ),
    "agenda": ComponentSpec(
        name="agenda",
        sty_package="klartex-agenda",
        description="§-numbered agenda with optional discussion and decisions",
        block_schema_path="agenda.schema.json",
    ),
    "name_roster": ComponentSpec(
        name="name_roster",
        sty_package="klartex-name-roster",
        description="Name/role/note table for board listings",
        block_schema_path="name_roster.schema.json",
    ),
    "page_break": ComponentSpec(
        name="page_break",
        sty_package=None,
        description="Force a page break",
        block_schema_path="page_break.schema.json",
    ),
    "list": ComponentSpec(
        name="list",
        sty_package=None,
        description="Bullet or numbered list, optionally nested",
        block_schema_path="list.schema.json",
    ),
    "table": ComponentSpec(
        name="table",
        sty_package=None,
        description="Simple data table with header and rows",
        block_schema_path="table.schema.json",
    ),
    "callout": ComponentSpec(
        name="callout",
        sty_package="klartex-callout",
        description="Visually distinct notice (info/tip/warning/danger/note)",
        block_schema_path="callout.schema.json",
    ),
    "quote": ComponentSpec(
        name="quote",
        sty_package=None,
        description="Typographic blockquote with optional attribution",
        block_schema_path="quote.schema.json",
    ),
    "latex": ComponentSpec(
        name="latex",
        sty_package=None,
        description="Raw LaTeX passthrough (not escaped)",
        block_schema_path="latex.schema.json",
    ),
    "resultatrakning": ComponentSpec(
        name="resultatrakning",
        sty_package="klartex-resultatrakning",
        description="Financial table with comparison years, grouped rows, subtotals, and note references",
        block_schema_path="resultatrakning.schema.json",
    ),
    "budgettabell": ComponentSpec(
        name="budgettabell",
        sty_package="klartex-budgettabell",
        description="Budget table with account codes, budgeted amounts, actuals, and percentages",
        block_schema_path="budgettabell.schema.json",
    ),
    "notapparat": ComponentSpec(
        name="notapparat",
        sty_package="klartex-notapparat",
        description="Numbered notes linked to financial tables",
        block_schema_path="notapparat.schema.json",
    ),
    # Legacy recipe component names (used by _recipe_base.tex.jinja)
    "klausuler": ComponentSpec(
        name="klausuler",
        sty_package="klartex-klausuler",
        description="Legal clause numbering with \\clause command (recipe component)",
    ),
    "signatureblock": ComponentSpec(
        name="signatureblock",
        sty_package="klartex-signatureblock",
        description="Two-party signature block (recipe component)",
    ),
    "titelsida": ComponentSpec(
        name="titelsida",
        sty_package="klartex-titelsida",
        description="Title page with two party names and document title (recipe component)",
    ),
    "invoice_header": ComponentSpec(
        name="invoice_header",
        sty_package=None,
        description="Right-aligned invoice header with number, date, due date",
    ),
    "invoice_recipient": ComponentSpec(
        name="invoice_recipient",
        sty_package=None,
        description="Recipient info and references in two columns",
    ),
    "invoice_table": ComponentSpec(
        name="invoice_table",
        sty_package=None,
        description="Invoice line items table with VAT and totals",
    ),
    "payment_info": ComponentSpec(
        name="payment_info",
        sty_package=None,
        description="Payment method table (bankgiro, IBAN, etc.)",
    ),
    "invoice_note": ComponentSpec(
        name="invoice_note",
        sty_package=None,
        description="Optional invoice footer note",
    ),
}


def get_component(name: str) -> ComponentSpec:
    """Look up a component by name.

    Raises:
        ValueError: If the component name is not registered.
    """
    if name not in _COMPONENTS:
        available = ", ".join(sorted(_COMPONENTS.keys()))
        raise ValueError(f"Unknown component '{name}'. Available: {available}")
    return _COMPONENTS[name]


def list_components() -> dict[str, ComponentSpec]:
    """Return all registered components."""
    return dict(_COMPONENTS)


def resolve_data_path(data: dict, path: str) -> Any:
    """Resolve a dot-notation path against a data dict.

    Example: resolve_data_path({"party1": {"name": "Acme"}}, "party1.name") -> "Acme"

    Returns None if the path doesn't exist.
    """
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def extract_component_data(
    component_type: str,
    data_map: dict[str, str] | None,
    data: dict,
) -> dict[str, Any]:
    """Extract data for a component using its data_map.

    Args:
        component_type: The component type name
        data_map: Mapping from component param names to data paths
        data: The full template data dict

    Returns:
        Dict of resolved parameter values
    """
    if not data_map:
        return {}
    return {
        param: resolve_data_path(data, path)
        for param, path in data_map.items()
    }
