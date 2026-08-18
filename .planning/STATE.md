<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: 2 of 4 (Carve out docs/) | Plans: 0/5 | Status: ready
Last: 2026-08-18 — phase 2 planned: 5 plans, waves 1→5 serial; 10 plan-check issues fixed
Next: /flow-execute 2

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
Stopped: phase 2 planned and checked; nothing carved yet
Resume: user runs /flow-pr. CARRY INTO THE PR: confirm lint ran `Check internal links` and passed, then push a deliberately broken internal reference and confirm lint turns red on that step, and revert. Evidence in phases/01-link-safety-net/VERIFICATION.md
