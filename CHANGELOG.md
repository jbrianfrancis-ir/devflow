# Changelog

## 0.39.0 (2026-11-02)
- Size budget: `scripts/budget-count.sh` and per-metric caps, enforced in CI.
- `destructive-git-guard.py` also blocks `git checkout .` / `git checkout -- .` and `git restore .`; `git restore --staged .` stays allowed.
- `/flow-pr` fix loop: the L×S < 5 rare-case cutoff, the two-strikes rule, and fix scope.
- Post-compaction rule in conventions.md; the agent-pointer block drops its overview table.
