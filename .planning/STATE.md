<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: 4 of 4 (verified) | Plans: 4/4 | Status: merged — roadmap complete
Last: 2026-09-10 — PR #38 merged (9e18b8f), validate green in 13s: all nine False
  Green requirements + a live secret-scan fail-open (diff.mnemonicPrefix silently
  disarmed the guard). v0.23.0. 3 review rounds / 6 lenses / 14 blocking closed
Next: none — deploy N/A (D-06), so a merged PR is the end state

## Gate
none

## Run
Iteration: 1 | Started: 2026-09-10T14:13Z | Repeats: 0
Signature: none

## Decisions
- init: no deployable surface (D-06); link checker stdlib-only (D-04)
- 2026-09-08: main protected — validate+PR required, admin bypass kept
- quick 014: falsify negative controls bind plan-format.md; external state is
  a cache, not evidence (quick 011)
- quick 015: flow-prober is a WRITE role (scratch-rooted); 4KB cap is now a
  SOFT target — never loop or trim to meet it, split with flow-split-plan.py
- quick 016: prober's scratch guarantee is codex-only (no claude flag confines
  writes without removing Bash) — docs say so per peer. Forbidden-regex scan is
  diff-scoped; repo-wide history scanning belongs in CI, not a per-commit hook

## Blockers
- none

## Session
Stopped: PR #38 merged — roadmap verified, nothing pending
Resume: new work starts at /flow-quick or a new roadmap phase via /flow-plan
