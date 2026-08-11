# DevFlow

Token-efficient spec-driven development for Claude Code. Fresh-context subagents, wave-parallel execution, plan checking, independent diff review, goal-backward verification, and durable `.planning/` state. 19 commands and 9 subagents across ~130KB of prompt content — but nothing loads it all: each command pulls ~1–5k tokens and the heavy work runs in subagents. Commands use the `/flow-*` prefix.

Claude Code only. No installer, no Node runtime, no hooks. "Ship" is a real pipeline: harden → UAT → human sign-off → production, orchestrated with [Aspire](https://aspire.dev) + azd on Azure.

**Orchestrator-agnostic.** DevFlow is a crew member, not a multiplexer — it runs inside whatever you already use (tmux, [herdr](https://herdr.dev), cmux, Orca, Superset, Conductor, the desktop app, or plain terminal tabs) and doesn't compete with any of them. It is skills in a normal interactive session: no `claude -p`, no headless spawning, no Agent SDK pool — usage stays on your subscription. What it adds is *legibility*: every skill ends in a machine-checkable `FLOW:` line, all state lives in files, and `/flow-status --all` boards every DevFlow project on the machine. Any outside session — a "foreman", a dashboard, a cron job — can observe and drive it without screen-scraping. Contract: [`docs/status-contract.md`](docs/status-contract.md).

## Install

```
/plugin marketplace add jbrianfrancis-ir/devflow
/plugin install devflow@devflow
```

DevFlow projects are **self-bootstrapping**: `/flow-new` and `/flow-migrate` write a `.claude/settings.json` declaring this marketplace + plugin, so any session opening the repo — including Claude Code on the web, where fresh containers don't carry your locally installed plugins — installs DevFlow at session start (desktop shows a one-time trust prompt).

**Context repos (BlitzOS-style)**: DevFlow projects slot into [BlitzOS](https://github.com/blitzdotdev/blitzos)-style context repos — thin private repos that let cloud agents boot already knowing your repos and their state. Detection, company-brain rendering, `FLOW:` status parsing, session-record mapping, and the bootstrap contract are specified in [`docs/blitzos.md`](docs/blitzos.md).

## Commands

| Loop | Command | Does |
|------|---------|------|
| core | `/flow-new` | Initialize project (greenfield or existing repo) → requirements, roadmap, state |
| core | `/flow-migrate` | Convert a GSD project to DevFlow — history archived, context distilled, position preserved |
| core | `/flow-plan N` | Discuss decisions, optional research, write + check plans (`--auto`, `--gaps`, `--research`) |
| core | `/flow-execute N` | Run plans in parallel waves via executor subagents, then verify |
| core | `/flow-verify N` | Re-verify a phase; walk through batched human checks |
| auto | `/flow-next` | Advance exactly one step — the driver for `/goal` and `/loop` |
| ad-hoc | `/flow-quick <task>` | Small task with Flow guarantees, no ceremony |
| ad-hoc | `/flow-debug <symptom>` | Hypothesis-driven debugging with session-resumable state |
| ad-hoc | `/flow-oracle <question>` | Second opinion from an external model — curated context bundle, `--panel` cross-check, resumable consults |
| ad-hoc | `/flow-status` | Position + next command (`--all` for the fleet board, `--pause` to stop cleanly) |
| parallel | `/flow-workstream` | Run phases side by side — one git worktree per stream (`new`, `list`, `drop`) |
| ad-hoc | `/flow-todo <idea>` | Capture without derailing |
| memory | `/flow-map` | Codebase memory for planners/executors (`--docs`, `--refresh`) |
| design | `/flow-design` | Link + pull a Claude Design (claude.ai/design) design system as hard UI constraints (`--refresh`) |
| integrate | `/flow-pr` | Independent lens review of the outgoing diff, push to origin, open a PR (narrative recap + reviewer's guide) against upstream |
| integrate | `/flow-ci` | Drive the open PR to green — watch checks, fix failures, answer bot review threads |
| deploy | `/flow-harden` | Production audit vs Aspire checklist; fix findings |
| deploy | `/flow-uat` | Deploy to UAT (provision on first deploy), generate acceptance test plan |
| deploy | `/flow-release` | Production deploy, gated on per-SHA UAT sign-off |

## Flow

```
/flow-new ──► /flow-plan 1 ──► /flow-execute 1 ──► … all phases verified …
         ──► /flow-harden ──► /flow-pr ──► /flow-ci ──► (merge) ──► /flow-uat ──► human sign-off ──► /flow-release
```

**Graph execution** (`references/plan-format.md`): a phase's plans form a dependency graph — plans are nodes, `depends_on` edges exist only where one plan consumes another's output (the *fake-edge test*), and waves are the graph's parallel layers. Same-wave plans share no files and no mutable resources (a shared migration chain or lockfile is a *hidden edge*). `/flow-execute` fans out one fresh-context executor per plan per wave; a *fan-in guard* counts results against spawns so a dead executor can't slip silently into a "complete" phase; and a fresh-context verifier — never the executors that did the work — proves the phase's `must_haves` against *anchors*: commands actually run, tests actually passed, code traced. must_haves freeze at execution start; gaps close by changing code, never by weakening a truth.

State lives in `.planning/` (hard size caps, sections overwritten not appended — see `templates/`). Every skill reads `STATE.md` first, so any session resumes cold. `JOURNAL.md` keeps a capped, newest-first one-line history of skill runs — warm starts, audit trail, and the lines context repos index.

**Conventions** (`references/conventions.md`): code lives under `src/` and tests under `tests/` off the repo root, and every change flows through git the same way — a feature branch off `dev` (or `main`), commits pushed to `origin`, integrated by pull request against `upstream` (or the base branch when there's no separate upstream). Deploy runs from merged base code. A **fail-closed secret scan** guards every commit and push (a hit is a human gate — the value is never echoed), and `ARCHITECTURE.md` carries a names-only **Environment manifest** (env vars/parameters + provisioning source; `.env` files are never opened) that `/flow-harden` audits against the code. Aspire updates within the current major apply automatically; a major bump (e.g. 13→14) needs approval. `ARCHITECTURE.md` can override the layout; the git workflow always applies.

**Architecture constraints**: `.planning/ARCHITECTURE.md` (created by `/flow-new`, or write it yourself from `templates/architecture.md`) pins your exact stack — runtime, frameworks, and library versions, patterns, Azure/Aspire resources, forbidden items. Planner, plan-checker, executor, and researcher treat it as law: plans pin the listed versions, nothing gets substituted or upgraded silently, and anything outside it surfaces as a decision checkpoint. `/flow-harden` audits for drift between the pins and reality.

**Second opinions** (`/flow-oracle`): when you're stuck or facing a high-stakes decision, ask an external frontier model — concepts from [steipete/oracle](https://github.com/steipete/oracle). The skill packs the question + only the files that change the answer into a context bundle, runs it through the best available engine (the `oracle` CLI or MCP server when installed; otherwise a render-and-copy bundle you paste into any chat UI — no install required), and distills the reply into a ≤10-line advisory verdict. `--panel` cross-checks 2–3 models; `--followup` chains onto a prior consult's session. Consults persist in `.planning/consults/` (resumable, with lineage), and DevFlow's rules still apply: the fail-closed secret scan runs over every outbound bundle, every send is a human gate, and advice conflicting with ARCHITECTURE.md pins surfaces as a decision checkpoint — never adopted silently. `/flow-debug` (when hypotheses run dry), `/flow-plan` (checker escalation), and `/flow-harden` (ambiguous findings) offer it at their stuck points.

**Design constraints**: `/flow-design` links a [Claude Design](https://claude.ai/design) design-system project up front (offered during `/flow-new` for UI projects), pulls it into `design-system/`, and distills tokens + component inventory into `.planning/DESIGN.md`. UI plans must name the component and its local spec path; executors read the spec before building; invented styles and one-off components are verification gaps. Missing components route back to the design system via a decision checkpoint, then `/flow-design --refresh`.

## Many streams at once

The bottleneck in agent-assisted work isn't decomposition — it's losing track of what each session is doing, and reading its output cold at the end. Four pieces address that:

**Fleet board** — `/flow-status --all` runs `scripts/flow-fleet.py`, which walks your roots for `.planning/STATE.md` and prints one row per project: phase, status, last `FLOW:` state, age, dirty/stale/on-base flags, and the exact next command. It reads files, never screens, so it works under every multiplexer and survives their updates. Attention-first ordering, a "needs a human" footer with copy-pasteable `cd … && /flow-…` lines, `--json` for programmatic drivers, and exit status `1` when anything needs you. Configure roots once in `~/.devflow/fleet.json`: `{"roots": ["~/dev"], "stale_days": 3}`.

**Workstreams** — `/flow-workstream new <slug>` cuts a git worktree on its own `flow/<slug>` branch so two phases run side by side without fighting over one checkout. It refuses streams that share a hidden edge (migration chain, lockfile, generated output, shared dev database), assigns a port offset so both apps can run, and names the untracked local files the new tree lacks. `.planning/` reconciliation at merge is specified in `references/conventions.md` → Parallel workstreams: `STATE.md`/`config.json` are branch-local, `JOURNAL.md`/`LEARNINGS.md` merge as unions, `ARCHITECTURE.md` and the other pins are single-writer.

**PR to green** — `/flow-ci` takes the PR from opened to mergeable: polls checks, pulls the real failure logs, classifies each failure as caused-by-this-branch / pre-existing-on-base / flake / needs-a-decision, fixes what's its own (with a regression test), and triages bot review threads into fix / refute / defer — replying and resolving each. It never disables a check to get green, never force-pushes, never merges, and never answers a human reviewer. Built for `/loop /flow-ci`.

**Review that isn't self-review** — `/flow-pr` no longer grades its own homework. It spawns parallel fresh-context `flow-reviewer` agents, one per lens (correctness, security, architecture, conventions, reuse, tests, design), selected from what the diff actually touches; findings are deduped across lenses and classified `blocking` / `should-fix` / `nit`, where blocking demands a concrete failure scenario. Findings can be **refuted** with a written reason rather than reflexively obeyed — but refuting a blocking finding is a human gate. The PR body then carries a **Review guide**: the 2–4 files to read first ranked by blast radius, which `must_haves` were proven by a command versus by a code trace, where verification was thin, and every deviation — so a reviewer never meets the diff cold.

## Autonomous operation

Every skill ends with a machine-checkable status line — `FLOW: CONTINUE|GATE|BLOCKED|DONE | position | next: command` — which Claude Code's `/goal` evaluator can verify from the transcript. Recipes:

- **Drive to completion** (primary): `/goal FLOW says DONE or GATE, or stop after 40 turns` then `/flow-next`. Claude keeps advancing phase by phase, turn after turn, stopping when done or when a human is needed.
- **Background cadence**: `/loop /flow-next` — one step per iteration, self-paced; the loop stops itself on GATE/BLOCKED/DONE.
- **Drive a PR to green**: `/loop /flow-ci` — checks watched, failures fixed, bot threads answered; stops when it's green or a human is needed.
- **Sweep the fleet**: `/flow-status --all` in any session (no `.planning/` required) — every project, attention first.
- **Watch a deployment**: `/loop 15m curl the UAT health endpoints and report any change`.

Human gates that never auto-proceed: checkpoint decisions/human-actions (incl. package legitimacy), secret-scan hits, external consult sends, PRs to upstream, replies to human PR reviewers and merges, refuting a blocking review finding, dropping a worktree with unmerged work, UAT acceptance + sign-off, production confirmation, tag pushes. Cost note: `/goal` turns and `/loop` iterations accumulate context in one session — small STATE.md and one-step-per-turn keep each cheap, but start a fresh session for each milestone-sized run.

## Session hygiene (`/clear`)

Unlike GSD, DevFlow does **not** need a `/clear` between every step. Each command loads ~1–5k tokens (not 20–26k), the heavy work runs in fresh-context subagents, and all state persists in `.planning/` — so a fresh session resumes cold (every skill reads `STATE.md` first). Clearing is a cheap convenience, not a requirement.

- **Driving manually**: `/clear` at phase boundaries, or when `/context` looks heavy — not between plan → execute → verify of the same phase. After a clear, run `/flow-status` to re-orient (or just run the next `/flow-` command; they self-orient).
- **Autonomous (`/goal`, `/loop`)**: do **not** `/clear` mid-run — it kills the goal/loop and its accumulated context. Let it reach a `GATE`/`DONE`, then `/clear` and start the next run. One autonomous run ≈ one phase or milestone.

## Acknowledgements

DevFlow's phase-loop discipline is derived in concept from [GSD Core](https://github.com/open-gsd/gsd-core) (MIT). It is an independent, ground-up reimplementation — no GSD source files are included; the behavioral contracts were rebuilt in a compressed, Claude-Code-only form. So is DevFlow's verification honesty: **exogenous abstention** on non-inferable truths (GSD's measurement — a verifier confidently false-passes a check it can't infer ~100% of the time, dropping to ~17% when routed on a tag applied at plan time, and only to ~67% when merely asked to be careful — is why `backstop_truths` is a structured field the planner sets rather than a judgment the verifier makes), the coincidental-reliance advisory, diff-scope conformance after execution, and the rule that a guard which could not run never reports success. See `NOTICE`.

The `/flow-oracle` consultation loop derives its concepts — context bundles, advisory panels, session lineage, detached runs, and the render-and-copy fallback — from [oracle](https://github.com/steipete/oracle) by Peter Steinberger (MIT), and drives the `oracle` CLI/MCP server directly when installed. No oracle source files are included.

The dependency-graph rules — the fake-edge test, hidden edges (shared mutable resources), fan-in guards against silent node failure, worker/verifier context separation, and frozen verification anchors — follow the graph-engineering framing articulated by Anatoli Kopadze (and the loops-to-graphs shift prompted by Peter Steinberger). Concepts only — no external source is included.

The multi-session shape — a fleet board over many repos instead of many terminal tabs, one worktree per stream, driving a PR to green before a human reads it, and an independent review crew whose findings are deduped, severity-classified, and refutable — was prompted by practitioners in [r/ClaudeCode's orchestrator thread](https://www.reddit.com/r/ClaudeCode/), whose "foreman and crew" setups (and the finding that decompose-and-fan-out underperforms one contained unit of work per session) shaped what DevFlow does and deliberately doesn't do. Concepts only — no external source is included.

Several workflow rules also trace to Peter Steinberger's agent tooling: the pre-PR self-review ("autoreview") and narrative-recap PR bodies, the regression-test-per-bug-fix rule, and the dead-code-deletion default come from [agent-scripts](https://github.com/steipete/agent-scripts)/[agent-rules](https://github.com/steipete/agent-rules); the UAT route sweep with console/network evidence and readiness-over-sleeps come from [sweetlink](https://github.com/steipete/sweetlink); researcher/mapper doc distillation optionally drives the [summarize](https://github.com/steipete/summarize) CLI when installed. Concepts only — no source files from any of these are included.

MIT licensed — see `LICENSE`.
