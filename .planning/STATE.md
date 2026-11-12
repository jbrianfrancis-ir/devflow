<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: none active | Status: complete — Documentation Restructure project done
Last: 2026-11-12 — last shipped 0.54.0 on main
Next: none queued — start new work with /flow-quick or a new project

## Gate
none

## Run
Iteration: 2 | Started: 2026-08-27T18:54Z | Repeats: 0
Signature: rule8:phase04:plans4/4:verifverified

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
Stopped: no active phase — 0.55.0 architecture refresh open as PR #85 (feat/arch-refresh)
Resume: /flow-ci 85, then /flow-status
