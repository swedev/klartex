# Issue #63: Composable page templates: separate header and footer slots

**Branch from:** main

## Summary

Restructures the page-template surface around two independent slots, header and footer. Each slot is either a predefined variant or custom `.tex.jinja` source, and structured settings keep applying to whichever slot stays predefined — today a custom source (`page_template_source`) switches off every structured override at once. The monolithic built-ins dissolve: `formal` / `clean` / `none` become the header variants `letterhead` / `logo` / empty (names per #64), and today's page-number footer (with `\kxfooter` when fields are given) becomes the footer variant `standard`; the old names stay as aliases so every existing payload renders unchanged. Concretely: `klartex/page_templates/` is split into `header/` and `footer/` fragments, the `\providecommand` contract for org fields and logo moves into `klartex-base.cls`, a single composition include (`_page_template.tex.jinja`) replaces `\VAR{page_template_source}` + `_page_template_overrides.tex.jinja` in both meta-templates with a defined order (document-level settings → header → footer → header-space reclaim → first-page style), `render()` and the CLI gain per-slot custom source (`header_source` / `footer_source`, `--header-template` / `--footer-template`), and the header variants get structured org fields and logo so a predefined header can carry content without any LaTeX. Eight schemas, the example payload, both READMEs and the tex-level / text-layer test suites are updated; a fixture takes the slot form. `page_numbers`, `first_page_header`, the `\kxfooter` layout, margins and typography are left to #67, #66, #62, #65 and #61.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | High |

Issue is open, unlabeled and unassigned, with no comments and no `agent-docs/github/project.json` (no board fields). No blockers: it references only #64, which is open but explicitly defers to whichever of #63/#64 lands first ("If #63 lands first, do this as part of its variant naming"), so this plan adopts #64's names `letterhead` / `logo` and leaves descriptions and presentation to #64. Related open issues that reference #63 and share these files: #64 (naming), #65 (margins), #67 (page numbers per slot), plus #61, #62, #66 from the same template-editor design session — all scoped out here. Sequencing: #63 lands first; #66 and #67 then edit `first_page_header` / `page_numbers` in the slot model this plan creates (`page_numbers` is reserved on the footer slot and rejected until #67 defines its tri-state). No other open plan touches `klartex/page_templates*`, `_page_template_overrides.tex.jinja`, the meta-template preambles or `klartex-base.cls`. Risk is High by breadth rather than depth: the change touches public JSON schemas (eight files), the Python API (`render()` kwargs, `PageTemplate` shape), the CLI, the packaged `.tex.jinja` assets and the custom-source contract, while promising unchanged chrome for every alias; the plan locks the alias output with preamble goldens captured from `main` before any change (step 0/14), plus tex-level and pdftotext assertions, and keeps the monolithic `page_template_source` mode's tolerance for missing/unknown `data.page_template` on the block path (recipe schemas already reject unknown names by `enum` and keep doing so). Ten design calls are agent judgment (D1–D10 in the plan), flagged for the PR body — chiefly the slot JSON shape, footer fields living directly on the footer slot, structured org fields on the header variants and their names (`org_name`, `address`, `web`, `email`, `phone`, `logo` — this plan's call, not #64's), custom sources travelling as kwargs/flags rather than inline JSON, and document-level settings applying alongside custom sources (one small behaviour change for payloads that combined a monolithic source with `font`/`diff_style`). Consumer `swedev/klartex.se` keeps working unchanged through the aliases and `page_template_source`; its slot-aware follow-up is a separate issue there, not filed without the user. Test dependencies (xelatex, pdftotext) are already required locally and in CI.

## Plan Review

**Status:** Reviewed

**Reviewed:** 2026-08-30

**Feedback:** Two codex passes. First pass: alias-equivalence broke on `none`'s `first_page_header` default (fixed by deriving non-slot defaults from the resolved slots, D10), the monolithic `page_template_source` path must keep tolerating unknown/missing `data.page_template` (now an explicit loader path, block-engine scope), a circular import via `renderer.py` (new dependency-free `klartex/jinja_env.py`), an inconsistent slot contract (header requires `variant`, footer may omit it; `web` chosen; `fields`/`has_fields` defined; `page_numbers` reserved in the loader only), phase order (schemas now precede render-level tests and the fixture; `body` needs a heading; test helpers gain source kwargs), and compatibility proven by preamble goldens captured from `main` rather than alias-vs-slot equivalence. Second pass: the first-page guard must also cover the empty header so `none` keeps emitting `\thispagestyle{plain}`, the tolerance claim narrowed to the block path (recipe schemas enum the name), and explicit slot flags suppress the CLI's monolithic auto-detection; line/count references corrected.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress log
