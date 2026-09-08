<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: 4 of 4 (complete) | Plans: 4/4 | Status: merged
Last: 2026-09-08 — quick 013 on flow/quick-013-ci-gates-and-versions (0e2369f, v0.20.1):
  ARCHITECTURE names both CI gates, template stack → .NET 10 / C# 14. Smoke green
Next: /flow-pr — this is the first PR under the new protection, so it also proves it

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
  admin bypass kept, strict=false. #36's version gate now enforces on the merge path

## Blockers
- none

## Session
Stopped: quick 013 committed on flow/quick-013-ci-gates-and-versions, not yet pushed
Resume: /flow-pr — main now requires a PR, so this is the only route in
