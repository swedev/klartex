"""Recipe loader and orchestration.

Loads YAML recipe files, validates them against the recipe schema,
and prepares template context for the Jinja meta-template.

This module does NOT generate LaTeX. LaTeX generation is handled
entirely by the meta-template (_recipe_base.tex.jinja).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from klartex.branding import Branding
from klartex.components import (
    ComponentSpec,
    extract_component_data,
    get_component,
)
from klartex.page_templates import load_page_template

# Path to the recipe format schema
_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "recipe.schema.json"
_recipe_schema: dict | None = None


def _get_recipe_schema() -> dict:
    """Load and cache the recipe JSON Schema."""
    global _recipe_schema
    if _recipe_schema is None:
        import json

        _recipe_schema = json.loads(_SCHEMA_PATH.read_text())
    return _recipe_schema


@dataclass
class RecipeComponent:
    """A component entry in a recipe."""

    type: str
    data_map: dict[str, str] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    spec: ComponentSpec | None = None


@dataclass
class RecipeDocument:
    """Document-level settings from a recipe."""

    title: str = ""
    page_template: str = "formal"
    metadata: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Recipe:
    """Parsed recipe definition."""

    name: str
    description: str
    lang: str = "sv"
    document: RecipeDocument = field(default_factory=RecipeDocument)
    components: list[RecipeComponent] = field(default_factory=list)
    content_fields: dict[str, dict[str, str]] = field(default_factory=dict)
    schema_path: str | None = None
    source_path: Path | None = None


def load_recipe(path: Path) -> Recipe:
    """Parse a YAML recipe file and validate against the recipe schema.

    Args:
        path: Path to the recipe.yaml file

    Returns:
        Parsed Recipe dataclass

    Raises:
        jsonschema.ValidationError: If the recipe YAML is invalid
        FileNotFoundError: If the file doesn't exist
    """
    raw = yaml.safe_load(path.read_text())

    # Validate against recipe schema
    schema = _get_recipe_schema()
    jsonschema.validate(raw, schema)

    # Parse template section
    tmpl = raw["template"]
    name = tmpl["name"]
    description = tmpl["description"]
    lang = tmpl.get("lang", "sv")

    # Parse document section
    doc_raw = raw.get("document", {})
    document = RecipeDocument(
        title=doc_raw.get("title", ""),
        page_template=doc_raw.get("page_template", "formal"),
        metadata=doc_raw.get("metadata", []),
    )

    # Parse components
    components = []
    for comp_raw in raw.get("components", []):
        comp_type = comp_raw["type"]
        spec = get_component(comp_type)
        components.append(
            RecipeComponent(
                type=comp_type,
                data_map=comp_raw.get("data_map", {}),
                options=comp_raw.get("options", {}),
                spec=spec,
            )
        )

    # Parse content fields
    content_fields = raw.get("content_fields", {})

    return Recipe(
        name=name,
        description=description,
        lang=lang,
        document=document,
        components=components,
        content_fields=content_fields,
        schema_path=raw.get("schema"),
        source_path=path,
    )


def prepare_recipe_context(
    recipe: Recipe,
    data: dict,
    brand: Branding,
) -> dict[str, Any]:
    """Build a template context dict for the Jinja meta-template.

    The context includes the recipe structure, resolved component data,
    and branding. Data should already be escaped via escape_data() before
    calling this function.

    Args:
        recipe: Parsed recipe
        data: Template data (already escaped for LaTeX)
        brand: Branding configuration

    Returns:
        Context dict for rendering _recipe_base.tex.jinja
    """
    # Resolve the document title (it's a Jinja expression)
    # We'll pass it through as-is and let the meta-template render it
    # Actually, the title may contain {{ data.xxx }} expressions,
    # so we render it here using a mini Jinja environment
    import jinja2

    title_env = jinja2.Environment(autoescape=False)
    try:
        title_template = title_env.from_string(recipe.document.title)
        rendered_title = title_template.render(data=data)
    except jinja2.TemplateError:
        rendered_title = recipe.document.title

    # Resolve page template (may contain Jinja expression like {{ data.page_template | default('formal') }})
    try:
        pt_template = title_env.from_string(recipe.document.page_template)
        rendered_page_template = pt_template.render(data=data)
    except jinja2.TemplateError:
        rendered_page_template = recipe.document.page_template

    # Resolve metadata fields
    resolved_metadata = []
    for meta in recipe.document.metadata:
        field_path = meta["field"]
        value = _resolve_path(data, field_path)
        optional = meta.get("optional", False)
        if optional and value is None:
            continue

        # Build display value with optional suffix fields (e.g., time_start/time_end)
        display_value = value if value is not None else ""
        suffix_fields = meta.get("suffix_fields", [])
        if suffix_fields:
            separator = meta.get("suffix_separator", ", ")
            suffix_parts = []
            for sf in suffix_fields:
                sv = _resolve_path(data, sf)
                if sv is not None:
                    suffix_parts.append(str(sv))
            if suffix_parts:
                display_value = f"{display_value}, {separator.join(suffix_parts)}"

        resolved_metadata.append({
            "label": meta["label"],
            "value": display_value,
        })

    # Resolve component data
    resolved_components = []
    for comp in recipe.components:
        comp_data = extract_component_data(comp.type, comp.data_map, data)
        resolved_components.append({
            "type": comp.type,
            "data": comp_data,
            "options": comp.options,
            "spec": comp.spec,
        })

    # Collect required .sty packages
    sty_packages = []
    seen = set()
    for comp in recipe.components:
        if comp.spec and comp.spec.sty_package and comp.spec.sty_package not in seen:
            sty_packages.append(comp.spec.sty_package)
            seen.add(comp.spec.sty_package)

    # Resolve page template
    page_tmpl = load_page_template(rendered_page_template)

    return {
        "recipe": recipe,
        "data": data,
        "brand": brand,
        "title": rendered_title,
        "page_template_include": page_tmpl.include,
        "metadata": resolved_metadata,
        "components": resolved_components,
        "sty_packages": sty_packages,
        "lang": recipe.lang,
    }


def _resolve_path(data: dict, path: str) -> Any:
    """Resolve a dot-notation path in a data dict."""
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current
