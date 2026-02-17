# Issue #2: Publish to PyPI

**Based on:** main

## Summary

Set up automated PyPI publishing for klartex using GitHub Actions and trusted publishing (OIDC). The workflow triggers on version tag pushes, runs tests, builds with hatchling, and publishes to PyPI -- enabling `pip install klartex`.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Low |
| **Safe for junior** | Yes |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-02-17
**Feedback:** Added safe `__version__` fallback for source checkouts, explicit dep install steps in workflow, `twine check` validation, `environment: pypi` requirement, TestPyPI dry-run step, and clarified that CI tests are non-render only.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress (if exists)

## Related Issues

- #3 GitHub Actions CI - Complementary CI workflow; not a blocker but natural companion
