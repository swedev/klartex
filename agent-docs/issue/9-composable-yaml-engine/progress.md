# Implementation Progress: Issue #9

**Started:** 2026-02-18
**Last updated:** 2026-02-18
**Status:** Completed

## Completed Steps

- [x] Phase 1, Step 1: Create `cls/klartex-signaturblock.sty`
- [x] Phase 1, Step 2: Create `cls/klartex-klausuler.sty`
- [x] Phase 1, Step 3: Create `cls/klartex-titelsida.sty`
- [x] Phase 1, Step 4: Update `klartex-base.cls` to load .sty files via RequirePackage
- [x] Phase 1, Step 5: Verify all existing templates still compile correctly
- [x] Phase 2, Step 1: Create `schemas/recipe.schema.json`
- [x] Phase 2, Step 2: Create sample recipe for protokoll (`templates/protokoll/recipe.yaml`)
- [x] Phase 3, Step 1: Create `klartex/recipe.py` (recipe loader and orchestration)
- [x] Phase 3, Step 2: Create `klartex/components.py` (component-to-LaTeX mapping)
- [x] Phase 3, Step 3: Create `templates/_recipe_base.tex.jinja` (meta-template)
- [x] Phase 4, Step 1: Update `klartex/registry.py` (recipe.yaml discovery)
- [x] Phase 4, Step 2: Update `klartex/renderer.py` (dual-path rendering with engine selection)
- [x] Phase 4, Step 3: Update temp directory setup (TEXINPUTS for .sty files)
- [x] Phase 4, Step 4: Expose engine parameter in CLI (`klartex/cli.py`) and API (`klartex/main.py`)
- [x] Phase 5, Step 1: Unit tests for recipe loading and validation (`tests/test_recipe.py`)
- [x] Phase 5, Step 2: Unit tests for component registry (`tests/test_components.py`)
- [x] Phase 5, Step 3: Integration test: recipe-based protokoll renders valid PDF
- [x] Phase 5, Step 4: Discovery and precedence tests (in `tests/test_renderer.py`)
- [x] Phase 5, Step 5: Escaping/safety tests for recipe rendering
- [x] Phase 5, Step 6: API/CLI engine selection tests (in `tests/test_api.py`)
- [x] Phase 5, Step 7: All 63 tests pass (was 22, now 63)
- [x] Phase 6, Step 1: Update README.md with composable architecture overview
- [x] Phase 6, Step 2: Update README.en.md with English version

## Notes

- .sty files use `\providecommand` to avoid conflicts when loaded via klartex-base.cls which defines language strings first via `\newcommand`
- TEXINPUTS environment variable is set during xelatex compilation to include the cls/ directory so RequirePackage can find .sty files
- The cls/ directory is also symlinked into the temp dir for redundancy
- PDF byte-size comparisons between separate renders are unreliable (timestamps/IDs differ), so the auto-vs-legacy precedence test was revised to use _select_engine helper instead
