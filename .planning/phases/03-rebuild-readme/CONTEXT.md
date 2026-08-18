# Phase 03 — Rebuild README · Context

## Locked
- **D-18 — Phase 03 MAY write new prose, for exactly two sections.** `## Quick start` and `## Configuration` have no source to move: phase 02 carved the configuration prose to `docs/providers.md`, and a first-run walkthrough never existed. Both are written fresh and kept **minimal**, each linking out for depth. The project's "restructure, not a rewrite — moved sentences move intact" assumption governed phase 02's *move*; it cannot govern sections that have no source. REQUIREMENTS.md's assumption now records this carve-out explicitly so phase 04's REQ-06 content-loss audit reads new prose as intended rather than as drift. Everything else in this phase is still a move or a trim, not a rewrite.
- **D-19 — Port G3 to full parity with `check-links.py`'s `_code_fence_mask` BEFORE any fenced block lands under `docs/`.** `LEARNINGS.md` binds this on the first phase to add a fence under `docs/`, and phase 03 is that phase (the index, and any Quick start examples). G3 currently toggles on any fence-shaped line and lacks the checker's same-character close rule; it has read clean only because none of the nine carved pages contains a fence. Make it its own task, done first. A guard that reports clean while blind is worse than no guard (`conventions.md` → Fail-closed guards).
- **D-20 — The opening condenses to 2–3 sentences and the displaced prose MOVES.** README's three dense positioning paragraphs become a tight statement above the install blocks (REQ-03: installable without scrolling past the first screen). The displaced detail — the Aspire / ship-pipeline framing and the orchestrator-agnostic argument — relocates into the `docs/` pages that already own those topics. It is not deleted; phase 04's audit must find it.

## Deferred
- Repointing inbound references and prose mentions, and the content-loss audit — REQ-06/REQ-08, phase 04. `plugins/devflow/skills/flow-status/SKILL.md` still names README sections in prose and stays broken until then.
- Extending `check-links.py` to scan inside fences — considered and rejected again; D-19 hardens the phase guard instead of reopening a checker that took three review rounds to stabilise.

## Discretion
- The exact wording of the two new sections, provided both stay minimal and link out.
- The index's ordering and grouping in `docs/README.md`, provided every `docs/*.md` except itself is linked with a one-line "what it answers" (REQ-04).
- Whether `## Flow`'s ASCII diagram lives under `## Quick start` or beside it, provided README ends with exactly the six sections REQ-01 names.
- Which `docs/` page receives each displaced opening paragraph under D-20.

## Watch out
- SC-04 is the real test of this phase: a first-time reader must get from the top of README to a running `/flow-new` **without opening `docs/`**. A Quick start that only links out fails it.
- REQ-02 — the 20-row command table's content is unchanged. Do not reflow, retitle, or "improve" it.
- SC-01 — README ≤ 110 lines and ≤ 14KB. It is at 61 lines / 4.3KB now, so there is room; the cap is not the binding constraint, REQ-03's first-screen rule is.
- Eight of the nine carved pages have no inbound link outside `.planning/` until this phase's index lands. Until then `check-links.py` cannot tell you a page is orphaned — it validates links that exist, not links that should.
- The three-step smoke command must stay green at every commit, and the reference count (179 now, floor 140) should RISE as the index adds links. A fall means something was dropped.
