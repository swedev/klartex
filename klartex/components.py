"""Component registry — maps component type names to LaTeX packages and macros.

Each component defines:
- sty_package: The .sty package to load (or None if no extra package needed)
- latex_macro: The primary LaTeX macro/environment name
- extract_data: Function to extract relevant data from the template data dict
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ComponentSpec:
    """Specification for a document component."""

    name: str
    sty_package: str | None = None
    description: str = ""


# Registry of known component types
_COMPONENTS: dict[str, ComponentSpec] = {
    "heading": ComponentSpec(
        name="heading",
        sty_package=None,
        description="Centered heading with optional subtitle",
    ),
    "metadata_table": ComponentSpec(
        name="metadata_table",
        sty_package=None,
        description="Key-value metadata table (date, location, etc.)",
    ),
    "attendees": ComponentSpec(
        name="attendees",
        sty_package=None,
        description="Attendee and adjuster list",
    ),
    "klausuler": ComponentSpec(
        name="klausuler",
        sty_package="klartex-klausuler",
        description="Legal clause numbering with \\clause command",
    ),
    "signaturblock": ComponentSpec(
        name="signaturblock",
        sty_package="klartex-signaturblock",
        description="Two-party signature block",
    ),
    "titelsida": ComponentSpec(
        name="titelsida",
        sty_package="klartex-titelsida",
        description="Title page with two party names and document title",
    ),
    "adjuster_signatures": ComponentSpec(
        name="adjuster_signatures",
        sty_package="klartex-signaturblock",
        description="Adjuster signature lines (for protokoll)",
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
