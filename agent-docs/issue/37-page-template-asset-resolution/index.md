# Issue #37: Page template assets resolve relative to cwd instead of the template's directory

**Branch from:** main

## Summary

Round 2 (issue reopened after PR #38). Round 1 made plain-name assets (`\includegraphics{logo.pdf}`) resolve next to the template via `TEXINPUTS`, but explicitly relative names (`./logo.pdf`, `../shared.tex`) still fail — Kpathsea never searches `TEXINPUTS` for them, only xelatex's cwd (our private tempdir). Fix: `_compile_tex` runs xelatex with `cwd=<asset root>` (template dir, else caller cwd) plus `-output-directory=<tempdir>`, with `TEXINPUTS` reordered (tmpdir replaces `.`) so plain-name precedence is unchanged.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Medium |
| **Issue state** | Reopened, label `plan exists` |
| **Blockers** | None (PR #38 merged; unresolved review thread there defines this round's scope) |
| **Test dependency** | XeLaTeX (already required by CI) |
| **Behavior change** | xelatex invocation shape changes for every render (cwd + `-output-directory`); `asset_dir=None` gives `./…` caller-cwd semantics; invalid `asset_dir` now raises `ValueError`; explicitly relative paths have no cwd fallback when `asset_dir` is set |

## Plan Review

**Status:** Reviewed

**Reviewed:** 2026-07-25

**Feedback:** Codex (round 2) confirmed the cwd + `-output-directory` architecture and step order; applied its revisions: two-pass aux-discovery and invocation-shape tests, recursive byte-level no-artifacts guard for both template dir and caller cwd, `asset_dir` validation before the xelatex-presence check with "not a directory" semantics (missing path + plain file), an `\includegraphics{./logo.pdf}` CLI repro matching the issue's primitive, fully precise search-order documentation, and expanded behavior-change triage.

## Related Files

- [plan.md](plan.md) - Full implementation plan (round 2)
- [progress.md](progress.md) - Implementation progress log (round 1 completed; round 2 pending)
