<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: 1 of 4 (Link safety net) | Plans: 0/3 | Status: ready
Last: 2026-08-17 — phase 1 planned: 3 plans, waves 1→3; plan-check PASS after 3 rounds
Next: /flow-execute 1

## Gate
none

## Decisions
- init: README trimmed to install/quickstart/commands/index, ≤110 lines (D-01)
- init: docs/ stays flat topic files + docs/README.md index (D-02)
- init: link checker is stdlib-only scripts/check-links.py, no third-party CI action (D-04)
- init: no deployable surface — harden/uat/release N/A (D-06)

## Blockers
- none

## Session
Stopped: phase 1 planned and checked (PASS); nothing executed yet
Resume: /flow-execute 1. Check report at .planning/phases/01-link-safety-net/CHECK.md. REQ-12's open marker belongs to phase 2 — /flow-plan 2 must ask about it
