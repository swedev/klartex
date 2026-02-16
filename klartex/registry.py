"""Discover and load templates from the templates directory."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TemplateInfo:
    name: str
    description: str
    schema: dict
    template_path: Path


def discover_templates(templates_dir: Path) -> dict[str, TemplateInfo]:
    """Scan templates/ for subdirectories containing schema.json + .tex.jinja."""
    templates = {}
    for schema_path in sorted(templates_dir.glob("*/schema.json")):
        name = schema_path.parent.name
        if name.startswith("_"):
            continue
        schema = json.loads(schema_path.read_text())
        tex_jinja = schema_path.parent / f"{name}.tex.jinja"
        if tex_jinja.exists():
            templates[name] = TemplateInfo(
                name=name,
                schema=schema,
                template_path=tex_jinja,
                description=schema.get("description", ""),
            )
    return templates
