# Changelog

## 0.41.0 (2026-11-04)
- Haiku lane for `flow-executor` (Claude native only, `hosts.md` → Model tiers): a `/flow-quick` mini-plan or sole-plan wave that edits only docs/config files (no architecture/auth/security/secret/migration/`.github/` paths), with no `<falsify>` or checkpoint task, spawns with the Agent tool's `model: "haiku"`; a CHECKPOINT, missing SUMMARY or failed verify gets one sonnet retry, and the executor is told the model actually passed for its trailer. `agents.models.executor` still wins. `/flow-quick` now passes provider and model to its executor.

## 0.40.0 (2026-11-02)
- Lite tier: `/flow-new` sets `config.json` `tier: "lite"` for one repo with no deploy surface expected under ~2k LOC (`--tier full|lite` overrides; edit `tier` to switch). Lite: ≤3 phases, one plan per phase, decisions settled in Discuss (also under `--auto`), one plan-check round (a second only for `[blocking]`/`[security]` issues or lint findings), `<falsify>` only on security and must-not-regress verifies, a hard 4KB plan cap (lint R8), the planner on Sonnet via `agents.models`, sequential execution in the main checkout with no worktrees or post-landing re-verify, and a verifier that trusts committed executor checks and re-runs only the smoke gate and must-not-regress or security checks.
- `flow-verifier` is a read-only role but was told to write `VERIFICATION.md`; it now returns the content and `/flow-execute` and `/flow-verify` write the file.
- The plan split rule lives once, in plan-format.md's split signals (flow-planner and flow-plan-checker point to it), and plan-format.md's restated "structured, never prose" paragraph is gone.

## 0.39.0 (2026-11-02)
- Size budget: `scripts/budget-count.sh` and per-metric caps, enforced in CI.
- `destructive-git-guard.py` also blocks `git checkout .` / `git checkout -- .` and `git restore .`; `git restore --staged .` stays allowed.
- `/flow-pr` fix loop: the L×S < 5 rare-case cutoff, the two-strikes rule, and fix scope.
- Post-compaction rule in conventions.md; the agent-pointer block drops its overview table.
