"""Klartex HTTP API — FastAPI application."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from klartex.renderer import render, get_registry

app = FastAPI(title="Klartex", description="PDF generation via LaTeX")


class RenderRequest(BaseModel):
    template: str
    data: dict
    branding: str = "default"
    branding_dir: str | None = None


@app.post("/render")
def render_pdf(req: RenderRequest):
    """Render a template to PDF."""
    try:
        pdf_bytes = render(req.template, req.data, branding=req.branding, branding_dir=req.branding_dir)
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
    return [
        {"name": info.name, "description": info.description}
        for info in sorted(registry.values(), key=lambda i: i.name)
    ]


@app.get("/templates/{name}/schema")
def get_schema(name: str):
    """Get the JSON Schema for a template."""
    registry = get_registry()
    if name not in registry:
        raise HTTPException(status_code=404, detail=f"Template '{name}' not found")
    return registry[name].schema
