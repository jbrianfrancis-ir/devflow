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

Start a new Codex thread after installation and invoke skills with `$flow-new`,
`$flow-plan`, `$flow-execute`, and the other `$flow-*` names. Codex cloud is not
part of the initial support contract.

### Provider selection

Native workers are used unless a delegating skill receives
`--provider claude|codex`. A project can save the same choice as
`"agents": {"provider": "native|claude|codex"}` in `.planning/config.json`;
the command flag wins. Cross-provider use requires both CLIs installed and
authenticated, authorizes the bounded repository context to be sent to that
provider, and preserves all Flow checkpoints, branch rules, and secret scans.

### Model tiers

Each role declares its own model, so cost is a property of the plugin rather than something you have to remember to ask for. Judgment roles — planner, plan-checker, verifier, reviewer, consultant, migrator — run on the top tier; bounded roles — mapper, researcher, and the high-volume **executor** — run a tier down. The executor is deliberately cheap: a DevFlow plan is a complete, unambiguous executor prompt by design, which is what makes that safe. Override per role with `"agents": {"models": {"executor": "opus"}}` in `.planning/config.json`.

Claude projects remain **self-bootstrapping**: `/flow-new` and `/flow-migrate` merge a `.claude/settings.json` declaration so fresh Claude sessions install DevFlow. Codex v1 uses the user-installed marketplace above and does not mutate user configuration from a project skill. Both also write `CLAUDE.md` and `AGENTS.md` pointer files at the repo root — marker-merged, never overwriting your content — so a session that never runs a `flow-*` skill still finds `.planning/`. They point at the artifacts rather than restating them; a copy of your constraints in an auto-loaded file goes stale and does more damage than no file at all.

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
| ad-hoc | `/flow-audit` | Read-only cross-artifact consistency check — coverage both ways, drift, open clarifications, principle conflicts |
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

**Graph execution** (`plugins/devflow/references/plan-format.md`): a phase's plans form a dependency graph — plans are nodes, `depends_on` edges exist only where one plan consumes another's output (the *fake-edge test*), and waves are the graph's parallel layers. Same-wave plans share no files and no mutable resources (a shared migration chain or lockfile is a *hidden edge*). `/flow-execute` fans out one fresh-context executor per plan per wave; a *fan-in guard* counts results against spawns so a dead executor can't slip silently into a "complete" phase; and a fresh-context verifier — never the executors that did the work — proves the phase's `must_haves` against *anchors*: commands actually run, tests actually passed, code traced. must_haves freeze at execution start; gaps close by changing code, never by weakening a truth.

**Smoke gate**: per-phase truths only prove *this* phase, which is exactly how phase 5 silently breaks phase 2. So every phase also has to clear one end-to-end check — the command declared in `ARCHITECTURE.md` → `## Smoke`, run verbatim and judged against its stated pass condition. A failure is a gap even when every phase truth verified, and it's flagged as pointing at earlier work when the evidence says so, so replanning targets the right phase. Undeclared, it becomes a standing human check — the verifier never invents a smoke command and never quietly skips the gate.

State lives in `.planning/` (hard size caps, sections overwritten not appended — see `plugins/devflow/templates/`). Every skill reads `STATE.md` first, so any session resumes cold. `JOURNAL.md` keeps a capped, newest-first one-line history of skill runs — warm starts, audit trail, and the lines context repos index.

