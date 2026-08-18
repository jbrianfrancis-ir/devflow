<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: 1 of 4 (Link safety net) | Plans: 3/3 | Status: verified
Last: 2026-08-18 — ARCHITECTURE.md `## Link checking` reconciled with the implementation; PR #20 green
Next: human — merge PR #20; then /flow-plan 2

## Gate
none

## Decisions
- init: README trimmed to install/quickstart/commands/index, ≤110 lines (D-01)
- init: docs/ stays flat topic files + docs/README.md index (D-02)
- init: link checker is stdlib-only scripts/check-links.py, no third-party CI action (D-04)
- init: no deployable surface — harden/uat/release N/A (D-06)
- phase 2: docs/ summarizes + links to references/ as source of truth (D-10)
- phase 1: anchor-slug backstop abstention accepted, left unproven (D-12)
- phase 1: ARCHITECTURE.md link-checking contract reconciled to implementation (D-13)

## Blockers
- none

## Session
Stopped: PR #20 green, contract reconciled — https://github.com/jbrianfrancis-ir/devflow/pull/20 — awaiting human merge
Resume: user runs /flow-pr. CARRY INTO THE PR: confirm lint ran `Check internal links` and passed, then push a deliberately broken internal reference and confirm lint turns red on that step, and revert. Evidence in phases/01-link-safety-net/VERIFICATION.md
