# Issue #3: GitHub Actions CI

**Based on:** main

## Summary

Set up a GitHub Actions CI workflow that runs the full test suite (including PDF render tests) on push to main and pull requests. Uses an Ubuntu runner with `setup-python` for Python 3.13 and apt-installed TeX Live for xelatex. Includes explicit verification that no render tests are skipped.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Low-Medium |
| **Safe for junior** | Yes |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-02-17
**Feedback:** Fixed internal inconsistency between lint+test jobs and single-job decision. Switched from Docker container to Ubuntu runner strategy to resolve Python 3.13 compatibility. Added explicit xelatex skip verification, workflow scaffolding details (checkout, setup-python, concurrency), and external dependencies to triage.

## Related Files

- [plan.md](plan.md) - Full implementation plan
- [progress.md](progress.md) - Implementation progress (if exists)

## Related Issues

- #2 Publish to PyPI - Complementary workflow; its publish.yml includes a lightweight test step without xelatex
