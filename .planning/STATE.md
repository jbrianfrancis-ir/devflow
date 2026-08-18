<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: 4 of 4 (complete) | Plans: 4/4 | Status: verified
Last: 2026-08-18 — phases 3 AND 4 done; phase 4 run as ad-hoc work, not a planned phase
Next: PR this branch, then merge

## Gate
none

## Decisions
- init: README trimmed to install/quickstart/commands/index, ≤110 lines (D-01)
- init: docs/ stays flat topic files + docs/README.md index (D-02)
- init: link checker is stdlib-only scripts/check-links.py, no third-party CI action (D-04)
- init: no deployable surface — harden/uat/release N/A (D-06)
- phase 2: docs/ summarizes + links to references/ as source of truth (D-10)
- phase 2: true move, no fence-hidden paths, fold-ins mapped (D-14/15/16)
- phase 1: anchor-slug backstop abstention accepted, left unproven (D-12)
- phase 1: ARCHITECTURE.md link-checking contract reconciled to implementation (D-13)

## Blockers
- none

## Session
Stopped: all four phases complete; README rebuilt, docs indexed, references repointed
Resume: SC-04 human check open — read README top-to-bottom as a newcomer, follow no docs/ link, confirm /flow-new through /flow-execute 1 works from README alone
