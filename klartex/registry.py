"""Discover and load templates from the templates directory."""

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path

from klartex.block_engine import BLOCK_ENGINE_TEMPLATE
from klartex.page_templates import (
    BLOCK_DEFAULT_TEXT,
    page_template_schema,
)
from klartex.recipe import describe_recipe_defaults, load_recipe


@dataclass
class TemplateInfo:
    name: str
    description: str
    schema: dict
    recipe_path: Path | None = None
    is_block_engine: bool = False
    validation_schema: dict | None = None

    def get_validation_schema(self) -> dict:
        """Return the schema used for runtime validation.

        For the block engine, this is the base schema without oneOf
        (per-block validation in the renderer gives better errors).
        For recipe templates, this is the same as the display schema.
        """
        return self.validation_schema if self.validation_schema is not None else self.schema


# Path to block engine schema
_SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"


def _inject_page_template(schema: dict, default_text: str) -> None:
    """Replace the schema file's ``page_template`` placeholder with the
    subtree generated from the slot model, so every template validates and
    documents the same page-template surface."""
    schema.setdefault("properties", {})["page_template"] = page_template_schema(default_text)


def discover_templates(templates_dir: Path) -> dict[str, TemplateInfo]:
    """Scan templates/ for subdirectories containing schema.json + recipe.yaml.

    Also registers the virtual ``_block`` template for the block engine.
    """
    templates = {}
    for schema_path in sorted(templates_dir.glob("*/schema.json")):
        name = schema_path.parent.name
        if name.startswith("_"):
            continue
        recipe_yaml = schema_path.parent / "recipe.yaml"
        if not recipe_yaml.exists():
            continue

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        # The default text is the recipe's own: a recipe declaring its slots
        # (faktura and kvitto's derived columns footer) must document them
        # where an agent reads the schema.
        _inject_page_template(
            schema, describe_recipe_defaults(load_recipe(recipe_yaml).document)
        )

        templates[name] = TemplateInfo(
            name=name,
            schema=schema,
            recipe_path=recipe_yaml,
            description=schema.get("description", ""),
        )

    # Register the block engine as a virtual template
    block_schema_path = _SCHEMAS_DIR / "block_engine.schema.json"
    if block_schema_path.exists():
        block_schema = json.loads(block_schema_path.read_text(encoding="utf-8"))
        _inject_page_template(block_schema, BLOCK_DEFAULT_TEXT)

        # Build discriminated union from per-block schemas for CLI/API display
        from klartex.components import _COMPONENTS

        base_schema = block_schema
        seen_paths = set()
        block_type_schemas = []
        for name, spec in sorted(_COMPONENTS.items()):
            if spec.block_schema_path and spec.block_schema_path not in seen_paths:
                s = spec.get_block_schema()
                if s:
                    seen_paths.add(spec.block_schema_path)
                    block_type_schemas.append(s)
        if block_type_schemas:
            display_schema = copy.deepcopy(base_schema)
            display_schema["properties"]["body"]["items"] = {
                "oneOf": block_type_schemas
            }
        else:
            display_schema = base_schema

        templates[BLOCK_ENGINE_TEMPLATE] = TemplateInfo(
            name=BLOCK_ENGINE_TEMPLATE,
            schema=display_schema,
            validation_schema=base_schema,
            description=base_schema.get("description", "Universal block engine"),
            is_block_engine=True,
        )

    return templates
