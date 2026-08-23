# Autonomy protocol

How Flow composes with Claude Code's `/goal` and `/loop`. Skills cannot start loops or set goals — `/goal` is a built-in CLI command, not something a skill can call — they emit transcript-verifiable status and behave predictably when driven.

The status line and `.planning/` file formats are a **public interface**, not an internal detail: outside sessions (a foreman session, a dashboard, a cron job, a context repo) observe and drive DevFlow through them rather than by reading terminal output. Full surface — file formats, the `flow-fleet.py --json` schema, exit codes, and what not to build against — in `docs/status-contract.md`.

## Status line
Every orchestrating skill ends its final message with exactly one line:

```
FLOW: <state> | <position> | next: <command>
```

States (the `/goal` evaluator matches these tokens):
- `CONTINUE` — more autonomous work is available; the next command can run without human input.
- `GATE` — human input required: checkpoint decision/human-action (incl. package legitimacy), a secret-scan hit, PR to upstream, sending an external consult bundle, UAT acceptance + sign-off, production confirmation, azd login. Include what's needed in `<position>`.
- `BLOCKED` — an error needs investigation before anything can proceed.
- `DONE` — roadmap fully verified (or released, after /flow-release; or fully verified with deploy N/A — see below).

Example: `FLOW: CONTINUE | phase 2/4 executed, verification pass | next: /flow-plan 3`

## Gate record — the question, not just the answer
A skill that emits `GATE` also writes the `## Gate` block in `STATE.md` (format in `templates/state.md`): `type`, `asked`, enumerated `options` with their consequences, `default`, and the plan/task when it is plan-scoped. Clear it to `none` the moment the gate is answered.

`<position>` is prose and stays prose — a human-readable clause, deliberately unparseable. The block is the machine-readable half, and it exists because a driver that can detect a gate but cannot learn the choices has to wake someone up to read a transcript. Now it can render the question and the options anywhere a human is.

**Structured is not auto-answerable.** A driver may surface options; it may never select one. Every gate below still requires a human, and the block changes only how legibly the question reaches them.

## Projects with no deployable surface
Not every project deploys. A library, a CLI, a marketplace plugin, a docs repo — the work is done when the roadmap is verified and merged; there is no UAT environment and no production to release to. For those, `.planning/config.json` records:

```json
"deploy": { "tool": null }
```

`null` is the signal, and it means exactly one thing: **this project has nothing to deploy.** Routing skips `/flow-harden`, `/flow-uat`, and `/flow-release` entirely, and a fully verified roadmap is terminal — `FLOW: DONE`, with no deploy pipeline to wait for.

Without it, a verified non-deploying project is unroutable: `/flow-next` rule 7 sends it to `/flow-harden`, which produces no `deploy/PIPELINE.md` because there is nothing to harden, so rule 7 matches again on the next iteration. Under `/loop` that burns hardening passes until the Repeats rail stops the run as `BLOCKED` — the rail reporting "no progress" about a routing bug rather than about work that is genuinely stuck, which is the one failure mode a rail must not manufacture.

**Fail-closed in the safe direction** (`conventions.md` → Fail-closed guards): only an explicit `null` skips the deploy chain. A missing `config.json`, an unreadable one, an absent `deploy` block, or any non-null tool all mean *this project deploys* — the default `/flow-new` writes is `"aspire+azd"`. Wrongly running a hardening pass costs a pass; wrongly skipping one ships unhardened code to production, so the ambiguous case takes the audit.

The human-readable "why" belongs in `PROJECT.md` as a `D-NN` decision. The config field is what routing reads; the decision entry is what a person reads six months later.

