<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: 3 of 4 (Rebuild README) | Plans: 0/4 | Status: ready
Last: 2026-08-18 — phase 3 planned: 4 plans, serial; 9 check issues fixed incl. 3 fail-open guards. PR #21 open for phase 2 (held)
Next: /flow-execute 3

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
Stopped: phase 3 planned and checked; PR #21 open for phase 2, marked do-not-merge-yet
Resume: /flow-execute 3. OPENING-MAP.md holds the opening-paragraph disposition; G1-G7 in it are the per-commit gates. 03-01 builds scripts/check-fenced-paths.py FIRST (D-19) before any fence lands under docs/
