# Progress: Issue #63 — Composable page templates: separate header and footer slots

## Status: Completed

**Completed:** 2026-08-30

(Update as work proceeds — newest entries first)

- **Phase 6** — README.md / README.en.md "Sidmallar" / "Page Templates" rewritten around the two slots; `CLAUDE.md` page-template section updated. CHANGELOG entry drafted for the PR body (written at release time per the repo's release flow).
- **Phase 5** — `--header-template` / `--footer-template`, mutual exclusion with `--page-template`, shared-directory rule, auto-detection suppressed when a slot flag is given.
- **Phase 4** — tex-level, recipe-path and pdftotext behaviour locks; `block_kallelse.json` on the slot form.
- **Phase 3** — eight schemas carry the slot definitions, goldens locked, example payload on the slot form.
- **Phase 2** — contract macros in `klartex-base.cls`, `_page_template.tex.jinja` composition, context/renderer plumbing.
- **Phase 1** — model, fragments, alias resolution.
- **Phase 0** — preamble goldens captured from `main` into `tests/fixtures/golden/`.

## Verification

- `pytest -n auto` — 472 passed, 0 skipped.
- Alias preamble goldens captured from `main` reproduce for `formal`, `clean`, `none` and the faktura recipe.
- Composed alias source diffed against `main:klartex/page_templates/<alias>.tex.jinja`: the only differences are the `\makeatother`/`\makeatletter` fragment boundary and the reclaim block moving after the footer.
- Manual: `klartex -d tests/fixtures/block_kallelse.json` renders the letterhead org details in the header and `Kallelse till årsmöte • Sida 1 av 1` in the footer; the same data with `--footer-template` keeps the header and replaces only the footer.
- `python -m build --wheel` ships `page_templates/header/*.tex.jinja`, `page_templates/footer/standard.tex.jinja` and `templates/_page_template.tex.jinja`.

## Open items for the PR body

- Agent-judgment design calls D1–D10 from the plan (slot JSON shape, footer fields directly on the footer slot, the header field names `org_name` / `address` / `web` / `email` / `phone` / `logo`, sources as kwargs/flags, document-level settings applying alongside a custom source).
- Review round 1 (PR #77) fixed three findings: the `letterhead` contact column now stacks lines with `\kx@hdrline` so an empty leading field no longer breaks the compile; the `letterhead` object form requires `org_name` so contact details cannot be silently dropped; and the `logo` filename carries a `pattern` so LaTeX-special characters fail validation instead of xelatex.
