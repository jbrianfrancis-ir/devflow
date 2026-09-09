<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: quick-015 (in progress) | Plans: 2/4 | Status: committed, not yet PR'd
Last: 2026-09-09 — quick 015-02: flow-prober role (R4, WRITE_ROLES, 13 agents);
  R7 hosts.md states .tmp+rename and never-diff-mid-write. 4 tasks, checks pass.
Next: quick 015 plans 03-04, then one manifest bump, then /flow-pr

## Gate
none

## Run
Iteration: 1 | Started: 2026-08-27T18:54Z | Repeats: 0
Signature: none

## Decisions
- init: no deployable surface — harden/uat/release N/A (D-06); link checker is
  stdlib-only scripts/check-links.py (D-04)
- quick 011: external state (PR/CI/deploy) is a cache, never evidence — re-read live
- 2026-09-08: main protected — validate required, PR required, admin bypass kept
- quick 014: falsify negative controls + execution-only assertions bind plan-format.md;
  revision rounds diff for silent deletion (v0.22.0)
- quick 015-01: secret-scan-guard.py pins diff prefixes, fails closed on unparseable diff;
  Forbidden entries may carry a regex, enforced across tracked files (R8)
- quick 015-02: flow-prober is a WRITE_ROLE (scratch build needs workspace-write,
  not repo access) — 13 agents; hosts.md states atomic .tmp+rename (R7)

## Blockers
- none

## Session
Stopped: quick 015 plan 02 done, 4 tasks committed (51f5b71..900d668), SUMMARY written
Resume: run quick 015 plans 03-04, then bump manifests once, then /flow-pr

