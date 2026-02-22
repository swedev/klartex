# Implementation Plan: Foreningskomponenter -- dagordning + namnrollista

## Summary

Create two reusable LaTeX component packages (`klartex-dagordning.sty` and `klartex-namnrollista.sty`) for Swedish association documents. These components extract recurring patterns from existing monolithic templates into standalone `.sty` files with self-describing `.meta.yaml` metadata. The dagordning component provides paragraph-numbered agenda lists; the namnrollista component provides formatted name/role tables.

## Triage Info

> Decision-support metadata for this issue.

| Field | Value |
|-------|-------|
| **Blocked by** | #9 Composable architecture -- YAML-recept-engine + .sty-komponenter (OPEN) |
| **Blocks** | None |
| **Related issues** | #15 Self-describing metadata -- meta.yaml per komponent (OPEN) |
| **Scope** | 8-10 files across `cls/`, `templates/protokoll/`, `klartex/`, `tests/` |
| **Risk** | Medium -- depends on #9 architecture decisions |
| **Complexity** | Medium |
| **Safe for junior** | Yes (once #9 is done and the component pattern is established) |
| **Conflict risk** | Medium -- #9 will restructure the component/template architecture; shares `tests/test_components.py` and `klartex/components.py` with #9 |

### Triage Notes

This issue explicitly depends on #9 (composable architecture). The issue body states: "Beror pa #9 (composable architecture)." Issue #9 will establish the pattern for breaking out `.sty` components from `klartex-base.cls` and creating a YAML recipe engine.

From the #9 plan, the architecture decisions relevant to this issue are:
- `.sty` files live in `cls/` directory with `klartex-` prefix naming (e.g., `cls/klartex-dagordning.sty`)
- A `klartex/components.py` module maps component names to LaTeX packages/macros/data extraction
- The renderer will symlink the entire `cls/` directory to the temp build directory
- A Jinja meta-template (`templates/_recipe_base.tex.jinja`) handles recipe-based rendering

Issue #15 (self-describing metadata) defines the `.meta.yaml` format that each component must include. While #15 is not listed as a hard blocker, the issue body references it: "Varje komponent ska ha en `.meta.yaml` med inputs, beskrivning och forekomst -- se #15."

**Recommendation:** Wait for #9 to land first. This plan aligns with the architecture decisions in #9's plan and should be updated if those decisions change during implementation.

## Analysis

### Current State

The protokoll template (`templates/protokoll/protokoll.tex.jinja`) already has agenda items (dagordning) rendered via hardcoded Jinja2:

```latex
\begin{clauses}
\BLOCK{for item in data.agenda_items}
\clause{\VAR{item.title}}
\BLOCK{if item.discussion}
\VAR{item.discussion}
\BLOCK{endif}
\BLOCK{if item.decision}
\textbf{Beslut:} \VAR{item.decision}
\BLOCK{endif}
\BLOCK{endfor}
\end{clauses}
```

This uses the `clauses` environment from `klartex-base.cls` (lines 116-147), which provides numbered clauses with `\clause{}` commands. However, the issue requests a separate dagordning component with paragraph-sign numbering, not the current clause numbering.

For namnrollista, there is no existing implementation. Attendee lists in the protokoll template are rendered as simple comma-joined strings (`data.attendees | join(', ')`).

### Key Considerations

1. **Directory structure**: Per #9's plan, `.sty` files go in `cls/` with `klartex-` prefix. The renderer will symlink the entire `cls/` directory.
2. **Component registry**: #9 creates `klartex/components.py` with a mapping from component name to `.sty` package, LaTeX macro, and data extraction function. This issue must register `dagordning` and `namnrollista` there.
3. **Backward compatibility**: Existing monolithic templates must continue working. The new components should be usable both from YAML recipes and from traditional `.tex.jinja` templates via `\usepackage`.
4. **The `clauses` environment in `klartex-base.cls`**: This is used by both `protokoll` and `avtal` templates. Issue #9 extracts it to `klartex-klausuler.sty`. The dagordning component is different -- it uses paragraph-sign numbering, not clause numbering.
5. **Schema field naming**: The existing `agenda_items` schema uses English field names (`title`, `decision`, `discussion`). The LaTeX commands/environments can be Swedish, but JSON data fields stay English.

## Implementation Steps

### Phase 1: Create klartex-dagordning.sty

1. Create the component package file
   - File: `cls/klartex-dagordning.sty`
   - Provide `\usepackage{klartex-dagordning}` as the public API
   - Define a `dagordning` environment with paragraph-sign numbering
   - Each item gets automatic numbering with a paragraph sign prefix: `\S 1`, `\S 2`, etc.
   - Support optional `beslut` (decision) annotation per item
   - Support optional `discussion` text before the decision
   - LaTeX interface:
     ```latex
     \usepackage{klartex-dagordning}
     ...
     \begin{dagordning}
       \punkt{Motets oppnande}
       \punkt[Beslut: Dagordningen godkanns]{Godkannande av dagordning}
     \end{dagordning}
     ```
   - Implementation details:
     - New counter `dagordningcounter` (separate from `clausecounter`)
     - Use `enumitem` to define the list (already loaded by `klartex-base.cls`)
     - Paragraph sign + arabic number as label
     - Appropriate spacing for association documents

2. Create the metadata file
   - File: `cls/klartex-dagordning.meta.yaml`
   - Define inputs per #15 specification:
     ```yaml
     name: dagordning
     description: "Paragrafnumrerad dagordning for foreningsdokument"
     inputs:
       - name: punkter
         type: array
         required: true
         items:
           rubrik: string
           diskussion: string
           beslut: string
         description: "Dagordningspunkter med valfri diskussion och beslut"
     used_in:
       - kallelse
       - arsmotesprotokoll
       - styrelsemotesprotokoll
     ```

### Phase 2: Create klartex-namnrollista.sty

1. Create the component package file
   - File: `cls/klartex-namnrollista.sty`
   - Provide `\usepackage{klartex-namnrollista}` as the public API
   - Define a `namnrollista` environment producing a formatted table
   - Uses `tabularx` and `booktabs` (already required by `klartex-base.cls`)
   - Columns: Namn, Roll, Notering (optional, hidden if no rows have it)
   - LaTeX interface:
     ```latex
     \usepackage{klartex-namnrollista}
     ...
     \begin{namnrollista}
       \person{Anna Andersson}{Ordforande}{}
       \person{Erik Eriksson}{Ledamot}{omval 2 ar}
     \end{namnrollista}
     ```
   - Implementation details:
     - Use `tabularx` with `X` columns for flexible widths
     - `\toprule`/`\midrule`/`\bottomrule` for clean table borders
     - Header row with bold labels
     - The `\person` command adds a table row

2. Create the metadata file
   - File: `cls/klartex-namnrollista.meta.yaml`
   - Define inputs per #15 specification:
     ```yaml
     name: namnrollista
     description: "Formaterad tabell med namn, roll och valfri notering"
     inputs:
       - name: personer
         type: array
         required: true
         items:
           namn: string
           roll: string
           notering: string
         description: "Lista med namn, roll och valfri notering"
     used_in:
       - verksamhetsberattelse
       - valberedningens-forslag
       - arsmotesprotokoll
     ```

### Phase 3: Register Components in components.py

1. Update `klartex/components.py` (created by #9)
   - Add `dagordning` entry mapping to:
     - Package: `klartex-dagordning`
     - Environment: `dagordning`
     - Macro: `\punkt`
     - Data keys: `agenda_items` (maps `title` to rubrik, `decision` to beslut, `discussion` to diskussion)
   - Add `namnrollista` entry mapping to:
     - Package: `klartex-namnrollista`
     - Environment: `namnrollista`
     - Macro: `\person`
     - Data keys: `people` array with `name`, `role`, `note`

### Phase 4: Create Jinja2 Component Macros

1. Create reusable Jinja2 macros that bridge JSON data to the LaTeX components
   - File: `templates/_dagordning.jinja`
   - File: `templates/_namnrollista.jinja`
   - These macros iterate over the data arrays and emit the LaTeX commands

2. `_dagordning.jinja`:
   ```jinja
   \begin{dagordning}
   \BLOCK{for item in items}
   \punkt\BLOCK{if item.decision}[Beslut: \VAR{item.decision}]\BLOCK{endif}{\VAR{item.title}}
   \BLOCK{if item.discussion}
   \VAR{item.discussion}
   \BLOCK{endif}
   \BLOCK{endfor}
   \end{dagordning}
   ```

3. `_namnrollista.jinja`:
   ```jinja
   \begin{namnrollista}
   \BLOCK{for person in items}
   \person{\VAR{person.name}}{\VAR{person.role}}{\VAR{person.note | default('')}}
   \BLOCK{endfor}
   \end{namnrollista}
   ```

### Phase 5: Update Protokoll Template

1. Modify `templates/protokoll/protokoll.tex.jinja`
   - Add `\usepackage{klartex-dagordning}` in the preamble (after `\documentclass{klartex-base}`)
   - Replace the hardcoded `clauses` loop (lines 45-56) with an include of the dagordning macro
   - Map existing `data.agenda_items` fields to the dagordning interface
   - This preserves backward compatibility since the schema fields (`title`, `discussion`, `decision`) remain unchanged

2. The `templates/protokoll/schema.json` does not need changes -- the existing `agenda_items` schema already matches what dagordning needs (title, discussion, decision)

### Phase 6: Tests

1. Create test fixture for dagordning
   - File: `tests/fixtures/protokoll_dagordning.json`
   - Test data with multiple agenda items including decisions and discussions

2. Add unit tests for both components
   - File: `tests/test_components.py` (extend, created by #9)
   - Test dagordning component registration and LaTeX output
   - Test namnrollista component registration and LaTeX output
   - Test special character escaping in component inputs
   - Test empty/missing optional fields (no decision, no note)

3. Integration test
   - Verify protokoll template still renders with the new dagordning component
   - Verify existing `tests/fixtures/protokoll.json` fixture still passes
   - File: `tests/test_renderer.py` (add test case)

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `cls/klartex-dagordning.sty` | Create | Paragraph-numbered agenda list LaTeX component |
| `cls/klartex-dagordning.meta.yaml` | Create | Self-describing metadata for dagordning |
| `cls/klartex-namnrollista.sty` | Create | Name/role table LaTeX component |
| `cls/klartex-namnrollista.meta.yaml` | Create | Self-describing metadata for namnrollista |
| `klartex/components.py` | Modify | Register dagordning and namnrollista in component mapping |
| `templates/_dagordning.jinja` | Create | Jinja2 macro bridging JSON to dagordning LaTeX |
| `templates/_namnrollista.jinja` | Create | Jinja2 macro bridging JSON to namnrollista LaTeX |
| `templates/protokoll/protokoll.tex.jinja` | Modify | Use dagordning component instead of hardcoded clauses loop |
| `tests/test_components.py` | Modify | Add tests for dagordning and namnrollista |
| `tests/test_renderer.py` | Modify | Add integration test for protokoll with dagordning |
| `tests/fixtures/protokoll_dagordning.json` | Create | Test fixture with dagordning data |

## Codebase Areas

- `cls/` (LaTeX style files alongside klartex-base.cls)
- `templates/` (shared Jinja2 macros)
- `templates/protokoll/` (existing template update)
- `klartex/` (component registry update)
- `tests/` (test files and fixtures)

## Design Decisions

> Non-trivial choices made during planning. Feedback welcome; otherwise implementation proceeds with these.

### 1. Paragraph-sign numbering vs reusing clauses environment
**Options:** (A) Reuse existing `clauses` environment with modified numbering, (B) Create new `dagordning` environment from scratch
**Decision:** B -- Create new environment
**Rationale:** The dagordning uses paragraph-sign numbering which is semantically different from legal clause numbering. The `clauses` environment is used by the avtal template and has specific formatting (bold numbers, specific spacing). A dedicated dagordning environment allows proper association-document formatting without breaking avtal templates. Issue #9 also plans to extract `clauses` to its own `klartex-klausuler.sty`, keeping them separate.

### 2. Component file naming follows #9 convention
**Options:** (A) `cls/komponenter/dagordning.sty`, (B) `cls/klartex-dagordning.sty`
**Decision:** B -- `cls/klartex-dagordning.sty` with `klartex-` prefix
**Rationale:** The #9 plan establishes that `.sty` files live directly in `cls/` with a `klartex-` prefix (e.g., `klartex-signaturblock.sty`, `klartex-klausuler.sty`). Following the same convention ensures consistency and makes the renderer's `cls/` directory symlink work without additional configuration.

### 3. Jinja2 macros bridge JSON data to LaTeX
**Options:** (A) Pure LaTeX commands only, (B) Jinja2 macros that emit LaTeX commands
**Decision:** Both -- `.sty` defines LaTeX interface, Jinja2 macros bridge JSON data to it
**Rationale:** The `.sty` files provide the LaTeX environments and commands. The Jinja2 macros handle the iteration over JSON arrays and data mapping. This matches the existing pattern where templates use Jinja2 to loop over data and emit LaTeX. It also supports the YAML recipe engine from #9 which needs this bridge layer via the meta-template.

### 4. Schema field naming: keep English in JSON, Swedish in LaTeX
**Options:** (A) Keep English field names in JSON schema, (B) Use Swedish field names everywhere
**Decision:** A -- Keep English field names in JSON schema for consistency
**Rationale:** The existing protokoll schema uses English field names (`agenda_items`, `title`, `decision`). Changing them would break backward compatibility. The LaTeX commands and environment names are Swedish (as they are user-facing in the rendered document), but the data interface stays English for consistency across the project.

### 5. namnrollista as table vs list
**Options:** (A) `tabularx` table with headers, (B) Description list with custom formatting
**Decision:** A -- `tabularx` table
**Rationale:** The issue specifies "formaterad tabell" (formatted table). A table with columns for Namn, Roll, and Notering provides clear structure and aligns well with the formal style of association documents. `tabularx` and `booktabs` are already loaded by `klartex-base.cls`.

## Verification Checklist

- [ ] `klartex-dagordning.sty` renders paragraph-numbered agenda items correctly
- [ ] Dagordning supports optional beslut/decision per item
- [ ] Dagordning supports optional discussion text per item
- [ ] `klartex-namnrollista.sty` renders a formatted name/role/note table
- [ ] Namnrollista handles missing optional notering field gracefully
- [ ] Both components have `.meta.yaml` with correct schema per #15
- [ ] Both components are registered in `klartex/components.py`
- [ ] Protokoll template works with dagordning component (backward compatible)
- [ ] Existing `protokoll.json` test fixture still renders correctly
- [ ] Special characters (Swedish characters, &, %, etc.) are handled correctly via `tex_escape`
- [ ] Components are discoverable by the renderer (symlinked `cls/` directory)
- [ ] Components work both in YAML recipe mode (#9) and in traditional `.tex.jinja` templates
