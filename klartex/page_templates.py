"""Page template loader and registry.

Page templates define page-level chrome: header/footer includes, margins,
page numbering, etc. They replace the simple ``header`` enum with a richer
abstraction that bundles header + footer + options.

A page template is a small YAML file in the ``page_templates/`` directory.
The ``include`` field references the existing ``_header_*.jinja`` include
that sets both header and footer layout.

Page template data in the render request can be either a string (shorthand)
or an object with overrides::

    "page_template": "formal"

    "page_template": {
        "name": "formal",
        "page_numbers": false,
        "first_page_header": false
    }
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Default directory for page template definitions
_ROOT = Path(__file__).resolve().parent.parent
PAGE_TEMPLATES_DIR = _ROOT / "page_templates"


@dataclass
class PageTemplate:
    """Resolved page template definition."""

    name: str
    description: str = ""
    include: str = "_header_standard.jinja"
    defaults: dict = field(default_factory=dict)
    overrides: dict = field(default_factory=dict)

    @property
    def page_numbers(self) -> bool:
        """Whether page numbers are shown."""
        return self.overrides.get(
            "page_numbers", self.defaults.get("page_numbers", True)
        )

    @property
    def first_page_header(self) -> bool:
        """Whether the header is shown on the first page."""
        return self.overrides.get(
            "first_page_header", self.defaults.get("first_page_header", True)
        )


# Cached registry keyed by directory path
_page_templates_cache: dict[Path, dict[str, dict]] = {}


def _load_all(templates_dir: Path | None = None) -> dict[str, dict]:
    """Load and cache all page template YAML files."""
    directory = templates_dir or PAGE_TEMPLATES_DIR
    if directory in _page_templates_cache:
        return _page_templates_cache[directory]

    result = {}
    for yaml_path in sorted(directory.glob("*.yaml")):
        raw = yaml.safe_load(yaml_path.read_text())
        name = raw["name"]
        result[name] = raw
    _page_templates_cache[directory] = result
    return result


def load_page_template(
    spec: str | dict,
    templates_dir: Path | None = None,
) -> PageTemplate:
    """Load a page template by name or spec dict.

    Args:
        spec: Either a template name string, or a dict with ``name`` and
              optional overrides (``page_numbers``, ``first_page_header``).
        templates_dir: Directory to load templates from (default: built-in).

    Returns:
        Resolved PageTemplate with defaults and overrides applied.

    Raises:
        ValueError: If the template name is not found.
    """
    if isinstance(spec, str):
        name = spec
        overrides = {}
    else:
        name = spec["name"]
        overrides = {k: v for k, v in spec.items() if k != "name"}

    registry = _load_all(templates_dir)
    if name not in registry:
        available = ", ".join(sorted(registry.keys()))
        raise ValueError(
            f"Unknown page template '{name}'. Available: {available}"
        )

    raw = registry[name]
    return PageTemplate(
        name=name,
        description=raw.get("description", ""),
        include=raw.get("include", "_header_standard.jinja"),
        defaults=raw.get("defaults", {}),
        overrides=overrides,
    )



def list_page_templates(
    templates_dir: Path | None = None,
) -> list[dict]:
    """Return all available page templates with metadata.

    Returns:
        List of dicts with name, description, include, and defaults.
    """
    registry = _load_all(templates_dir)
    return [
        {
            "name": raw["name"],
            "description": raw.get("description", ""),
            "defaults": raw.get("defaults", {}),
        }
        for raw in sorted(registry.values(), key=lambda r: r["name"])
    ]


def reset_cache() -> None:
    """Clear the cached page templates (useful for testing)."""
    _page_templates_cache.clear()
