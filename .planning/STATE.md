<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: 4 of 4 (complete) | Plans: 4/4 | Status: merged
Last: 2026-09-08 — quick 013 on flow/quick-013-ci-gates-and-versions (v0.21.0): ARCHITECTURE
  `## CI gates`, template stack → .NET 10 / C# 14. 2 review rounds, 1 blocking fixed (a false
  "direct pushes are closed off" — admins are exempt); round 2 clean. Smoke green
Next: /flow-pr — first PR under the new protection, so it also proves it

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

## Blockers
- none

## Session
Stopped: PR #37 open — https://github.com/jbrianfrancis-ir/devflow/pull/37
Resume: /flow-ci 37 — first PR under the new protection; validate is a required check

