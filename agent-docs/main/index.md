# Main Branch

**Branch:** main

## Overview

Klartex is an open source PDF generation service: structured JSON data + template name → professional PDF via XeLaTeX.

Three consumption modes: Python library, CLI tool, HTTP service (FastAPI).

### Templates

- `protokoll` (meeting minutes) — YAML recipe
- `faktura` (invoice) — YAML recipe
- `_block` (universal block engine) — agent composes `body[]` freely from typed blocks

### Page Templates

Page templates (`.tex.jinja` files) control page-level chrome: headers, footers, colors, logos. Three built-in: `formal`, `clean`, `none`. External page templates are passed as source content via `--page-template` (CLI) or `page_template_source` (API) — no path resolution, the caller reads the file and passes the content in.

### Rendering Paths

- **Recipe path**: YAML recipe declares components + data mappings → `_recipe_base.tex.jinja`
- **Block engine path**: Agent composes `body[]` from typed blocks → `_block_engine.tex.jinja`

Both paths inject page template source directly into the preamble (no Jinja include).

## Context Files

(Add project-brief.md, tech-context.md, system-patterns.md as the project matures)
