<!-- .planning/codebase/MAP.md — cap 6KB. Memory for planners/executors, not documentation. Overwrite whole file on refresh. -->
---
mapped: 2026-08-17
mapped_sha: 5ccb5bd100f6ac635ae42e08ef5f4e0b8003b13f
---
# Codebase Map

## Stack
This repo IS a Claude Code / Codex plugin (not an app that runs it): markdown prompt content (skills/agents/references/templates) + 2 stdlib-only Python 3 helper scripts. No language manifest (no package.json/pyproject.toml/go.mod/csproj) — nothing to install or build.

## Layout
```
plugins/devflow/          portable payload, shared by both hosts
  .claude-plugin/plugin.json  Claude manifest (name/version/description)
  .codex-plugin/plugin.json   Codex manifest — version must match Claude's
  agents/*.md                11 subagent role files (name/description/tools/model)
  skills/<flow-x>/SKILL.md   20 skill dirs — /flow-* (Claude) == $flow-* (Codex)
  references/*.md            11 shared doctrine docs (conventions, autonomy, ...)
  templates/*.md              17 output templates
  scripts/flow-agent.py      cross-provider dispatch bridge (role → claude -p / codex exec)
  scripts/flow-fleet.py      fleet scanner (walks .planning/ across repos)
.claude-plugin/marketplace.json   repo-root Claude marketplace → ./plugins/devflow
.agents/plugins/marketplace.json  repo-root Codex marketplace → ./plugins/devflow (local)
scripts/validate-plugin.py  repo-level CI validator (not shipped as plugin content)
tests/test_flow_agent.py, test_flow_fleet.py   unittest suites for scripts above
docs/blitzos.md, docs/status-contract.md   external-consumer contracts (no skill loads them)
README.md                   167 lines / ~31.6KB — the only other user-facing doc
```
Layout deliberately differs from DevFlow's own default convention (code under `src/`) — payload lives under `plugins/devflow/` because that's the plugin-source layout, not an app layout.

## Architecture
Not a running app — no runtime data flow here. A user's project installs `plugins/devflow` via the marketplace; each skill is a markdown prompt loaded on invocation (`/flow-*`/`$flow-*`); heavy work spawns fresh-context subagents (`agents/*.md`); cross-provider roles route through `flow-agent.py` (`claude -p`/`codex exec`, sandboxed via `READ_ONLY_ROLES`/`WRITE_ROLES`); `flow-fleet.py` backs `/flow-status --all`. `validate-plugin.py` is the only thing that "runs" this repo's code, in CI.

## Conventions
- Skill dirs and agent files name-match 1:1 into `flow-agent.py`'s `READ_ONLY_ROLES`/`WRITE_ROLES` sets (agent filename minus `flow-`); `validate-plugin.py` enforces this plus frontmatter shape and that read-only-role agents declare no write tools.
- Both plugin.json manifests must carry identical `version`; both marketplace.json files must point at `./plugins/devflow`. Counts pinned in CI: exactly 20 skills, 11 agents.
- Prose style (README + references + skills): dense, terse, load-bearing — no filler. Match this register editing any `.md` here.
- Tests import the hyphenated `flow-*.py` scripts via `importlib.util.spec_from_file_location` (hyphens aren't valid module names) — follow for new script tests.

## Commands
build: none | test: `python3 -m unittest discover -s tests -v` (verified, exits 0; one test gated behind `DEVFLOW_SMOKE=1`) | lint: `python3 scripts/validate-plugin.py` (verified, exits 0) | run: N/A — install via `/plugin marketplace add jbrianfrancis-ir/devflow` (Claude) or `codex plugin marketplace add …/devflow` (Codex)
CI `lint.yml` (push to main + PRs): runs both commands above. `release.yml` (push to main + manual dispatch): tags/releases when plugin.json's `version` is untagged.

## Env vars
- `DEVFLOW_SMOKE` — gates one live-CLI test, `tests/test_flow_agent.py:163`; unset in normal CI.
- `flow-agent.py:154` passes `os.environ.copy()` to the dispatched CLI subprocess; no specific names read here.

## Related repos
- github.com/blitzdotdev/blitzos — DevFlow repos slot into BlitzOS-style context repos; contract in `docs/blitzos.md`.
- github.com/open-gsd/gsd-core — phase-loop is an independent reimplementation (no shared source); `/flow-migrate` converts a GSD `.planning/`.
- github.com/steipete/oracle, github.com/github/spec-kit, github.com/Dzazaleo/adversarial-review-skills — concept-only prior art, README § Acknowledgements.

## Gotchas
- **README.md (167 lines) is about to be split.** Sections: Install (provider selection, model tiers, BlitzOS repos), Commands (table), Flow (graph execution, provenance, smoke gate, conventions, architecture constraints, oracle, design constraints), Saying "unknown" out loud (clarification markers, assumptions, success criteria, `/flow-audit`), Many streams at once (fleet board, workstreams, PR-to-green, plan-review panel, drift-aware mapping, adversarial review + ledger, non-self-review), Autonomous operation, Session hygiene, Acknowledgements. Most already have an authoritative source README compresses: status contract → `docs/status-contract.md`; BlitzOS → `docs/blitzos.md`; everything else (graph execution, conventions, autonomy, plan-format, oracle, adjudication) → `plugins/devflow/references/*.md`, the natural landing spot for split-out content.
- **Inbound links (repo-wide grep — preserve/redirect on split):** `README.md`→`docs/status-contract.md` (L7), `docs/blitzos.md` (L44); `references/conventions.md`→`docs/blitzos.md` ×2; `references/autonomy.md`→`../docs/status-contract.md`; `templates/journal.md`, `scripts/flow-fleet.py` mention `docs/blitzos.md` in code comments only; `docs/status-contract.md`→`docs/blitzos.md`. External: `.github/ISSUE_TEMPLATE/config.yml`→`…devflow#readme` (GitHub auto-anchor, not a section). No manifest description links README/docs. `skills/flow-status/SKILL.md` names README sections in prose only (not a link) — goes stale silently if they move.
- `validate-plugin.py` parses `READ_ONLY_ROLES`/`WRITE_ROLES` out of `flow-agent.py` by regex, not import — keep those literals regex-parseable.
- MIT licensed; NOTICE carries required upstream attributions — keep in sync with README § Acknowledgements.
