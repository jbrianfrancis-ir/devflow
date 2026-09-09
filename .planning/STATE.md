<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: quick-015 (in progress) | Plans: 1/4 | Status: committed, not yet PR'd
Last: 2026-09-09 — quick 015-01: closed secret-scan-guard.py's live fail-open
  (mnemonicPrefix/noprefix bypass); diff calls pin prefixes, unparseable diff fails
  closed. R8: Forbidden entries may carry a regex. 4 tasks, tests 33->36 OK.
Next: quick 015 plans 02-04, then one manifest bump, then /flow-pr

## Gate
none

## Run
Iteration: 1 | Started: 2026-08-27T18:54Z | Repeats: 0
Signature: none

## Decisions
- init: no deployable surface — harden/uat/release N/A (D-06); link checker is
  stdlib-only scripts/check-links.py (D-04)
- quick 009: /flow-hooks scaffolds guard-only PreToolUse backstops; no .planning/ required
- quick 011: external state (PR/CI/deploy) is a cache, never evidence — re-read live
- 2026-09-08: main protected — validate required, PR required, admin bypass kept
- quick 014: falsify negative controls + execution-only assertions bind plan-format.md;
  revision rounds diff for silent deletion (v0.22.0)
- quick 015-01: secret-scan-guard.py pins diff prefixes, fails closed on unparseable diff;
  Forbidden entries may carry a regex, enforced across tracked files (R8)

## Blockers
- none

## Session
Stopped: quick 015 plan 01 done, 4 tasks committed (4a5d4cc..42f5287), SUMMARY written
Resume: run quick 015 plans 02-04, then bump manifests once, then /flow-pr

