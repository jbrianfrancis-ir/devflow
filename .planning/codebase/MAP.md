<!-- .planning/codebase/MAP.md — cap 6KB. Memory for planners/executors, not documentation. Overwrite whole file on refresh. -->
---
mapped: 2026-08-18
mapped_sha: d1dfd048f53c3e25dadbe586c5c6eff6d543c468
---
# Codebase Map

## Stack
This repo IS a Claude Code / Codex plugin (not an app that runs it): markdown prompt content (skills/agents/references/templates) + 3 stdlib-only Python 3 helper scripts. No language manifest (no package.json/pyproject.toml/go.mod/csproj) — nothing to install or build.

## Layout
```
plugins/devflow/          portable payload, shared by both hosts
  .claude-plugin/, .codex-plugin/  per-host plugin.json manifests (version must match)
  agents/*.md                11 subagent role files (name/description/tools/model)
  skills/<flow-x>/SKILL.md   20 skill dirs — /flow-* (Claude) == $flow-* (Codex)
  references/*.md            11 shared doctrine docs (conventions, autonomy, ...)
  templates/*.md              17 output templates
  scripts/flow-agent.py      cross-provider dispatch bridge (role → claude -p / codex exec)
  scripts/flow-fleet.py      fleet scanner (walks .planning/ across repos)
.claude-plugin/, .agents/plugins/  repo-root marketplace.json files → ./plugins/devflow
scripts/validate-plugin.py  repo-level CI validator (not shipped as plugin content)
scripts/check-links.py     repo-level internal-reference checker (not shipped)
tests/*.py                  unittest suites: flow_agent, flow_fleet, check_links (49 tests)
docs/blitzos.md, docs/status-contract.md   external-consumer contracts (no skill loads them)
README.md                   167 lines / ~31.6KB — the only other user-facing doc (unsplit so far)
CLAUDE.md, AGENTS.md, .claude/settings.json   repo root — plugin self-bootstrap pointers
.planning/                  this repo is itself DevFlow-managed (docs-restructure project)
```
Layout deliberately differs from DevFlow's own default convention (code under `src/`) — payload lives under `plugins/devflow/` because that's the plugin-source layout, not an app layout.

## Architecture
Not a running app — no runtime data flow. A user's project installs `plugins/devflow` via the marketplace; each skill is a markdown prompt loaded on invocation (`/flow-*`/`$flow-*`); heavy work spawns fresh-context subagents (`agents/*.md`); cross-provider roles route through `flow-agent.py` (`claude -p`/`codex exec`, sandboxed via `READ_ONLY_ROLES`/`WRITE_ROLES`); `flow-fleet.py` backs `/flow-status --all`. `validate-plugin.py` and `check-links.py` are the only things that "run" this repo's own code, both in CI (`lint.yml`).

## Conventions
- Skill dirs and agent files name-match 1:1 into `flow-agent.py`'s `READ_ONLY_ROLES`/`WRITE_ROLES` sets (agent filename minus `flow-`); `validate-plugin.py` enforces this plus frontmatter shape and that read-only-role agents declare no write tools.
- Both plugin.json manifests must carry identical `version`; marketplace.json files point at `./plugins/devflow`. CI pins exactly 20 skills, 11 agents.
- Prose style (README + references + skills): dense, terse, load-bearing — no filler. Match this register editing any `.md` here.
- Tests import the hyphenated `flow-*.py`/`check-links.py` scripts via `importlib.util.spec_from_file_location` (hyphens aren't valid module names) — follow for new script tests.

## Commands
Smoke (verified; `.planning/ARCHITECTURE.md ## Smoke`; same 3 steps as CI `lint.yml`):
`python3 scripts/validate-plugin.py && python3 -m unittest discover -s tests -v && python3 scripts/check-links.py`
build: none | test: unittest, 49 tests | lint: validate-plugin.py | links: check-links.py | run: N/A — install via `/plugin marketplace add jbrianfrancis-ir/devflow` (Claude) or `codex plugin marketplace add …/devflow` (Codex). `release.yml` tags/releases on push to main when `version` is untagged.

## Env vars
- `DEVFLOW_SMOKE` — gates one live-CLI test, `tests/test_flow_agent.py:163`; unset in normal CI.
- `flow-agent.py:154` passes `os.environ.copy()` to the dispatched CLI subprocess; no specific names read here.

## Related repos
- github.com/blitzdotdev/blitzos — DevFlow repos slot into BlitzOS-style context repos; contract in `docs/blitzos.md`.
- github.com/open-gsd/gsd-core — phase-loop is an independent reimplementation (no shared source); `/flow-migrate` converts a GSD `.planning/`.
- github.com/steipete/oracle, github.com/github/spec-kit, github.com/Dzazaleo/adversarial-review-skills — concept-only prior art, README § Acknowledgements.

## Gotchas
- **README split: phase 01/4 done, 02-04 pending.** Phase 01 only built the link-safety net (`check-links.py` + CI + smoke) — README untouched, still 167 lines. 02 carves topics into `docs/` pages; 03 rewrites README as install+quickstart+commands+docs-index; 04 repoints every inbound ref (incl. prose) and audits content loss. `docs/status-contract.md`/`docs/blitzos.md` already exist as sources README compresses; everything else (graph execution, conventions, autonomy, plan-format, oracle, adjudication) → `plugins/devflow/references/*.md`. REQ-12/D-10: a docs/ page summarizes + links its reference, never restates normative detail.
- **`check-links.py` skips fenced code blocks** (`_code_fence_mask`, applied before the link/backtick regexes) — a path moved inside a ``` fence during the 02-04 moves loses CI coverage silently.
- Inbound links needing redirect on the eventual split: `README.md`→`docs/status-contract.md` (L7), `docs/blitzos.md` (L44); `references/conventions.md`→`docs/blitzos.md` ×2; `templates/journal.md`/`flow-fleet.py` mention `docs/blitzos.md` in comments only; `.github/ISSUE_TEMPLATE/config.yml`→`…devflow#readme` (external). `references/autonomy.md`'s dangling link already fixed (phase 01). `skills/flow-status/SKILL.md` names README sections in prose only — goes stale silently if they move.
- `validate-plugin.py` parses `READ_ONLY_ROLES`/`WRITE_ROLES` out of `flow-agent.py` by regex, not import — keep those literals regex-parseable.
- MIT licensed; NOTICE carries required upstream attributions — keep in sync with README § Acknowledgements.
