"""Recipe loader and orchestration.

Loads YAML recipe files, validates them against the recipe schema,
and prepares template context for the Jinja meta-template.

This module does NOT generate LaTeX. LaTeX generation is handled
entirely by the meta-template (_recipe_base.tex.jinja).
"""

import copy
import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from klartex.components import (
    ComponentSpec,
    extract_component_data,
    get_component,
    resolve_data_path,
)
from klartex.page_templates import (
    FOOTER_VARIANTS,
    HEADER_VARIANTS,
    RECIPE_DEFAULT_SLOTS,
    PageTemplate,
    load_page_template,
)

# Path to the recipe format schema
_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "recipe.schema.json"
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
    class_options: str = ""
    #: Slot object, in payload syntax, for the slots data.page_template
    #: leaves out.
    page_template: dict = field(default_factory=lambda: dict(RECIPE_DEFAULT_SLOTS))
    metadata: list[dict[str, Any]] = field(default_factory=list)
    #: Footer field name -> dot-path, or list of dot-paths, into the payload
    #: data. Resolved per render and merged under the payload's own footer
    #: fields. Empty unless the recipe's footer slot declares ``fields_from``.
    footer_fields_from: dict[str, str | list[str]] = field(default_factory=dict)
    #: The variant ``footer_fields_from`` was declared for; None when unset.
    footer_fields_from_variant: str | None = None
    #: True when a columns footer names its gaps instead of dropping them.
    label_missing_footer_fields: bool = False


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


def _pop_fields_from(page_template: dict, path: Path) -> tuple[dict, str | None]:
    """Take ``fields_from`` off the recipe's footer slot object and validate it.

    ``page_template`` is edited in place, so what remains is payload syntax
    ``load_page_template`` accepts. Returns the map and the variant it was
    declared for, both empty when no slot declares one.

    Raises:
        ValueError: If the map sits anywhere but a footer slot object, on a
            variant that has no fields, beside a literal ``fields``, names a
            field the variant does not have, or carries a path that is not a
            non-empty string or a non-empty list of non-empty strings.
    """
    header = page_template.get("header")
    misplaced = "fields_from" in page_template or (
        isinstance(header, dict) and "fields_from" in header
    )
    if misplaced:
        raise ValueError(
            f"{path}: fields_from belongs on the footer slot object "
            f"(page_template.footer), beside its variant."
        )

    footer = page_template.get("footer")
    if not isinstance(footer, dict) or "fields_from" not in footer:
        return {}, None

    fields_from = footer.pop("fields_from")
    variant = footer.get("variant")
    if variant not in FOOTER_VARIANTS or not FOOTER_VARIANTS[variant].fields:
        raise ValueError(
            f"{path}: fields_from needs a footer slot object whose variant has "
            f"fields; got {variant!r}."
        )
    if "fields" in footer:
        raise ValueError(
            f"{path}: a footer slot carries either fields or fields_from, not "
            f"both — the {variant} footer declares both."
        )
    if not isinstance(fields_from, dict) or not fields_from:
        raise ValueError(
            f"{path}: fields_from must be a non-empty object mapping "
            f"{variant} footer fields to data paths."
        )

    known = FOOTER_VARIANTS[variant].fields
    for name, source in fields_from.items():
        if name not in known:
            raise ValueError(
                f"{path}: fields_from.{name} is not a field of the {variant} "
                f"footer (fields: {', '.join(known)})."
            )
        paths = source if isinstance(source, list) else [source]
        if not paths or not all(isinstance(p, str) and p.strip() for p in paths):
            raise ValueError(
                f"{path}: fields_from.{name} must be a non-empty dot-path or a "
                f"non-empty list of non-empty dot-paths, got {source!r}."
            )

    return fields_from, variant


def _derive_slot_fields(
    fields_from: dict[str, str | list[str]], data: dict
) -> dict[str, Any]:
    """Resolve a ``fields_from`` map against the payload data.

    A string path yields the value when it is set; a list of paths yields the
    list of set values. A field whose paths all resolve to nothing is left
    out, so the merge never plants an empty value over a derived one.
    """
    derived: dict[str, Any] = {}
    for name, source in fields_from.items():
        if isinstance(source, list):
            values = [v for p in source if (v := resolve_data_path(data, p))]
            if values:
                derived[name] = values
            continue
        value = resolve_data_path(data, source)
        if value:
            derived[name] = value
    return derived


