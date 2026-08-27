<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: 4 of 4 (complete) | Plans: 4/4 | Status: verified
Last: 2026-08-27 — quick 011 (stale PR state) done: autonomy.md live-read rule,
  flow-next rules 8-11 + flow-status PR rows re-read gh live, STATE.md repaired
Next: /flow-pr for flow/stale-pr-state

## Gate
type: none
asked: none
options: none
default: none
plan: none | task: none

## Run
Iteration: 1 | Started: 2026-08-27T18:54Z | Repeats: 0
Signature: none

## Decisions
- init: no deployable surface — harden/uat/release N/A (D-06)
- init: link checker is stdlib-only scripts/check-links.py (D-04)
- phase 3: SC-04 confirmed PASS by human read-through (2026-08-19)
- quick 001: Aspire refs at 13.5.0; auto-apply policy left unchanged — minors now
  carry breaking changes, open question for the human
- quick 009: /flow-hooks scaffolds guard-only PreToolUse backstops (base-branch,
  protected-paths, secret-scan); no .planning/ required to run it
- quick 011: external state (PR/CI/deploy) is a cache, never evidence — re-read
  live before routing or asserting on it (autonomy.md)

## Blockers
- none

## Session
Stopped: quick 011 all 4 tasks committed on flow/stale-pr-state; smoke green
  (validate-plugin OK, 161 tests OK/2 skipped, check-links 0 failures/212 refs)
Resume: /flow-pr to open the PR for flow/stale-pr-state
