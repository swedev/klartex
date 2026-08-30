# Progress: Issue #81 — Publish klartex-render:X.Y.Z at each release — a klartex serve compile endpoint

## Status: Completed (2026-08-30)

(Update as work proceeds — newest entries first)

- [x] 9. PR body — D1–D7 flagged as agent judgment, #76 coordination note, release-day reminder to make the ghcr package public
- [x] 8. Docs — `README.md` and `README.en.md` get parallel `klartex serve` + image sections; `CLAUDE.md` gains an "HTTP surface" architecture subsection, the `test_server.py` test-file line and a serve command
- [x] 7. `publish.yml` — build job resolves and validates the version (wheel vs `pyproject.toml` vs release tag) and exposes it as an output; new `image` job with the D4 guards (release-tag identity, base-pin equality, wheel presence, login-before-inspect tag absence), per-version concurrency, free-disk, multi-arch build+push, digest to the step summary. `actionlint` clean.
- [x] 6. `docker/Dockerfile.render` + `.dockerignore` — pinned base, wheel-only COPY, `--only-binary=:all:`, non-root with a real HOME, urllib HEALTHCHECK, `CMD klartex serve --host 0.0.0.0`
- [x] 5. CI — `ci.yml`, `publish.yml` and `base-image.yml` install `.[dev,serve]` and their skip guard covers `test_server` as well as `xelatex` (D5)
- [x] 4. `tests/test_server.py` — moved suite adapted to the slot API, plus env-config, D7 envelope-mapping, footer-slot and CLI tests. 57 tests; whole file `importorskip`s away without the extra
- [x] 3. `klartex/cli.py` — `serve` subcommand, lazy import, narrow missing-extra error, `--host`/`--port`, `workers=1`
- [x] 2. `klartex/server/` — `__init__.py`, `app.py`, `render.py`; slot API, env config (D2), core-version `/health` (D3), D7 error handlers
- [x] 1. `pyproject.toml` — `serve` extra (`fastapi`, `uvicorn[standard]`) and `httpx` in `dev`

## Verification

- `pytest -n auto` with `.[dev,serve]` and xelatex on PATH: 525 passed, 0 skipped.
- A venv with `.[dev]` only: `tests/test_server.py` skips as one file, its reason line contains `test_server.py`, so the CI guard catches it. `klartex serve` in that venv prints the install hint and exits 1.
- `klartex serve` locally: `/health` returns the core version, `/render` returns a real PDF.
- `actionlint` clean on all three workflows; the pin-equality and version-resolution shell logic run correctly against the real files.
- `docker build -f docker/Dockerfile.render` against the pinned base on arm64: `--only-binary=:all:` resolved every `uvicorn[standard]` dependency. The container run with `--read-only --tmpfs /tmp --tmpfs /home/render` reports uid 1001, reaches `healthy` on the HEALTHCHECK, renders both a plain document and an inline bundle with an asset, and answers the documented `400` shapes.

## Not verified here

- The `image` job's refusal paths (existing registry tag, tag/version mismatch, diverged base pin) and the multi-arch push. They need a pushed branch and a `workflow_dispatch`, or a real release.

## Deviations from the plan

- The env-config helper lives in `render.py` (as `env_positive_int`) and is imported by `app.py`, rather than in a module of its own: D1 fixes the package at three modules, and `app.py` importing `render.py` is the direction that already exists.
- `klartex/server/__init__.py` is docstring-only per D1. An `app` re-export there shadows the `klartex.server.app` submodule, which broke a test's import of the module.
- `serve` also maps the config helper's `ValueError` to the CLI's `Error: …` style rather than letting a traceback out.
