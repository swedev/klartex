# Issue #6: Homebrew Formula

**Based on:** main

## Summary

Create a Homebrew formula so klartex can be installed via `brew install klartex`. The formula will live in a custom tap (`swedev/homebrew-tap`) and install klartex from PyPI into a Homebrew-managed virtualenv. xelatex is documented as a runtime requirement via caveats since Homebrew formulas cannot depend on casks.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | No (blocked by #2 Publish to PyPI) |
| **Risk** | Low |
| **Safe for junior** | Yes |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-02-17
**Feedback:** Fixed scope/conflict accuracy, reordered phases so resource generation precedes formula finalization, strengthened formula test block to catch packaging issues, added external dependencies to triage.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress (if exists)

## Related Issues

- #2 Publish to PyPI - Blocker; formula needs a published PyPI package
- #4 Docker image - Alternative distribution channel
