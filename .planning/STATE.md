<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: quick-016 (complete) | Plans: 4/4 | Status: 016-01..016-04 all committed
Last: 2026-09-09 — quick 016-04: prober scratch-root claim scoped to what each
  peer enforces (codex --sandbox/--cd real; claude cwd+prompt only, no
  confining flag exists); SCRATCH_ROLES validator check no longer fails open
  on a regex miss; 3 offline rooting tests added (18 total, DEVFLOW_SMOKE
  still gates the live-CLI pair); hosts.md .tmp rule scoped off prober.
Next: quick-016 done — run /flow-status for the next roadmap item

## Gate
none

## Run
Iteration: 1 | Started: 2026-08-27T18:54Z | Repeats: 0
Signature: none

## Decisions
- init: no deployable surface (D-06); link checker stdlib-only (D-04)
- quick 011: external state (PR/CI/deploy) is a cache, not evidence
- 2026-09-08: main protected — validate+PR required, admin bypass kept
- quick 014: falsify negative controls + execution-only assertions bind
  plan-format.md (v0.22.0)
- quick 015-01/02/03: secret-scan diff-prefix pins (R8); flow-prober WRITE_ROLE
  (R7); backstop resolution -> truths entry (R5); checker cross-plan refs (R6)
- quick 015-04: flow-split-plan.py is the 4KB-cap remedy (R9); split don't trim
- quick 016-01: plan-ref regex anchors to phase prefix + boundary lookaround;
  new-plan depends_on/wave only edges back to source when files overlap
- quick 016-04: no claude CLI flag confines writes to a directory without
  removing Bash; prober's scratch-root guarantee is codex-only, claude relies
  on cwd+prompt — docs and code now say so explicitly per peer

## Blockers
- none

## Session
Stopped: quick 016 plan 04 done, 3 tasks committed (88edf73..6f589d4), SUMMARY written
Resume: quick-016 complete — pick the next roadmap/quick item

