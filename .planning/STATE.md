<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: 4 of 4 (complete) | Plans: 4/4 | Status: verified
Last: 2026-08-27 — PR #30 (v0.17.0, /flow-hooks) and PR #31 (flow-pr direct-invocation
  gate) both open in parallel off main, not yet merged
Next: /flow-ci for PR #30, then PR #31 (or vice versa) — expect a STATE.md/JOURNAL.md
  merge conflict between them, resolve by keeping both entries

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

## Blockers
- none

## Session
Stopped: PR #31 opened (github.com/jbrianfrancis-ir/devflow/pull/31) — quick 010, 2 commits
Resume: /flow-ci for PR #30 and #31. /flow-handsoff is deferred to its own branch — see DECISIONS 2026-08-22 for why
