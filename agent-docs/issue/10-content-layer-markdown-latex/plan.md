# Implementation Plan: Content-lager -- markdown to LaTeX-rendering

## Summary

Add a content layer that converts markdown-like text to LaTeX before Jinja2 rendering. This allows AI agents (and users) to write free-form text with headings, bold, bullet lists, and numbered lists in JSON data fields, without needing LaTeX knowledge or a dedicated component for every text pattern.

## Triage Info

> Decision-support metadata for this issue.

| Field | Value |
|-------|-------|
| **Blocked by** | #9 Composable architecture (OPEN) -- partial: core filter is independent, template integration may need coordination |
| **Blocks** | None |
| **Related issues** | #9 (YAML recipes with content fields), #11 (foreningskomponenter touches same templates) |
| **Scope** | 6 files across rendering pipeline, templates, and tests |
| **Risk** | Medium |
| **Complexity** | Medium |
| **Safe for junior** | Yes (well-scoped text transformation) |
| **Conflict risk** | Medium -- overlaps with #9 and #11 on `klartex/renderer.py`, `templates/protokoll/protokoll.tex.jinja`, `tests/test_renderer.py` |

### Triage Notes

Issue #10 explicitly states "Beror pa #9 (composable architecture -- content-falt i YAML-recept)." However, the markdown-to-LaTeX converter itself (Phases 1-2) can be implemented and tested independently -- it is a pure text transformation function with no dependency on #9. Template integration (Phase 4) touches files that #9 and #11 also modify, so coordination is needed if those are in progress. This plan focuses on the standalone converter first, then template updates.

## Analysis

### Current Architecture

The rendering pipeline is:
1. JSON data validated against `schema.json`
2. All string values LaTeX-escaped via `tex_escape.py` (`escape_data()`)
3. Jinja2 template renders `.tex` source using escaped data
4. `xelatex` compiles to PDF

Currently, text fields like `item.discussion` (protokoll), `clause.body` (avtal), and `data.preamble` (avtal) are rendered as plain LaTeX strings. Any formatting must be hard-coded in the Jinja2 template.

### Problem

