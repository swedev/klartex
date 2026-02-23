"""Discover and load templates from the templates directory."""

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
        templates[BLOCK_ENGINE_TEMPLATE] = TemplateInfo(
            name=BLOCK_ENGINE_TEMPLATE,
            schema=block_schema,
            description=block_schema.get("description", "Universal block engine"),
            is_block_engine=True,
        )

    return templates
