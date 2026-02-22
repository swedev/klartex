"""Klartex HTTP API — FastAPI application."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from klartex.renderer import render, get_registry
from klartex.page_templates import list_page_templates
from klartex.components import get_component, list_components

app = FastAPI(title="Klartex", description="PDF generation via LaTeX")


class RenderRequest(BaseModel):
    template: str
    data: dict
    page_template_source: str | None = None


@app.post("/render")
def render_pdf(req: RenderRequest):
    """Render a template to PDF."""
    try:
        pdf_bytes = render(req.template, req.data, page_template_source=req.page_template_source)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={req.template}.pdf"},
    )


@app.get("/templates")
def list_templates():
    """List available templates."""
    registry = get_registry()
    result = []
    for info in sorted(registry.values(), key=lambda i: i.name):
        kind = "block-engine" if info.is_block_engine else "recipe"
        result.append({
            "name": info.name,
            "description": info.description,
            "type": kind,
        })
    return result


@app.get("/page-templates")
def get_page_templates():
    """List available page templates."""
    return list_page_templates()


@app.get("/blocks")
def list_blocks():
    """List available block types for the block engine."""
    components = list_components()
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "has_schema": spec.block_schema_path is not None,
        }
        for spec in sorted(components.values(), key=lambda s: s.name)
        if spec.block_schema_path is not None
    ]


@app.get("/blocks/{name}/schema")
def get_block_schema(name: str):
    """Get the JSON Schema for a block type."""
    try:
        spec = get_component(name)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Block type '{name}' not found")
    schema = spec.get_block_schema()
    if schema is None:
        raise HTTPException(
            status_code=404, detail=f"No schema defined for block type '{name}'"
        )
    return schema


@app.get("/templates/{name}/schema")
def get_schema(name: str):
    """Get the JSON Schema for a template."""
    registry = get_registry()
    if name not in registry:
        raise HTTPException(status_code=404, detail=f"Template '{name}' not found")
    return registry[name].schema
