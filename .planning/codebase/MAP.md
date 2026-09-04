<!-- .planning/codebase/MAP.md — cap 6KB. Memory for planners/executors, not documentation. Overwrite whole file on refresh. -->
---
mapped: 2026-08-18
mapped_sha: 1da9692e636e590fa6a0e924d84356e0cf4f6bef
---
# Codebase Map

## Stack
This repo IS a Claude Code / Codex plugin (not an app that runs it): markdown prompt content (skills/agents/references/templates) + 3 stdlib-only Python 3 helper scripts. No language manifest — nothing to install or build.

## Layout
```
plugins/devflow/          portable payload, shared by both hosts
  .claude-plugin/, .codex-plugin/  per-host plugin.json manifests (version must match)
  agents/*.md                11 subagent role files (name/description/tools/model)
  skills/<flow-x>/SKILL.md   20 skill dirs — /flow-* (Claude) == $flow-* (Codex)
  references/*.md            11 shared doctrine docs — the authoritative layer
  templates/*.md              18 output templates
  scripts/flow-agent.py      cross-provider dispatch bridge (role → claude -p / codex exec)
  scripts/flow-fleet.py      fleet scanner (walks .planning/ across repos)
.claude-plugin/, .agents/plugins/  repo-root marketplace.json files → ./plugins/devflow
scripts/validate-plugin.py, scripts/check-links.py, scripts/check-fenced-paths.py, scripts/check-version-bump.py   repo-level CI validators (not shipped as plugin content)
tests/*.py                  unittest suites: flow_agent, flow_fleet, check_links, check_fenced_paths, check_version_bump (183 tests)
docs/                       11 pages: blitzos.md, status-contract.md (pre-existing) + 9 new (phase 02) —
                             acknowledgements, autonomy, execution-model, installation, parallel-work,
                             provenance, providers, requirements-clarity, review — each summarizing +
                             linking its references/*.md authority
README.md                   61 lines (was 167) — Install, Commands, Flow, Acknowledgements
CLAUDE.md, AGENTS.md, .claude/settings.json   repo root — plugin self-bootstrap pointers
.planning/                  this repo is itself DevFlow-managed (docs-restructure project)
```
Layout deliberately differs from DevFlow's default convention (code under `src/`) — payload lives under `plugins/devflow/` because that's the plugin-source layout, not an app layout.

## Architecture
Not a running app — no runtime data flow. A user's project installs `plugins/devflow` via the marketplace; each skill is a markdown prompt loaded on invocation (`/flow-*`/`$flow-*`); heavy work spawns fresh-context subagents (`agents/*.md`); cross-provider roles route through `flow-agent.py` (`claude -p`/`codex exec`, sandboxed via `READ_ONLY_ROLES`/`WRITE_ROLES`); `flow-fleet.py` backs `/flow-status --all`. `validate-plugin.py`, `check-links.py` and `check-version-bump.py` (PR-only) are the code that runs in CI (`lint.yml`); `check-fenced-paths.py` is wired to no workflow. `docs/*.md` are pure summaries — detail stays in `references/*.md`.

## Conventions
- Skill dirs and agent files name-match 1:1 into `flow-agent.py`'s `READ_ONLY_ROLES`/`WRITE_ROLES` sets (filename minus `flow-`); `validate-plugin.py` regex-parses those literals and enforces the match, plus frontmatter shape and read-only agents declaring no write tools.
- Both plugin.json manifests must carry identical `version`; marketplace.json points at `./plugins/devflow`. CI pins exactly 20 skills, 11 agents.
- Prose style (README + docs/ + references + skills): dense, terse, load-bearing — no filler.
- `docs/*.md` (phase 02): one H1, topical H2s, each links its authority as `[`file.md`](../plugins/devflow/references/file.md)` — never a bare backticked path. Sibling links as `blitzos.md`, not `docs/blitzos.md` (markdown links resolve against the referring file's own dir only — github.com's rule).
- Tests import hyphenated `flow-*.py`/`check-links.py` via `importlib.util.spec_from_file_location` (hyphens aren't valid module names).

## Commands
Smoke (verified; `.planning/ARCHITECTURE.md ## Smoke`; CI `lint.yml` runs these 3 plus a PR-only version-bump gate):
`python3 scripts/validate-plugin.py && python3 -m unittest discover -s tests -v && python3 scripts/check-links.py`
build: none | test: unittest, 183 tests | lint: validate-plugin.py | links: check-links.py (`0 failures, 179 checked`; floor 140) | run: N/A — install via `/plugin marketplace add jbrianfrancis-ir/devflow` (Claude) or `codex plugin marketplace add …/devflow` (Codex).

## Env vars
- `DEVFLOW_SMOKE` — gates one live-CLI test, `tests/test_flow_agent.py:163`; unset in normal CI.
- `flow-agent.py:154` passes `os.environ.copy()` to the dispatched CLI subprocess; no specific names read.

## Related repos
- github.com/blitzdotdev/blitzos — DevFlow repos slot into BlitzOS-style context repos; contract in `docs/blitzos.md`.
- github.com/open-gsd/gsd-core — phase-loop is an independent reimplementation (no shared source); `/flow-migrate` converts a GSD `.planning/`.
- github.com/steipete/oracle, github.com/github/spec-kit, github.com/Dzazaleo/adversarial-review-skills — concept-only prior art, `docs/acknowledgements.md`.

## Gotchas
- **README split: phases 01/02 done, 03/04 pending.** 02 carved `docs/` from 2 pages to 11, shrinking README 167→61 lines. Only `docs/acknowledgements.md` has an inbound link from README — the other 8 new pages have **no inbound link outside `.planning/`** until phase 03 (rebuild README + `docs/README.md` index) and phase 04 (repoint every inbound reference incl. prose, audit content loss).
- **`check-links.py` masks fenced code blocks** — a path moved inside a ``` fence loses CI coverage silently. Phase 02's guard (MAPPING.md `G3`, an awk fence-toggle) is **not full parity**: no same-character-close rule, toggles on any fence-shaped line. Clean today only because the 9 new pages have zero fences (`blitzos.md`/`status-contract.md` do, and are excluded from G3). Port the same-char-close rule before the first fenced block lands under `docs/`.
- `validate-plugin.py` parses roles out of `flow-agent.py` by regex, not import — keep literals regex-parseable.
- MIT licensed; NOTICE carries required attributions — sync with `docs/acknowledgements.md`.
