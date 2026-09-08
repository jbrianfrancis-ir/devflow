<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: 4 of 4 (complete) | Plans: 4/4 | Status: merged
Last: 2026-09-08 — PR #36 merged 2026-09-04 (e665a01): release 0.20.0 + version-bump
  CI gate; `validate` green, zero review threads. Milestone complete
Next: no roadmap work remains (D-06: no uat/release). /flow-quick the TODOS items on a
  fresh branch, or open the next milestone

## Gate
type: none
asked: none — branch protection resolved 2026-09-08 (option 1)
options: none
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
- 2026-09-08: main is protected — `validate` required, PR required (0 approvals),
  admin bypass kept, strict=false. #36's version gate now enforces on the merge path

## Blockers
- none

## Session
Stopped: PR #36 merged; .planning/ edits (TODOS, STATE, JOURNAL) uncommitted on the
  merged branch flow/release-0-20-0 — they need a fresh branch to reach main
Resume: answer the branch-protection gate; carry the .planning/ edits onto a new branch
