# DevFlow

Token-efficient spec-driven development for Claude Code and local Codex clients. Fresh-context subagents, wave-parallel execution, plan checking, independent diff review, goal-backward verification that abstains rather than guessing, and durable `.planning/` state. Claude invokes skills as `/flow-*`; Codex invokes the same skills as `$flow-*`.

## Install

### Claude Code

```
/plugin marketplace add jbrianfrancis-ir/devflow
/plugin install devflow@devflow
```

### Codex CLI, app, or IDE

```text
codex plugin marketplace add jbrianfrancis-ir/devflow
codex plugin add devflow@devflow
```

## Quick start

1. `/flow-new` — run it in the repo you want to work in (new or existing). It asks a bounded round of
   questions, then writes `.planning/` (`REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, `config.json`, …) on a
   new `flow/<slug>` feature branch.
2. `/flow-plan 1` — discusses the phase's open decisions, then writes and checks the phase's plans.
3. `/flow-execute 1` — runs the plans in dependency waves via executor subagents, then verifies the phase.
4. Repeat 2–3 for each phase. `/flow-status` at any point prints where you are and the exact next command.
5. `/flow-pr` once a phase is verified — pushes the branch and opens a pull request.

```
/flow-new ──► /flow-plan 1 ──► /flow-execute 1 ──► … all phases verified …
         ──► /flow-harden ──► /flow-pr ──► /flow-ci ──► (merge) ──► /flow-uat ──► human sign-off ──► /flow-release
```

What happens inside a phase — the wave graph, the smoke gate, state files: [docs/execution-model.md](docs/execution-model.md).

### Running it hands-off

Steps 2–4 are the loop, and you don't have to type each one. Every skill ends in a
machine-checkable `FLOW:` line, so Claude Code's `/goal` can drive the loop and stop on its own:

```
/goal FLOW says DONE, GATE, or BLOCKED, or stop after 40 turns
/flow-next
```

`/flow-next` advances exactly one step — plan, execute, replan gaps, or harden — and reports
`CONTINUE`, `GATE`, `BLOCKED`, or `DONE`. The goal keeps re-invoking it while the answer is
`CONTINUE`, and stops when the roadmap is finished or a decision needs you. `/loop /flow-next` does
the same at a background cadence.

It stops for you rather than guessing: opening a pull request, clearing a secret-scan hit, accepting
a knowingly-shipped defect, and every other human gate never auto-proceed. Set the turn cap to
something you're willing to spend. Full recipes, the loop rails that stop a run going nowhere, and
the complete gate list: [docs/autonomy.md](docs/autonomy.md).

## Commands

| Loop | Command | Does |
|------|---------|------|
| core | `/flow-new` | Initialize project (greenfield or existing repo) → requirements, roadmap, state |
| core | `/flow-migrate` | Convert a GSD project to DevFlow — history archived, context distilled, position preserved |
| core | `/flow-plan N` | Discuss decisions, optional research, write + check plans (`--auto`, `--gaps`, `--research`, `--panel`) |
| core | `/flow-execute N` | Run plans in parallel waves via executor subagents, then verify |
| core | `/flow-verify N` | Re-verify a phase; walk through batched human checks |
| auto | `/flow-next` | Advance exactly one step — the driver for `/goal` and `/loop` |
| ad-hoc | `/flow-quick <task>` | Small task with Flow guarantees, no ceremony |
| ad-hoc | `/flow-debug <symptom>` | Hypothesis-driven debugging with session-resumable state |
| ad-hoc | `/flow-oracle <question>` | Second opinion from an external model — curated context bundle, `--panel` cross-check, resumable consults |
| ad-hoc | `/flow-status` | Position + next command (`--all` for the fleet board, `--pause` to stop cleanly, `--reset-run` to re-arm the loop rails) |
| ad-hoc | `/flow-audit` | Read-only cross-artifact consistency check — coverage both ways, drift, open clarifications, principle conflicts |
| parallel | `/flow-workstream` | Run phases side by side — one git worktree per stream (`new`, `list`, `drop`) |
| ad-hoc | `/flow-todo <idea>` | Capture without derailing |
| memory | `/flow-map` | Codebase memory for planners/executors (`--docs`, `--refresh`) |
| design | `/flow-design` | Link + pull a Claude Design (claude.ai/design) design system as hard UI constraints (`--refresh`) |
| integrate | `/flow-pr` | Independent lens review of the outgoing diff, push to origin, open a PR (narrative recap + reviewer's guide) against upstream (`--adversarial` reviews through the peer provider and adjudicates into a ledger) |
| integrate | `/flow-ci` | Drive the open PR to green — watch checks, fix failures, answer bot review threads |
| deploy | `/flow-harden` | Production audit vs Aspire checklist; fix findings |
| deploy | `/flow-uat` | Deploy to UAT (provision on first deploy), generate acceptance test plan |
| deploy | `/flow-release` | Production deploy, gated on per-SHA UAT sign-off |

## Configuration

- `--provider native|claude|codex` on the delegating skills, and the project default `agents.provider` in
  `.planning/config.json` (`"agents": {"provider": "native"}`) — the flag wins over the file.
- Other keys `.planning/config.json` carries, named not explained: `mode`, `commit_docs`,
  `agents.models.<role>`, `autonomy.max_iterations`, `autonomy.max_repeats`, `autonomy.max_hours`,
  `git.base`, `git.origin`, `git.upstream`, `git.branch`, `deploy.tool`.
- Provider dispatch and model tiers: [docs/providers.md](docs/providers.md). Loop rails: [docs/autonomy.md](docs/autonomy.md).

## Documentation

Every topic page this README links out to — providers, execution model, autonomy, parallel work,
provenance, and more — is indexed at [docs/README.md](docs/README.md).

## License and acknowledgements

Concept lineage and upstream credit: [docs/acknowledgements.md](docs/acknowledgements.md). Required attributions are in `NOTICE`.

MIT licensed — see `LICENSE`.