## Human gates — never auto-proceed, even in auto mode or under /goal//loop
Checkpoint `decision` and `human-action` tasks; failed-package verification; a fail-closed secret-scan hit (credential material in an outgoing diff — see `conventions.md`); sending a consult bundle to an external model (`/flow-oracle` — outward-facing, see `oracle.md`); UAT acceptance results and SIGNOFF.md; production release confirmation; opening a pull request to upstream; replying to or resolving a **human** reviewer's PR thread, and merging a PR (`/flow-ci` — driving checks to green is autonomous, review and merge are not); refuting a `blocking` review finding rather than fixing it, and shipping a `CONFIRMED` finding dispositioned `ACCEPTED AS-IS` — a known defect going out knowingly is a human's call, never a subagent's (`/flow-pr`, `adjudication.md`); removing a worktree with unmerged or unpushed commits (`/flow-workstream drop`); pushing tags; anything destructive in git. Also a hard rule (not a gate): never commit to the base branch (`dev`/`main`) — always a feature branch (see `conventions.md`).

Every gate in that list writes the `## Gate` block when it is raised, and **a `.planning/DECISIONS.md` entry when it is answered** — append-only, format in `templates/decisions.md`, created on first write. Record what was asked, what the human actually answered, the git identity that answered it, and the SHA at the time. Log the answer you were given, including a refusal or a modified approval: a log that only contains approvals is not a record, it is a highlight reel. Write the entry as part of the same commit as the work it authorized, so the approval and the change are one atomic fact in history.

Stopping at a gate and leaving no trace proves nothing later — the decision lived in a conversation that no longer exists, which is exactly the hole an auditor finds. A secret-scan hit is the one exception to verbatim detail: record file, line, and pattern class, never the matched value (`conventions.md`).

## Under /loop (dynamic mode)
After emitting the status line: `CONTINUE` → reschedule soon and keep going next iteration. `GATE`/`BLOCKED`/`DONE` → stop the loop (ScheduleWakeup `stop: true`) and state plainly why it stopped and what the human should do.

## Loop rails — the run has to be able to stop itself
`CONTINUE` means *the next command can run*, not *the run is getting anywhere*. A rule that keeps re-matching its own precondition — replanning gaps that replanning does not close is the usual one — emits `CONTINUE` forever, and a `/loop` will happily honor it all night. So the loop carries its own memory: `/flow-next` maintains the `## Run` block in `STATE.md` and checks three rails **before** doing any work.

- **Stuck** — build a `Signature` from what the routing actually matched (`rule<N>:phase<NN>:plans<d/t>:verif<status>`). Same as last iteration → `Repeats + 1`; different → `Repeats: 0`. At `Repeats >= max_repeats`: `FLOW: BLOCKED | no progress across {K} iterations at rule {N} | next: /flow-debug {what is not moving}`. Keep the signature human-readable — someone debugging a stuck run should learn why from the block alone.
- **Iterations** — at `Iteration >= max_iterations`: `FLOW: GATE | iteration cap {N} reached at {position} | next: raise autonomy.max_iterations, or take it manually`.
- **Time** — `max_hours` elapsed since `Started` (null = off): same `GATE` shape.

Then increment `Iteration`, write the block, and proceed. Reset the block when a gate is answered (a human has touched the run) or on `/flow-status --reset-run`.

**Fail-closed** (`conventions.md` → Fail-closed guards): an *absent* block is a legitimate cold start — iteration 1. A *malformed* one is `BLOCKED`, never silently reset to zero, because a counter that cannot be read is not a counter that says zero.

Tunable per project in `.planning/config.json` — defaults bind before a wasted night, not after:

```json
"autonomy": { "max_iterations": 40, "max_repeats": 3, "max_hours": null }
```

Rails belong to `/flow-next`. A human running `/flow-plan` or `/flow-execute` by hand is the rail.

## Suggested invocations (what skills print, users run)
- Drive to completion: `/goal FLOW says DONE, GATE, or BLOCKED, or stop after 40 turns` then `/flow-next`. **`BLOCKED` belongs in the condition**: it is as terminal as the other two, and a condition listing only DONE and GATE leaves a blocked run being retried by an evaluator waiting for a state it will never reach.
- Background cadence: `/loop /flow-next`
- Drive a PR to green: `/loop /flow-ci`
- Board every project (any session, no `.planning/` needed): `/flow-status --all`
- Watch a deployment: `/loop 15m curl the UAT health endpoints and report any change`
