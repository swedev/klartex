# Issue #19: Agent-friendly CLI: full block schema, example command, blocks listing

**Branch from:** main

## Summary

Make the klartex CLI self-describing enough that an agent can go from `klartex schema _block` to valid JSON without reading source code. Three changes: discriminated-union schema, `example` subcommand, `blocks` listing.

## Triage Status

| Field | Value |
|-------|-------|
| **Ready to work** | Yes |
| **Risk** | Low |

## Plan Review

**Status:** Reviewed
**Reviewed:** 2026-03-29
**Feedback:** Plan is straightforward — all data exists, just needs wiring. No blockers.

## Related Files

- [plan.md](plan.md) - Implementation plan
- [research.md](research.md) - Research findings
