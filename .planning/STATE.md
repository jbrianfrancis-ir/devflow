<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: quick-015 (in progress) | Plans: 4/4 | Status: committed, not yet PR'd
Last: 2026-09-09 — quick 015-04: R9 flow-split-plan.py implemented + tested;
  plan-format.md/flow-plan SKILL.md point the 4KB cap at it, split-don't-trim.
Next: one manifest bump (0.21.0 -> next), then /flow-pr

## Gate
none

## Run
Iteration: 1 | Started: 2026-08-27T18:54Z | Repeats: 0
Signature: none

## Decisions
- init: no deployable surface (D-06); link checker stdlib-only check-links.py (D-04)
- quick 011: external state (PR/CI/deploy) is a cache, not evidence — re-read live
- 2026-09-08: main protected — validate+PR required, admin bypass kept
- quick 014: falsify negative controls + execution-only assertions bind
  plan-format.md; revision rounds diff for silent deletion (v0.22.0)
- quick 015-01: secret-scan-guard pins diff prefixes, fails closed on unparseable
  diff; Forbidden entries may carry a regex (R8)
- quick 015-02: flow-prober is WRITE_ROLE (13 agents); hosts.md states atomic
  .tmp+rename (R7)
- quick 015-03: backstop resolution -> truths entry (R5); checker 6b cross-plan
  refs (R6)
- quick 015-04: flow-split-plan.py is the 4KB-cap remedy (R9); split don't trim;
  size re-checks after hand edits

## Blockers
- none

## Session
Stopped: quick 015 plan 04 done, 3 tasks committed (f0975b1..8caa7ae), SUMMARY written
Resume: bump manifests once (last step of quick-015), then /flow-pr

