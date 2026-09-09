<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: 4 of 4 (complete) | Plans: 4/4 | Status: committed, not yet PR'd
Last: 2026-09-09 — quick 014 (v0.22.0): closed False Green P0 (R1-R3) — falsify negative
  control + execution-only assertion in plan-format.md, checker check 5b, executor
  falsify-then-verify flow, revision deletion diff. Falsify clauses run for real.
  5 pre-existing test_flow_hooks failures deferred.
Next: /flow-pr — open PR for quick 014

## Gate
none

## Run
Iteration: 1 | Started: 2026-08-27T18:54Z | Repeats: 0
Signature: none

## Decisions
- init: no deployable surface — harden/uat/release N/A (D-06)
- init: link checker is stdlib-only scripts/check-links.py (D-04)
- quick 009: /flow-hooks scaffolds guard-only PreToolUse backstops (base-branch,
  protected-paths, secret-scan); no .planning/ required to run it
- quick 011: external state (PR/CI/deploy) is a cache, never evidence — re-read
  live before routing or asserting on it (autonomy.md)
- 2026-09-08: main is protected — `validate` required, PR required (0 approvals),
  admin bypass kept, strict=false. Gates the merge path; an admin push still bypasses
- quick 014: falsify negative controls + execution-only test assertions bind plan-format.md;
  revision rounds diff must_haves/files_modified for silent deletion (v0.22.0)

## Blockers
- none

## Session
Stopped: quick 014 done, 5 tasks committed (687a27d..c0f6212), SUMMARY written; not pushed
Resume: /flow-pr

