<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: 4 of 4 (complete) | Plans: 4/4 | Status: verified
Last: 2026-08-27 — PR #30 (v0.17.0, /flow-hooks) and PR #31 (flow-pr direct-invocation
  gate) both merged to main; no open PRs
Next: quick 011 (stale PR state) in flight on flow/stale-pr-state

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
Stopped: PRs #30 and #31 both merged to main 2026-08-27 (16:28-16:29Z); rule-10 gate
  on #31 answered by the merge itself
Resume: continue quick 011 (stale-pr-state) on flow/stale-pr-state; no /flow-ci owed
  to either PR
