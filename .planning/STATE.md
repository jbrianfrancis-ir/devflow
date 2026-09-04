<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: 4 of 4 (complete) | Plans: 4/4 | Status: verified
Last: 2026-09-04 — PR #36 (release 0.20.0 + version-bump CI gate); 3 review rounds,
  3 fail-opens fixed (2 blocking, each found by 2 lenses), smoke green
Next: /flow-ci 36; two human items in the PR body

## Gate
type: approval
asked: PR #36 — make `validate` a required status check on main (without it the new
  gate blocks nothing), and whether ARCHITECTURE.md names the 2nd CI gate + BASE_REF.
options:
  1. Set branch protection, fold the ARCHITECTURE.md wording into this PR
  2. Merge as-is — the gate reports but cannot enforce
default: none
plan: none | task: none

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

## Blockers
- none

## Session
Stopped: PR #36 open — https://github.com/jbrianfrancis-ir/devflow/pull/36
Resume: /flow-ci 36; the gate is PR-only, so #36 exercises it against itself
