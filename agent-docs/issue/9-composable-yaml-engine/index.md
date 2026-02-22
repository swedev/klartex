# Issue #9: Composable Architecture — YAML-recept-engine + .sty-komponenter

**Based on:** main

## Summary

This issue transforms Klartex from monolithic `.tex.jinja` templates to a composable architecture. LaTeX building blocks (signature blocks, clauses, title pages) are extracted into reusable `.sty` packages. A new YAML "recipe" format allows templates to be defined declaratively by combining components, instead of writing full LaTeX/Jinja files. The renderer is extended with a dual-path approach: existing monolithic templates continue to work, while new templates can use the recipe engine.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Medium |
| **Safe for junior** | No |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-02-18
**Feedback:** Codex review applied. Key changes: (1) Fixed render-path contradiction — added explicit engine selection contract (auto/legacy/recipe) exposed in render(), CLI, API. (2) Committed to Jinja meta-template as sole LaTeX generation path, removed Python string-building ambiguity. (3) Added escaping/safety contract for recipe rendering with injection tests. (4) Fixed triage — explicit blocked issues (#10, #11, #12, #13, #14) instead of vague "all". (5) Corrected cls/ symlink factual error. (6) Added discovery/precedence and engine selection tests. (7) Clarified schema convention (template data vs recipe format). (8) Added README.en.md to docs. (9) Updated scope to ~15 files.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress (if exists)

## Related Issues

- #10 - Content-lager — markdown to LaTeX-rendering (sibling concern, not a blocker)
