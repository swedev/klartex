# Plan: Issue #49 — A paragraph longer than a page does not break — it spills past the bottom margin

## Goal

A single paragraph longer than one page must flow onto the next page like any other text, instead of silently running past the bottom margin and losing content. The widow/orphan protection introduced in v0.6.0 (no 1- or 2-line widows/orphans) must be preserved — only the unintended "no break anywhere in the paragraph" side effect goes away. The class is shared by both surfaces, so the fix applies to block-engine and recipe renders alike.

## Approach

**Root cause (confirmed empirically).** `klartex/cls/klartex-base.cls` lines 61–62 set the eTeX penalty arrays

```tex
\widowpenalties 2 10000 10000
\clubpenalties 2 10000 10000
```

intending "forbid 1- and 2-line widows and orphans" (comment on lines 58–60, CHANGELOG v0.6.0 typography entry). But eTeX's penalty arrays clamp the line index to the array length — the *last* value applies to **every** subsequent line (in `post_line_break`: `if r > n then r := n`). So `2 10000 10000` puts an infinite penalty at *every* interline break point of *every* paragraph, making paragraphs categorically unbreakable across pages. When a paragraph exceeds the page, xelatex emits `Overfull \vbox (…pt too high) has occurred while \output is active` and the text is clipped at the bottom margin — no error, compile succeeds, content silently lost. This landed in commit `fbbfc79` ("Block engine: list-item content blocks, widow + heading-orphan protection") and matches the issue's observation that the behaviour has nothing to do with change marking.

**Fix.** Append an explicit terminating `0` so the repetition stops after line 2:

```tex
\widowpenalties 3 10000 10000 0
\clubpenalties 3 10000 10000 0
```

Semantics after the fix: a break leaving 1 or 2 lines at the start (`\clubpenalties`) or end (`\widowpenalties`) of a paragraph still gets penalty 10000 (forbidden); every break point deeper than 2 lines from either edge gets 0 and breaks freely. This is exactly the protection the comment describes.

**Verification already performed during planning** (scratchpad only, working tree untouched):

- Minimal `article` probe with the buggy arrays: `Overfull \vbox (564.0pt too high)`, a full page of text clipped. Same probe with `3 10000 10000 0`: clean break, no overfull box.
- Real pipeline: `render('_block', {"body": [{"type": "text", "text": <~2 pages of lorem>}]})` → only 739 of 1140 words survive in the `pdftotext` text layer (the rest is drawn below the page and clipped).
- Patched copy of the actual `klartex-base.cls` (only the two lines changed) compiling the same paragraph plus a trailing marker word: 2 pages, 0 overfull boxes, all 1141 words including the marker present in the text layer.

**Residual, by design:** a paragraph of ≤ 4 lines is still unbreakable (the 2-line club and 2-line widow zones overlap), so a 4-line paragraph near the bottom moves to the next page as a whole. That is the intended consequence of the 2+2 policy, not a defect.

**Scope check:** `\widowpenalties`/`\clubpenalties` appear nowhere else in `klartex/cls/` or the templates; no `\interlinepenalties`/`\interlinepenalty` overrides exist. The fix is those two lines plus a comment touch-up.

## Steps

Red first, then green:

1. **Add the regression test** in `tests/test_pdf_text_layer.py` (it already has the render → `pdftotext` round-trip machinery and the `requires_tools` skip guard). Refactor the existing `_text_layer` helper into a raw variant plus the current whitespace-normalized one (`_raw_text_layer()` returning the untouched `pdftotext` output; `_text_layer()` normalizing it), since the normalized form collapses the `\f` page separators. The test renders a `_block` document whose single `text` block is a fixed, generously long payload (e.g. a lorem sentence repeated 60×, comfortably over 2 pages at `\setstretch{1.3}`) ending in a unique marker word (e.g. `SLUTMARKÖR`), then:
   - splits the raw output on `\f`, discards the trailing empty segment, and asserts at least 2 pages, and
   - asserts the marker word appears on the *final* non-empty page — the decisive assertion: on current `main` the buggy render still reports 2 pages, but the marker is clipped away.
2. **Add a preservation test** so the fix cannot regress to "arrays removed entirely" (which would also let long paragraphs break, but drop the widow/orphan policy): render a `_block` document with a raw `latex` block whose source prints the array values into the page — `\the\widowpenalties 1`, `\the\widowpenalties 3`, `\the\clubpenalties 1`, `\the\clubpenalties 3` — and assert the text layer shows `10000` for positions 1–2 and `0` for position 3 for both arrays. (Probe verified with xelatex during planning: `W1=10000. W3=0. C1=10000. C3=0.` comes back through `pdftotext`.)
3. **Run the new tests against the unchanged class** and confirm the regression test fails red (marker missing from the last page) and the preservation test fails on position 3 (currently `10000`, the repeated last value).
4. **Apply the fix**: in `klartex/cls/klartex-base.cls` (lines 58–62), change the two arrays to `\widowpenalties 3 10000 10000 0` and `\clubpenalties 3 10000 10000 0`. Extend the comment to note *why* the terminating `0` is required (the last array value repeats for all remaining lines, so without it every interline break is forbidden) — this is a technical constraint comment, the kind that prevents the bug from being "simplified" back in.
5. **Re-run the focused tests** (green), then the full suite (`pytest`) — no existing test asserts page geometry or break positions, but multi-page fixture renders (`block_arsredovisning`, `avtal`, …) must still compile.
6. At release time, add a CHANGELOG entry under `Fixes` (in Swedish, per convention) describing that paragraphs longer than a page now break instead of spilling past the bottom margin, and that 1–2-line widow/orphan protection is unchanged.

## Risks

- **Layout shifts in existing documents.** Pages that previously carried an unbreakable paragraph (forcing early breaks or overfull spill) will now break mid-paragraph. This is the corrected behaviour — anything that changes was wrong before — but pixel-tuned documents may re-flow. Low risk; no test asserts exact break positions.
- **Interaction with the block engine's `\kxneedspace`/`\nopagebreak` machinery.** Those operate on the vertical list *between* blocks and are untouched; the fix only re-enables break points *inside* paragraphs. The CHANGELOG's documented spacing rationale (v0.9.2–v0.9.4 orphan fixes) concerns block-boundary breaks and is unaffected.
- **Fixture output drift** in the PDF text-layer round-trip battery: none expected — those fixtures' paragraphs are short and their break points unchanged.

## Test Plan

- New: `tests/test_pdf_text_layer.py::test_paragraph_longer_than_a_page_breaks_onto_next_page` (name indicative) — asserts the trailing marker word of a >1-page paragraph appears on the final page of the text layer and the PDF has at least 2 pages. Red before the fix, green after.
- New: a preservation test in the same file asserting `\the\widowpenalties`/`\the\clubpenalties` positions 1–2 are `10000` and position 3 is `0`, so the widow/orphan policy cannot silently disappear.
- Full `pytest` run (xelatex + pdftotext available locally) — all existing compilation and round-trip tests stay green.
- Manual sanity: render `tests/fixtures/block_kallelse.json` and one multi-page fixture via the CLI and eyeball that block-boundary spacing (headings, clauses) looks unchanged.