Documents like verksamhetsberattelser, motioner, and revisionsberattelser need rich running text (headings, bullet lists, bold). Today, the only options are:
- One component per text pattern (doesn't scale)
- Raw LaTeX in data fields (requires LaTeX expertise)

### Solution: Markdown Content Filter

A new `content.py` module that converts a simple markdown subset to LaTeX. Applied selectively via a Jinja2 filter (`| content`) in templates. The filter runs **instead of** normal `tex_escape` for content fields, since it produces intentional LaTeX commands.

### Key Design Constraint: Escaping Contract

Content fields need different escaping than plain fields:
- **Plain fields:** all special chars escaped by `escape_data()`, rendered via `\VAR{data.field}`
- **Content fields:** raw (unescaped) text processed by the `content` filter which handles escaping internally

**Final contract:** The renderer passes both `data` (escaped) and `raw` (original unescaped) in the Jinja2 context. Templates use `\VAR{data.field}` for plain text and `\VAR{raw.field | content}` for rich text content fields. The `markdown_to_latex()` function receives raw text and calls `tex_escape()` internally on text segments before wrapping them in LaTeX commands.

## Implementation Steps

### Phase 1: Core Markdown-to-LaTeX Converter

1. Create `klartex/content.py` with the conversion function
   - File: `klartex/content.py`
   - Implement `markdown_to_latex(text: str) -> str`
   - Input: raw (unescaped) markdown text
   - Output: LaTeX source with text segments properly escaped
   - Supported syntax:
     - `## Heading` -> `\subsection{Heading}`
     - `### Heading` -> `\subsubsection{Heading}`
     - Blank line -> paragraph break (LaTeX handles via parskip package already loaded in cls)
     - `**bold text**` -> `\textbf{bold text}`
     - `*italic text*` -> `\textit{italic text}`
     - `- item` / `* item` -> `\begin{itemize}\item ...\end{itemize}`
     - `1. item` -> `\begin{enumerate}\item ...\end{enumerate}`
   - Handle nested inline content: bold inside list items, etc.
   - Escape special LaTeX chars in text portions via `tex_escape()`

2. Implementation approach for the parser:
   - Process line-by-line for block-level elements (headings, lists, paragraphs)
   - Apply inline transformations (bold, italic) within each line after escaping text segments
   - Track state for consecutive list items to group them in `\begin{itemize}...\end{itemize}` or `\begin{enumerate}...\end{enumerate}`
   - Close current list environment when transitioning between list types, on blank lines, or on headings
   - Do NOT use a third-party markdown library -- keep it minimal and focused

3. Edge cases to handle explicitly:
   - Unmatched `*` or `**` markers: treat as literal text (escaped)
   - Switching between `itemize` and `enumerate`: close previous environment, open new one
   - List termination: blank line or heading ends current list
   - Leading/trailing whitespace: strip from lines before processing
   - Consecutive blank lines: collapse to single paragraph break
   - Literal `*` that is not markdown: context-sensitive (e.g., `2 * 3` should not italicize)
   - Empty input or whitespace-only input: return empty string

### Phase 2: Escaping Integration and Renderer Changes

1. Update `klartex/renderer.py`
   - File: `klartex/renderer.py`
   - Add `from klartex.content import markdown_to_latex`
   - Register Jinja2 filter: `_jinja_env.filters['content'] = markdown_to_latex`
   - Pass raw data alongside escaped data in the Jinja2 context:
     ```python
     context = {
         "data": escaped_data,
         "raw": data,  # original unescaped data for | content filter
         "brand": brand,
     }
     ```
   - No changes to `escape_data()` -- it continues to escape all fields as before

### Phase 3: Tests

1. Create `tests/test_content.py`
   - File: `tests/test_content.py`
   - Test heading conversion (`##` -> `\subsection{}`, `###` -> `\subsubsection{}`)
   - Test paragraph handling (blank lines between paragraphs)
   - Test bold (`**text**` -> `\textbf{text}`)
   - Test italic (`*text*` -> `\textit{text}`)
   - Test unordered lists (`-` and `*` markers)
   - Test ordered lists (`1.`, `2.`)
   - Test mixed content (heading + paragraph + list)
   - Test LaTeX special char escaping within content (`$`, `%`, `&`, `#`, `_`)
   - Test that plain text without markdown passes through with only escaping
   - Test nested inline formatting in list items (`- **bold item**`)
   - Test edge cases:
     - Unmatched `**` and `*` markers (should remain as escaped literal text)
     - Switching between `itemize` and `enumerate` mid-content
     - List terminated by blank line and by heading
     - Consecutive blank lines collapsed
     - Leading/trailing whitespace stripped
     - Empty and whitespace-only input
     - Literal asterisk in non-markdown context (e.g., `2 * 3`)

2. Update `tests/test_renderer.py`
   - Add integration test rendering a protokoll with markdown in discussion fields
   - Verify PDF generation succeeds with content-formatted fields
   - **Add .tex source assertion:** intercept the rendered `.tex` before xelatex compilation and verify it contains expected LaTeX commands (`\subsection{}`, `\textbf{}`, `\begin{itemize}`) from markdown input

### Phase 4: Update Existing Templates

1. Update `templates/protokoll/protokoll.tex.jinja`
   - Change `\VAR{item.discussion}` to `\VAR{raw.agenda_items[loop.index0].discussion | content}` (or use a simpler loop variable approach -- see note below)
   - Change `\VAR{item.decision}` to `\VAR{raw.agenda_items[loop.index0].decision | content}`
   - **Note on loop access:** The current template iterates `\BLOCK{for item in data.agenda_items}`. To access raw data inside the loop, either:
     - (A) Change the loop to iterate over zipped data: use a custom Jinja2 filter or zip raw+escaped
     - (B) Simplest: change the loop to iterate over `raw.agenda_items` and apply `| content` for rich fields, `| tex_escape` for plain fields
     - **Decision: (B)** -- Loop over `raw.agenda_items`, use `| content` for discussion/decision, use a `tex_escape` filter for plain fields like `item.title`
   - This requires also registering `tex_escape` as a Jinja2 filter in `renderer.py`

2. Update `templates/avtal/avtal.tex.jinja`
   - Change `\VAR{clause.body}` to `\VAR{raw_clause.body | content}` (loop over `raw.clauses`)
   - Change `\VAR{data.preamble}` to `\VAR{raw.preamble | content}`
   - **Subclauses:** Keep `\VAR{sub}` as plain escaped text (inline-only context inside `\item`). Subclauses are short clause items, not rich content blocks. Applying `| content` inside an existing `\item` would produce nested list environments which is fragile.

## Files Summary

| File | Action | Purpose |
|------|--------|---------|
| `klartex/content.py` | Create | Markdown-to-LaTeX converter function |
| `klartex/renderer.py` | Modify | Register `content` and `tex_escape` filters, pass `raw` data to context |
| `templates/protokoll/protokoll.tex.jinja` | Modify | Use `| content` filter on discussion/decision fields via `raw` data |
| `templates/avtal/avtal.tex.jinja` | Modify | Use `| content` filter on body/preamble fields via `raw` data |
| `tests/test_content.py` | Create | Unit tests for markdown-to-LaTeX conversion |
| `tests/test_renderer.py` | Modify | Integration tests with markdown content and .tex source assertions |

## Codebase Areas

- `klartex/` (new content module, renderer modification)
- `templates/protokoll/` (template update)
- `templates/avtal/` (template update)
- `tests/` (new and updated tests)

## Design Decisions

> Non-trivial choices made during planning. Feedback welcome; otherwise implementation proceeds with these.

### 1. Custom minimal parser vs third-party markdown library
**Options:** (A) Use a library like `mistune` or `markdown-it-py` vs (B) Write a minimal line-by-line parser
**Decision:** B -- Minimal custom parser
**Rationale:** The issue explicitly says "Behover inte vara full markdown -- bara de vanligaste konstruktionerna." A custom parser for ~6 constructs is simpler, has zero dependencies, and avoids pulling in a full markdown AST. The supported subset (headings, bold, italic, bullet/numbered lists, paragraphs) can be handled with straightforward line-by-line processing and regex for inline elements.

### 2. Escaping strategy for content fields
**Options:** (A) Pre-escape all data then reverse-escape in content filter vs (B) Pass both escaped and raw data to templates vs (C) Schema-annotated selective escaping
**Decision:** B -- Dual data context (`data` + `raw`)
**Rationale:** Passing `raw` alongside `data` in the Jinja2 context is the least invasive change. Templates explicitly choose `data.field` (escaped) for plain text or `raw.field | content` for rich text. No changes to `escape_data()` needed. The content filter handles its own escaping internally. Template authors must use `raw` for content fields -- this is a clear, documented convention.

### 3. Jinja2 filter vs pre-processing step
**Options:** (A) Jinja2 filter `| content` applied in templates vs (B) Pre-process content fields before Jinja2 rendering
**Decision:** A -- Jinja2 filter
**Rationale:** A filter gives template authors explicit control over which fields get markdown processing. It's visible in the template where conversion happens. Pre-processing would require schema annotations and a more complex pipeline. The filter approach also works naturally when issue #9 introduces YAML recipes -- the filter is template-level, independent of the data source.

### 4. Backward compatibility
**Options:** (A) Auto-apply content filter to all text fields vs (B) Opt-in per field via `| content` filter
**Decision:** B -- Opt-in
**Rationale:** Existing templates continue to work unchanged. Fields without `| content` behave exactly as before (plain escaped text). This ensures zero breaking changes. Templates are updated incrementally to use the content filter where rich text is desired.

### 5. Subclauses: content vs plain text
**Options:** (A) Apply `| content` to subclause items vs (B) Keep subclauses as plain escaped text
**Decision:** B -- Plain escaped text for subclauses
**Rationale:** Subclauses in `avtal.tex.jinja` are rendered inside `\item` in a `subclauses` list environment. Applying the content filter here could produce nested list environments (list within list item), which is fragile and likely not the intended use case. Subclauses are short, single-line clause items, not rich content blocks.

## Verification Checklist

- [ ] `markdown_to_latex("## Rubrik")` produces `\subsection{Rubrik}` (with Rubrik escaped)
- [ ] `markdown_to_latex("**bold**")` produces `\textbf{bold}`
- [ ] Unordered lists (`- item`) produce `\begin{itemize}\item ...\end{itemize}`
- [ ] Ordered lists (`1. item`) produce `\begin{enumerate}\item ...\end{enumerate}`
- [ ] Paragraphs (blank-line separated) render correctly
- [ ] LaTeX special characters in content are escaped (`$`, `%`, `&`, etc.)
- [ ] Plain text without markdown syntax passes through with only escaping
- [ ] Unmatched `*`/`**` treated as literal (escaped) text
- [ ] List type transitions close previous environment correctly
- [ ] Consecutive blank lines collapsed to single paragraph break
- [ ] Existing templates render identically when `| content` is not used
- [ ] Protokoll with markdown in discussion fields renders to valid PDF
- [ ] Rendered `.tex` source contains expected LaTeX commands from markdown input
- [ ] Avtal with markdown in clause body renders to valid PDF
- [ ] No new dependencies added to `pyproject.toml`
