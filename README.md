# DevFlow

Token-efficient spec-driven development for Claude Code and local Codex clients. Fresh-context subagents, wave-parallel execution, plan checking, independent diff review, goal-backward verification that abstains rather than guessing, and durable `.planning/` state.

Claude invokes skills as `/flow-*`; Codex invokes the same skills as `$flow-*`.

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

## Flow

```
/flow-new ──► /flow-plan 1 ──► /flow-execute 1 ──► … all phases verified …
         ──► /flow-harden ──► /flow-pr ──► /flow-ci ──► (merge) ──► /flow-uat ──► human sign-off ──► /flow-release
```

## Acknowledgements

Concept lineage and upstream credit: [docs/acknowledgements.md](docs/acknowledgements.md). Required attributions are in `NOTICE`.

MIT licensed — see `LICENSE`.
