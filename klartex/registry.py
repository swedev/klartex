"""Discover and load templates from the templates directory."""

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TemplateInfo:
    name: str
    description: str
    schema: dict
    template_path: Path | None = None
    recipe_path: Path | None = None

    @property
    def has_legacy(self) -> bool:
        """Whether this template has a monolithic .tex.jinja file."""
        return self.template_path is not None

    @property
    def has_recipe(self) -> bool:
        """Whether this template has a recipe.yaml file."""
        return self.recipe_path is not None


def discover_templates(templates_dir: Path) -> dict[str, TemplateInfo]:
    """Scan templates/ for subdirectories containing schema.json + (.tex.jinja and/or recipe.yaml)."""
    templates = {}
    for schema_path in sorted(templates_dir.glob("*/schema.json")):
        name = schema_path.parent.name
        if name.startswith("_"):
            continue
        schema = json.loads(schema_path.read_text())

        tex_jinja = schema_path.parent / f"{name}.tex.jinja"
        recipe_yaml = schema_path.parent / "recipe.yaml"

        has_tex = tex_jinja.exists()
        has_recipe = recipe_yaml.exists()

        # A template must have at least one of .tex.jinja or recipe.yaml
        if not has_tex and not has_recipe:
            continue

        templates[name] = TemplateInfo(
            name=name,
            schema=schema,
            template_path=tex_jinja if has_tex else None,
            recipe_path=recipe_yaml if has_recipe else None,
            description=schema.get("description", ""),
        )
    return templates
