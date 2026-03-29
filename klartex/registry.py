"""Discover and load templates from the templates directory."""

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path

from klartex.block_engine import BLOCK_ENGINE_TEMPLATE


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


def discover_templates(templates_dir: Path) -> dict[str, TemplateInfo]:
    """Scan templates/ for subdirectories containing schema.json + recipe.yaml.

    Also registers the virtual ``_block`` template for the block engine.
    """
    templates = {}
    for schema_path in sorted(templates_dir.glob("*/schema.json")):
        name = schema_path.parent.name
        if name.startswith("_"):
            continue
        schema = json.loads(schema_path.read_text())

        recipe_yaml = schema_path.parent / "recipe.yaml"
        if not recipe_yaml.exists():
            continue

        templates[name] = TemplateInfo(
            name=name,
            schema=schema,
            recipe_path=recipe_yaml,
            description=schema.get("description", ""),
        )

    # Register the block engine as a virtual template
    block_schema_path = _SCHEMAS_DIR / "block_engine.schema.json"
    if block_schema_path.exists():
        block_schema = json.loads(block_schema_path.read_text())

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
