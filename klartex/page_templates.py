"""Page template loader and registry.

Page templates define page-level chrome: header/footer layout, margins,
page numbering, etc. Each page template is a self-contained ``.tex.jinja``
file in the ``page_templates/`` directory.

Built-in names (``formal``, ``clean``, ``none``) resolve to
``page_templates/{name}.tex.jinja``.

Page template data in the render request can be either a string (shorthand)
or an object with overrides::

    "page_template": "formal"

    "page_template": {
        "name": "formal",
        "page_numbers": false,
        "first_page_header": false,
        "font": "Futura",
        "header_font": "Futura",
        "footer": {
            "company": "Bolaget AB",
            "org_number": "556123-4567",
            "bankgiro": "1234-5678"
        }
    }
"""

from dataclasses import dataclass, field
from pathlib import Path

# Default directory for page template definitions
_ROOT = Path(__file__).resolve().parent
PAGE_TEMPLATES_DIR = _ROOT / "page_templates"

# Built-in template defaults
_BUILTIN_DEFAULTS: dict[str, dict] = {
    "formal": {
        "description": "Logo top-left, org name in header, page numbers in footer",
        "page_numbers": True,
        "first_page_header": True,
    },
    "clean": {
        "description": "Logo only in header, page numbers in footer, no org details",
        "page_numbers": True,
        "first_page_header": True,
    },
    "none": {
        "description": "No header, page numbers only in footer",
        "page_numbers": True,
        "first_page_header": False,
    },
}


# Footer fields grouped by footer column, in render order
FOOTER_COMPANY_FIELDS = ("company", "address", "seat")
FOOTER_CONTACT_FIELDS = ("phone", "email", "web")
FOOTER_PAYMENT_FIELDS = ("bankgiro", "plusgiro", "iban", "bic")
FOOTER_ORG_FIELDS = ("org_number", "vat_number", "f_tax")
FOOTER_FIELDS = (
    FOOTER_COMPANY_FIELDS
    + FOOTER_CONTACT_FIELDS
    + FOOTER_PAYMENT_FIELDS
    + FOOTER_ORG_FIELDS
)


@dataclass
class PageTemplate:
    """Resolved page template definition."""

    name: str
    description: str = ""
    page_numbers: bool = True
    first_page_header: bool = True
    font: str | None = None
    header_font: str | None = None
    footer: dict = field(default_factory=dict)
    diff_highlight: str = "none"

    @property
    def footer_has_payment(self) -> bool:
        """True when the footer carries any payment field — the signal for
        the faktura recipe to suppress its in-body payment_info block."""
        return any(self.footer.get(f) for f in FOOTER_PAYMENT_FIELDS)


def load_page_template(
    spec: str | dict,
) -> PageTemplate:
    """Load a page template by name or spec dict.

    Args:
        spec: Either a template name string, or a dict with ``name`` and
              optional overrides (``page_numbers``, ``first_page_header``,
              ``font``, ``header_font``, ``footer``, ``diff_highlight``).

    Returns:
        Resolved PageTemplate with defaults and overrides applied.

    Raises:
        ValueError: If the template name is not found.
    """
    if isinstance(spec, str):
        name = spec
        overrides: dict = {}
    else:
        name = spec["name"]
        overrides = {k: v for k, v in spec.items() if k != "name"}

    if name not in _BUILTIN_DEFAULTS:
        available = ", ".join(sorted(_BUILTIN_DEFAULTS.keys()))
        raise ValueError(
            f"Unknown page template '{name}'. Available: {available}"
        )

    defaults = _BUILTIN_DEFAULTS[name]

    return PageTemplate(
        name=name,
        description=defaults["description"],
        page_numbers=overrides.get("page_numbers", defaults["page_numbers"]),
        first_page_header=overrides.get(
            "first_page_header", defaults["first_page_header"]
        ),
        font=overrides.get("font"),
        header_font=overrides.get("header_font", overrides.get("font")),
        footer=overrides.get("footer") or {},
        diff_highlight=overrides.get("diff_highlight") or "none",
    )


def read_page_template_source(name: str) -> str:
    """Read the .tex.jinja source for a built-in page template.

    Args:
        name: Built-in template name (e.g. "formal").

    Returns:
        The raw .tex.jinja content as a string.

    Raises:
        FileNotFoundError: If the template file doesn't exist.
    """
    path = PAGE_TEMPLATES_DIR / f"{name}.tex.jinja"
    return path.read_text(encoding="utf-8")


def list_page_templates() -> list[dict]:
    """Return all available built-in page templates with metadata.

    Returns:
        List of dicts with name, description, and defaults.
    """
    return [
        {
            "name": name,
            "description": info["description"],
            "defaults": {
                "page_numbers": info["page_numbers"],
                "first_page_header": info["first_page_header"],
            },
        }
        for name, info in sorted(_BUILTIN_DEFAULTS.items())
    ]
