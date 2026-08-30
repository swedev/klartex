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
- Pre-existing defect, out of scope here: the `letterhead` fragment emits `\\` before `\orgemail` / `\orgphone` unconditionally, so a header with `org_name` set but `web` empty and `email` set fails to compile ("There's no line here to end"). Reproducible on `main` with the documented custom-template idiom. Fixing it changes the fragment and would break the alias goldens, so it belongs with #64 (header presentation).