**Conventions** (`plugins/devflow/references/conventions.md`): code lives under `src/` and tests under `tests/` off the repo root, and every change flows through git the same way — a feature branch off `dev` (or `main`), commits pushed to `origin`, integrated by pull request against `upstream` (or the base branch when there's no separate upstream). Deploy runs from merged base code. A **fail-closed secret scan** guards every commit and push (a hit is a human gate — the value is never echoed), and `ARCHITECTURE.md` carries a names-only **Environment manifest** (env vars/parameters + provisioning source; `.env` files are never opened) that `/flow-harden` audits against the code. Aspire updates within the current major apply automatically; a major bump (e.g. 13→14) needs approval. `ARCHITECTURE.md` can override the layout; the git workflow always applies.

**Architecture constraints**: `.planning/ARCHITECTURE.md` (created by `/flow-new`, or write it yourself from `plugins/devflow/templates/architecture.md`) pins your exact stack — runtime, frameworks, and library versions, patterns, Azure/Aspire resources, forbidden items. Planner, plan-checker, executor, and researcher treat it as law: plans pin the listed versions, nothing gets substituted or upgraded silently, and anything outside it surfaces as a decision checkpoint. `/flow-harden` audits for drift between the pins and reality.

**Second opinions** (`/flow-oracle`): when you're stuck or facing a high-stakes decision, ask an external frontier model — concepts from [steipete/oracle](https://github.com/steipete/oracle). The skill packs the question + only the files that change the answer into a context bundle, runs it through the best available engine (the `oracle` CLI or MCP server when installed; otherwise a render-and-copy bundle you paste into any chat UI — no install required), and distills the reply into a ≤10-line advisory verdict. `--panel` cross-checks 2–3 models; `--followup` chains onto a prior consult's session. Consults persist in `.planning/consults/` (resumable, with lineage), and DevFlow's rules still apply: the fail-closed secret scan runs over every outbound bundle, every send is a human gate, and advice conflicting with ARCHITECTURE.md pins surfaces as a decision checkpoint — never adopted silently. `/flow-debug` (when hypotheses run dry), `/flow-plan` (checker escalation), and `/flow-harden` (ambiguous findings) offer it at their stuck points.

**Design constraints**: `/flow-design` links a [Claude Design](https://claude.ai/design) design-system project up front (offered during `/flow-new` for UI projects), pulls it into `design-system/`, and distills tokens + component inventory into `.planning/DESIGN.md`. UI plans must name the component and its local spec path; executors read the spec before building; invented styles and one-off components are verification gaps. Missing components route back to the design system via a decision checkpoint, then `/flow-design --refresh`.

## Saying "unknown" out loud

An agent asked to write requirements will write confident sentences, because that is what requirements look like. The gap between what the user actually settled and what the document asserts is where silent wrong decisions come from, and DevFlow now refuses to close that gap by guessing.

**`[NEEDS CLARIFICATION: …]`** markers sit inline in `REQUIREMENTS.md` wherever an unsettled choice would change what gets built (`- REQ-03: authenticates users via [NEEDS CLARIFICATION: email/password, SSO, or OAuth?]`). `/flow-plan` asks about the markers its phase touches, before anything it newly noticed; answering one resolves it in place as a D-NN decision. Any still open when the phase is planned become `must_haves.backstop_truths`, and the verifier abstains rather than certifying whichever behavior got built. That is one chain from *the spec didn't say* to *nobody claimed it was right* — with a human asked at each cheap moment along the way.

Two companions in the same file. **`## Assumptions`** records the defaults chosen where the description was silent — written down they're reviewable, unwritten they're landmines; an assumption too load-bearing to be wrong is a requirement or a marker instead. **`SC-NN` success criteria** are measurable and technology-agnostic ("p95 under 400ms at 500 concurrent users", "90% finish onboarding unaided") — the only place a performance, scale, or UX threshold can live. `/flow-harden` audits them before deploy (a number nothing measures is a finding; a human-judged one is deferred, never dropped) and `/flow-uat` writes an acceptance case per criterion, threshold included, since "felt fast" is not a result.

**`/flow-audit`** checks the artifacts against each other, read-only and severity-rated: coverage in *both* directions (a plan tracing to no requirement is work nobody asked for), status drift where disk disagrees with ROADMAP or STATE, markers still open on already-executed work, acceptance resting on unmeasurable adjectives, and conflicts with `ARCHITECTURE.md`'s **`## Principles`** — the project's own practice law, where a conflict is resolved by changing the plan, never by reinterpreting the principle.

## Many streams at once

The bottleneck in agent-assisted work isn't decomposition — it's losing track of what each session is doing, and reading its output cold at the end. Four pieces address that:

**Fleet board** — `/flow-status --all` runs `plugins/devflow/scripts/flow-fleet.py`, which walks your roots for `.planning/STATE.md` and prints one row per project: phase, status, last `FLOW:` state, age, dirty/stale/on-base flags, and the exact next command. It reads files, never screens, so it works under every multiplexer and survives their updates. Attention-first ordering, a "needs a human" footer with copy-pasteable `cd … && /flow-…` lines, `--json` for programmatic drivers, and exit status `1` when anything needs you. Configure roots once in `~/.devflow/fleet.json`: `{"roots": ["~/dev"], "stale_days": 3}`.

**Workstreams** — `/flow-workstream new <slug>` cuts a git worktree on its own `flow/<slug>` branch so two phases run side by side without fighting over one checkout. It refuses streams that share a hidden edge (migration chain, lockfile, generated output, shared dev database), assigns a port offset so both apps can run, and names the untracked local files the new tree lacks. `.planning/` reconciliation at merge is specified in `plugins/devflow/references/conventions.md` → Parallel workstreams: `STATE.md`/`config.json` are branch-local, `JOURNAL.md`/`LEARNINGS.md` merge as unions, `ARCHITECTURE.md` and the other pins are single-writer.

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

DevFlow's specification discipline comes in concept from [Spec Kit](https://github.com/github/spec-kit) (MIT): inline `[NEEDS CLARIFICATION]` markers instead of silent resolution, a recorded `## Assumptions` section, measurable technology-agnostic success criteria, and severity-rated cross-artifact analysis that reports rather than repairs. Its *constitution* became a `## Principles` section of `ARCHITECTURE.md` rather than a fourth governing file — with the rule that made it worth taking: a conflict is resolved by changing the work, never by reinterpreting the principle. Concepts only — no external source is included.

The multi-session shape — a fleet board over many repos instead of many terminal tabs, one worktree per stream, driving a PR to green before a human reads it, and an independent review crew whose findings are deduped, severity-classified, and refutable — was prompted by practitioners in [r/ClaudeCode's orchestrator thread](https://www.reddit.com/r/ClaudeCode/), whose "foreman and crew" setups (and the finding that decompose-and-fan-out underperforms one contained unit of work per session) shaped what DevFlow does and deliberately doesn't do. Concepts only — no external source is included.

Several workflow rules also trace to Peter Steinberger's agent tooling: the pre-PR self-review ("autoreview") and narrative-recap PR bodies, the regression-test-per-bug-fix rule, and the dead-code-deletion default come from [agent-scripts](https://github.com/steipete/agent-scripts)/[agent-rules](https://github.com/steipete/agent-rules); the UAT route sweep with console/network evidence and readiness-over-sleeps come from [sweetlink](https://github.com/steipete/sweetlink); researcher/mapper doc distillation optionally drives the [summarize](https://github.com/steipete/summarize) CLI when installed. Concepts only — no source files from any of these are included.

MIT licensed — see `LICENSE`.
