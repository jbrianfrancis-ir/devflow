<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: 4 of 4 (complete) | Plans: 4/4 | Status: verified
Last: 2026-08-21 — quick 004–006 on flow/deploy-na-routing; /flow-pr review closed (3 blocking)
Next: /flow-pr — push and open the PR for flow/deploy-na-routing (7 commits)

## Gate
none

## Run
Iteration: 2 | Started: 2026-08-19T21:55Z | Repeats: 0
Signature: rule7:phase04:plans4/4:verifverified — superseded by D-06, terminal DONE

## Decisions
- init: no deployable surface — harden/uat/release N/A (D-06)
- init: link checker is stdlib-only scripts/check-links.py (D-04)
- phase 2: docs/ summarizes + links to references/ as source of truth (D-10)
- phase 3: SC-04 confirmed PASS by human read-through (2026-08-19)
- quick 001: Aspire refs at 13.5.0; auto-apply policy left unchanged — minors now
  carry breaking changes, open question for the human
- D-21: skills may declare hooks (skill-scoped, prompt-type, validated) — reverses
  the standing "ships no hooks" property; /flow-handsoff needs it

## Blockers
- none

## Session
Stopped: mid-/flow-pr on flow/deploy-na-routing — review fixes committed, version bumped, PR not yet opened
Resume: /flow-pr to open it. Phase 03/04 VERIFICATION records now exist (quick 003); phase 03 carries two SUPERSEDED byte-identity truths recorded in its gaps
