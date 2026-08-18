# DevFlow

Token-efficient spec-driven development for Claude Code and local Codex clients. Fresh-context subagents, wave-parallel execution, plan checking, independent diff review, goal-backward verification that abstains rather than guessing, and durable `.planning/` state. 20 shared Agent Skills and 9 subagents across ~165KB of prompt content — but nothing loads it all: skills load progressively at ~1–5k tokens each, and heavy work runs in bounded native subagents or, when explicitly selected, through the other provider's authenticated CLI.

No Node runtime and no hooks. "Ship" is a real pipeline: harden → UAT → human sign-off → production, orchestrated with [Aspire](https://aspire.dev) + azd on Azure. Claude invokes skills as `/flow-*`; Codex invokes the same skills as `$flow-*`.

**Orchestrator-agnostic.** DevFlow runs as skills inside the interactive host rather than replacing it. Native subagents are the default. Cross-provider work is opt-in via `--provider claude|codex` or a saved project default, and uses `claude -p` or `codex exec` only for that bounded peer role. What DevFlow adds is *legibility*: every skill ends in a machine-checkable `FLOW:` line, all state lives in files, and `flow-status --all` boards every DevFlow project without screen-scraping. Contract: [`docs/status-contract.md`](docs/status-contract.md).

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

DevFlow's phase-loop discipline is derived in concept from [GSD Core](https://github.com/open-gsd/gsd-core) (MIT). It is an independent, ground-up reimplementation — no GSD source files are included; the behavioral contracts were rebuilt in a compressed, Claude-Code-only form. So is DevFlow's verification honesty: **exogenous abstention** on non-inferable truths (GSD's measurement — a verifier confidently false-passes a check it can't infer ~100% of the time, dropping to ~17% when routed on a tag applied at plan time, and only to ~67% when merely asked to be careful — is why `backstop_truths` is a structured field the planner sets rather than a judgment the verifier makes), the coincidental-reliance advisory, diff-scope conformance after execution, and the rule that a guard which could not run never reports success. See `NOTICE`.

The `/flow-oracle` consultation loop derives its concepts — context bundles, advisory panels, session lineage, detached runs, and the render-and-copy fallback — from [oracle](https://github.com/steipete/oracle) by Peter Steinberger (MIT), and drives the `oracle` CLI/MCP server directly when installed. No oracle source files are included.

The dependency-graph rules — the fake-edge test, hidden edges (shared mutable resources), fan-in guards against silent node failure, worker/verifier context separation, and frozen verification anchors — follow the graph-engineering framing articulated by Anatoli Kopadze (and the loops-to-graphs shift prompted by Peter Steinberger). Concepts only — no external source is included.

DevFlow's specification discipline comes in concept from [Spec Kit](https://github.com/github/spec-kit) (MIT): inline `[NEEDS CLARIFICATION]` markers instead of silent resolution, a recorded `## Assumptions` section, measurable technology-agnostic success criteria, and severity-rated cross-artifact analysis that reports rather than repairs. Its *constitution* became a `## Principles` section of `ARCHITECTURE.md` rather than a fourth governing file — with the rule that made it worth taking: a conflict is resolved by changing the work, never by reinterpreting the principle. Concepts only — no external source is included.

The multi-session shape — a fleet board over many repos instead of many terminal tabs, one worktree per stream, driving a PR to green before a human reads it, and an independent review crew whose findings are deduped, severity-classified, and refutable — was prompted by practitioners in [r/ClaudeCode's orchestrator thread](https://www.reddit.com/r/ClaudeCode/), whose "foreman and crew" setups (and the finding that decompose-and-fan-out underperforms one contained unit of work per session) shaped what DevFlow does and deliberately doesn't do. Concepts only — no external source is included.

The adjudication half of `/flow-pr --adversarial` — ruling findings on two axes rather than one, holding a refutation to the same evidence bar as the finding it answers, making a deferral cost an artifact that already exists, screening each round against durable settled ground, and keeping closed rounds immutable so a correction cites rather than overwrites — comes in concept from [adversarial-review-skills](https://github.com/Dzazaleo/adversarial-review-skills) by Dzazaleo (MIT). Its shape there is a four-session manual relay: a brief pasted into a rival AI, the reply pasted back, a separate session to adjudicate. DevFlow already had the transport — the cross-provider bridge dispatches a bounded read-only role to the peer CLI under an enforced sandbox — so what it takes is the *judgment* discipline, and what it drops is the copy-paste. Concepts only — no source is included, and the ~70KB of prompt content there is compressed to one reference and one template here.

The autonomous-run rails, the structured gate, the pre-code review panel, and the librarian pass were prompted by an [AgentOS blueprint](https://gist.github.com/iannuttall/8152098b5ce8e6c1a7499ee561ed93f4) — itself a reconstruction of a Danny Postma talk, not a primary source, and a spec for a hosted control plane (containers, an object-store MCP, a Kanban board, a push inbox) that DevFlow deliberately is not. What transferred was its policy layer: that an open-ended agent loop needs *spend, time, and stuck* rails as first-class product features rather than a cap the operator remembers to type; that the human interrupt channel should carry a question **and its choices** as data (`inbox.ask`) instead of prose; that a plan is worth reviewing by a panel before any code exists; and that something has to update the wiki from how the codebase actually works once the work lands. Each is rebuilt in DevFlow's own idiom — files and prompts, no runtime — and the thresholds are ours: a `/flow-next` iteration is a whole phase-step, so "stuck" is 3, not the blueprint's 19 LLM turns. Concepts only — no external source is included.

Several workflow rules also trace to Peter Steinberger's agent tooling: the pre-PR self-review ("autoreview") and narrative-recap PR bodies, the regression-test-per-bug-fix rule, and the dead-code-deletion default come from [agent-scripts](https://github.com/steipete/agent-scripts)/[agent-rules](https://github.com/steipete/agent-rules); the UAT route sweep with console/network evidence and readiness-over-sleeps come from [sweetlink](https://github.com/steipete/sweetlink); researcher/mapper doc distillation optionally drives the [summarize](https://github.com/steipete/summarize) CLI when installed. Concepts only — no source files from any of these are included.

MIT licensed — see `LICENSE`.
