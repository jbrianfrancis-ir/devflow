# Changelog

## 0.45.0 (2026-11-07)
- Opt-in observed usage report (`"usage_report": true` in `.planning/config.json`; off by default, and off changes no output). The bridge (`flow-agent.py`) adds a `usage` object of numbers and enums only: claude-peer tokens are `modelUsage` summed over every model (its top-level `usage` covers only the final message), codex-peer tokens are `unknown`, duration is the bridge's wall clock, and failed or timed-out attempts are kept. The orchestrator writes executor and verifier dispatch records as one `usage:` JSON line in SUMMARY/VERIFICATION frontmatter (`hosts.md` → Usage report), and new `plugins/devflow/scripts/flow-usage.py` renders tokens, duration and retries by phase+role and role+model. Values not observed stay `unknown`, a real `0` stays `0`, a sum with gaps reads `partial: N (k/n known)`, tokens are never summed across sources, a SUMMARY/VERIFICATION with no record renders as an all-`unknown` `not recorded` row, and a duplicate dispatch is refused. `/flow-execute` writes the records at Close (a mid-run SUMMARY edit would trip the next `wave-start`). No savings or plan-percentage figures; no prompt or message text is recorded.

## 0.44.0 (2026-11-05)
- IMPACT visual-design constraints ([source](https://hackernoon.com/the-impact-framework-six-rules-for-better-ai-generated-designs)): new `references/impact.md` (Importance, Margins, Palette, Alignment, Contrast, Typography + an AVOID list, adjective→fact translations, lint order). `/flow-design` fills rules the design system leaves unstated as measurable IMPACT lines (and uses IMPACT defaults in manual mode); the DESIGN.md template's Rules hint asks for facts, not adjectives; `flow-planner` has UI tasks without a DESIGN.md state IMPACT facts in the `<action>`. Optional guidance, no new gate or phase: lite, `/flow-quick` and no-UI work are unaffected.

## 0.43.0 (2026-11-04)
- Haiku lane for `flow-executor` (Claude native only, `hosts.md` → Model tiers): a `/flow-quick` mini-plan or sole-plan wave that edits only docs/config files (no architecture/auth/security/secret/migration/`.github/` paths), with no `<falsify>` or checkpoint task, spawns with the Agent tool's `model: "haiku"`; a CHECKPOINT, missing SUMMARY or failed verify gets one sonnet retry, and the executor is told the model actually passed for its trailer. `agents.models.executor` still wins. `/flow-quick` now passes provider and model to its executor.

## 0.42.0 (2026-11-04)
- One-off routing: `/flow-new` defaults a one-off export, dump, report, format/convert, backfill, or one-time script job (no long-lived service, deploy target, or UI) to the lite tier after offering `/flow-quick`, records `"one_off":true`, and says so in one line; `--tier full` opts in. Plan-count guard: `flow-plan-lint.py` prints a non-fatal `WARN plan-count` past 8 plans, or past 2 phases on a lite/one-off job (`--plan-count --adding N` runs it alone); `/flow-plan` runs it before planning and offers to collapse. docs/hooks.md points to the `/flow-hooks` guard table instead of repeating it.

## 0.40.0 (2026-11-02)
- Lite tier: `/flow-new` sets `config.json` `tier: "lite"` for one repo with no deploy surface expected under ~2k LOC (`--tier full|lite` overrides; edit `tier` to switch). Lite: ≤3 phases, one plan per phase, decisions settled in Discuss (also under `--auto`), one plan-check round (a second only for `[blocking]`/`[security]` issues or lint findings), `<falsify>` only on security and must-not-regress verifies, a hard 4KB plan cap (lint R8), the planner on Sonnet via `agents.models`, sequential execution in the main checkout with no worktrees or post-landing re-verify, and a verifier that trusts committed executor checks and re-runs only the smoke gate and must-not-regress or security checks.
- `flow-verifier` is a read-only role but was told to write `VERIFICATION.md`; it now returns the content and `/flow-execute` and `/flow-verify` write the file.
- The plan split rule lives once, in plan-format.md's split signals (flow-planner and flow-plan-checker point to it), and plan-format.md's restated "structured, never prose" paragraph is gone.

## 0.39.0 (2026-11-02)
- Size budget: `scripts/budget-count.sh` and per-metric caps, enforced in CI.
- `destructive-git-guard.py` also blocks `git checkout .` / `git checkout -- .` and `git restore .`; `git restore --staged .` stays allowed.
- `/flow-pr` fix loop: the L×S < 5 rare-case cutoff, the two-strikes rule, and fix scope.
- Post-compaction rule in conventions.md; the agent-pointer block drops its overview table.
