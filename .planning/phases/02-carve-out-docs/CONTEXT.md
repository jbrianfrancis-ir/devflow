# Phase 02 — Carve out docs/ · Context

## Locked
- **D-14 — This phase is a true MOVE, not a copy.** Content is removed from `README.md` in the same commit that lands it in a `docs/` page. There is never a window where the same prose lives in both. Consequence to accept knowingly: between phase 02 and phase 03, `README.md` is a thin husk — sections gone, no index yet — and that is how it will render on GitHub if anyone looks mid-flight. REQ-07 already implies this shape (it has this phase replace Acknowledgements with a pointer).
- **D-15 — No repo path reference may land inside a fenced code block.** `check-links.py` masks fenced content entirely, so a path moved into a fence silently loses CI coverage — the exact hole `LEARNINGS.md` opens with, and this is the phase most likely to create it. Path references stay in prose where the checker can see them. This is verified, not merely intended: a `must_haves` truth must grep the new `docs/` pages for path-shaped tokens inside fences and fail if any appear.
- **D-16 — Topics REQ-05 does not name fold into the nearest named page.** Conventions, architecture constraints, and the smoke gate fold into the execution-model page; second opinions (`/flow-oracle`) and design constraints fold into their nearest topical home. This keeps REQ-05's eight files and SC-03's 250-line cap intact without widening the requirement. **The planner must state the exact section→file mapping in the plan** so it is reviewable before any prose moves.

## Deferred
- `docs/README.md` (the index) — REQ-04, phase 03. The carved pages land unindexed in this phase; that is deliberate and is why the intermediate state is ugly.
- Rewriting `README.md` into its final shape — REQ-01/02/03, phase 03. This phase only *removes* what it moves; it does not restructure what remains.
- Repointing inbound references and the content-loss audit — REQ-06/REQ-08, phase 04.
- Extending `check-links.py` to see inside fences — considered and rejected for now; it reopens a file that took three review rounds to stabilise, and fenced examples legitimately carry fake paths that would need their own skip rule.

## Discretion
- Page filenames within REQ-05's named topics, and the order pages are carved.
- How much of each section is summary versus link under D-10/REQ-12a, provided no behavior fact appears in full in both a `docs/` page and its `references/*.md` contract.
- Whether to carve one page per commit or group closely related pages, provided every commit is a complete move (removal + arrival together, per D-14).

## Watch out
- `NOTICE` must stay byte-identical (REQ-07). The Acknowledgements prose moves verbatim; `NOTICE` is the legal artifact and is not touched.
- `references/*.md` is not edited by this project (REQ-12c).
- The smoke command now has three steps and includes the link check; every commit must leave it green, and the checker's reported reference count must not collapse (floor 140, currently 162).
- A `docs/` page that contradicts its `references/` contract is a defect, not staleness (REQ-12a).
