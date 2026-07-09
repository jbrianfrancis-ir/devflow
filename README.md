# DevFlow

Token-efficient spec-driven development for Claude Code. Fresh-context subagents, wave-parallel execution, plan checking, goal-backward verification, and durable `.planning/` state — at ~70KB of prompt content (each command loads ~1–5k tokens). Commands use the `/flow-*` prefix.

Claude Code only. No installer, no Node runtime, no hooks. "Ship" is a real pipeline: harden → UAT → human sign-off → production, orchestrated with [Aspire](https://aspire.dev) + azd on Azure.

## Install

```
/plugin marketplace add jbrianfrancis-ir/devflow
/plugin install devflow@devflow
```

## Commands

| Loop | Command | Does |
|------|---------|------|
| core | `/flow-new` | Initialize project (greenfield or existing repo) → requirements, roadmap, state |
| core | `/flow-plan N` | Discuss decisions, optional research, write + check plans (`--auto`, `--gaps`, `--research`) |
| core | `/flow-execute N` | Run plans in parallel waves via executor subagents, then verify |
| core | `/flow-verify N` | Re-verify a phase; walk through batched human checks |
| auto | `/flow-next` | Advance exactly one step — the driver for `/goal` and `/loop` |
| ad-hoc | `/flow-quick <task>` | Small task with Flow guarantees, no ceremony |
| ad-hoc | `/flow-debug <symptom>` | Hypothesis-driven debugging with session-resumable state |
| ad-hoc | `/flow-status` | Position + next command (`--pause` to stop cleanly) |
| ad-hoc | `/flow-todo <idea>` | Capture without derailing |
| memory | `/flow-map` | Codebase memory for planners/executors (`--docs`, `--refresh`) |
| design | `/flow-design` | Link + pull a Claude Design (claude.ai/design) design system as hard UI constraints (`--refresh`) |
| integrate | `/flow-pr` | Push the feature branch to origin and open a PR against upstream |
| deploy | `/flow-harden` | Production audit vs Aspire checklist; fix findings |
| deploy | `/flow-uat` | Deploy to UAT (provision on first deploy), generate acceptance test plan |
| deploy | `/flow-release` | Production deploy, gated on per-SHA UAT sign-off |

## Flow

```
/flow-new ──► /flow-plan 1 ──► /flow-execute 1 ──► … all phases verified …
         ──► /flow-harden ──► /flow-pr ──► (merge) ──► /flow-uat ──► human sign-off ──► /flow-release
```

State lives in `.planning/` (hard size caps, sections overwritten not appended — see `templates/`). Every skill reads `STATE.md` first, so any session resumes cold.

**Conventions** (`references/conventions.md`): code lives under `src/` off the repo root, and every change flows through git the same way — a feature branch off `dev` (or `main`), commits pushed to `origin`, integrated by pull request against `upstream` (or the base branch when there's no separate upstream). Deploy runs from merged base code. `ARCHITECTURE.md` can override the layout; the git workflow always applies.

**Architecture constraints**: `.planning/ARCHITECTURE.md` (created by `/flow-new`, or write it yourself from `templates/architecture.md`) pins your exact stack — runtime, frameworks, and library versions, patterns, Azure/Aspire resources, forbidden items. Planner, plan-checker, executor, and researcher treat it as law: plans pin the listed versions, nothing gets substituted or upgraded silently, and anything outside it surfaces as a decision checkpoint. `/flow-harden` audits for drift between the pins and reality.

**Design constraints**: `/flow-design` links a [Claude Design](https://claude.ai/design) design-system project up front (offered during `/flow-new` for UI projects), pulls it into `design-system/`, and distills tokens + component inventory into `.planning/DESIGN.md`. UI plans must name the component and its local spec path; executors read the spec before building; invented styles and one-off components are verification gaps. Missing components route back to the design system via a decision checkpoint, then `/flow-design --refresh`.

## Autonomous operation

Every skill ends with a machine-checkable status line — `FLOW: CONTINUE|GATE|BLOCKED|DONE | position | next: command` — which Claude Code's `/goal` evaluator can verify from the transcript. Recipes:

- **Drive to completion** (primary): `/goal FLOW says DONE or GATE, or stop after 40 turns` then `/flow-next`. Claude keeps advancing phase by phase, turn after turn, stopping when done or when a human is needed.
- **Background cadence**: `/loop /flow-next` — one step per iteration, self-paced; the loop stops itself on GATE/BLOCKED/DONE.
- **Watch a deployment**: `/loop 15m curl the UAT health endpoints and report any change`.

Human gates that never auto-proceed: checkpoint decisions/human-actions (incl. package legitimacy), PRs to upstream, UAT acceptance + sign-off, production confirmation, tag pushes. Cost note: `/goal` turns and `/loop` iterations accumulate context in one session — small STATE.md and one-step-per-turn keep each cheap, but start a fresh session for each milestone-sized run.

## Acknowledgements

DevFlow's phase-loop discipline is derived in concept from [GSD Core](https://github.com/open-gsd/gsd-core) (MIT). It is an independent, ground-up reimplementation — no GSD source files are included; the behavioral contracts were rebuilt in a compressed, Claude-Code-only form. See `NOTICE`.

MIT licensed — see `LICENSE`.