def describe_recipe_defaults(document: RecipeDocument) -> str:
    """One clause naming what a left-out page-template slot resolves to for
    this recipe — the ``default_text`` of the injected ``page_template``
    schema subtree."""

    def slot_text(slot: str, variants: dict) -> str:
        value = document.page_template.get(slot)
        variant = value.get("variant") if isinstance(value, dict) else value
        if variant is None:
            return f"an empty {slot}"
        text = f"the {variants[variant].label} {slot}"
        if isinstance(value, dict) and value.get("title"):
            text += " with the document title"
        return text

    footer = slot_text("footer", FOOTER_VARIANTS)
    if document.footer_fields_from:
        # Declaration order, not sorted: the map is written seller-first, and
        # the sentence reads the way the recipe does.
        sources = dict.fromkeys(
            path.split(".")[0]
            for source in document.footer_fields_from.values()
            for path in (source if isinstance(source, list) else [source])
        )
        footer += f", with fields derived from {', '.join(sources)}"
    return f"{slot_text('header', HEADER_VARIANTS)} and {footer}"


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
    # The derivation map is recipe syntax, not payload syntax: taking it off
    # the slot object leaves behind something load_page_template accepts.
    page_template = copy.deepcopy(doc_raw.get("page_template") or {})
    fields_from, fields_from_variant = _pop_fields_from(page_template, path)
    document = RecipeDocument(
        title=doc_raw.get("title", ""),
        class_options=doc_raw.get("class_options", ""),
        # A partial slot object (one slot named) falls back to the recipe
        # default for the other slot, so load_page_template always gets both.
        page_template={**RECIPE_DEFAULT_SLOTS, **page_template},
        metadata=doc_raw.get("metadata", []),
        footer_fields_from=fields_from,
        footer_fields_from_variant=fields_from_variant,
        label_missing_footer_fields=doc_raw.get("label_missing_footer_fields", False),
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
    *,
    header_source: str | None = None,
    footer_source: str | None = None,
    page_template_source: str | None = None,
) -> dict[str, Any]:
    """Build a template context dict for the Jinja meta-template.

    The context includes the recipe structure, resolved component data,
    and page template settings. Data should already be escaped via
    escape_data() before calling this function.

    Args:
        recipe: Parsed recipe
        data: Template data (already escaped for LaTeX)
        header_source: Optional raw .tex.jinja content owning the header slot.
        footer_source: Optional raw .tex.jinja content owning the footer slot.
        page_template_source: Optional raw content owning both slots.

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

    # Resolve metadata fields
    resolved_metadata = []
    for meta in recipe.document.metadata:
        field_path = meta["field"]
        value = _resolve_path(data, field_path)
        optional = meta.get("optional", False)
        if optional and value is None:
            continue

        # Build display value with optional suffix fields (e.g., time_start/time_end).
        # List-typed values (e.g. attendees, adjusters) are joined with ', ' so the
        # downstream description_list renderer can treat every value as a string.
        if isinstance(value, list):
            display_value = ", ".join(str(v) for v in value)
        elif value is not None:
            display_value = value
        else:
            display_value = ""
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
    # Resolve page template: the recipe's slot object fills in whatever
    # data.page_template leaves out.
    page_tmpl = load_page_template(
        data.get("page_template"),
        defaults=recipe.document.page_template,
        header_source=header_source,
        footer_source=footer_source,
        page_template_source=page_template_source,
    )
    page_tmpl = _merge_derived_footer_fields(recipe.document, page_tmpl, data)

    return {
        "recipe": recipe,
        "data": data,
        "title": rendered_title,
        "class_options": recipe.document.class_options,
        "page_template": page_tmpl,
        "metadata": resolved_metadata,
        "components": resolved_components,
        "sty_packages": sty_packages,
        "lang": recipe.lang,
        "number_format": data.get("number_format"),
        "label_missing_footer_fields": recipe.document.label_missing_footer_fields,
    }


def _merge_derived_footer_fields(
    document: RecipeDocument, template: PageTemplate, data: dict
) -> PageTemplate:
    """Fill the recipe's derived footer fields into the resolved footer slot.

    The payload wins key by key: a field the payload's footer sets keeps its
    value, and a field it leaves out — or sets to ``""``, ``[]`` or ``null``,
    the same "unset" ``footer_keyvals`` and ``footer_has_payment`` read — takes
    the derived value. The merge applies only to a predefined footer of the
    variant the map was declared for; another variant, an empty footer or a
    custom source is left exactly as resolved.

    The recipe's own dicts and the loaded ``PageTemplate`` are never mutated —
    a recipe is loaded once and rendered for many payloads.
    """
    if not document.footer_fields_from:
        return template
    footer = template.footer
    if not footer.is_predefined or footer.variant != document.footer_fields_from_variant:
        return template

    supplied = footer.fields
    merged = dict(supplied)
    for name, value in _derive_slot_fields(document.footer_fields_from, data).items():
        if not merged.get(name):
            merged[name] = value
    if merged == supplied:
        return template
    return dataclasses.replace(
        template,
        footer=dataclasses.replace(
            footer, settings={**footer.settings, "fields": merged}
        ),
    )


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
