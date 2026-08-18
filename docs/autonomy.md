# Autonomous operation

Every skill ends its final message with a machine-checkable status line —
`FLOW: CONTINUE|GATE|BLOCKED|DONE | position | next: command` — which Claude Code's `/goal` evaluator
can verify from the transcript, and which `/loop` and `/flow-status --all` read the same way. Example:
`FLOW: CONTINUE | phase 2/4 executed, verification pass | next: /flow-plan 3`. The full state grammar
is specified in [`autonomy.md`](../plugins/devflow/references/autonomy.md).

## Recipes
- **Drive to completion** (primary): `/goal FLOW says DONE or GATE, or stop after 40 turns` then `/flow-next`. Claude keeps advancing phase by phase, turn after turn, stopping when done or when a human is needed.
- **Background cadence**: `/loop /flow-next` — one step per iteration, self-paced; the loop stops itself on GATE/BLOCKED/DONE.
- **Drive a PR to green**: `/loop /flow-ci` — checks watched, failures fixed, bot threads answered; stops when it's green or a human is needed.
- **Sweep the fleet**: `/flow-status --all` in any session (no `.planning/` required) — every project, attention first.
- **Watch a deployment**: `/loop 15m curl the UAT health endpoints and report any change`.

## Loop rails
`CONTINUE` has always meant *the next command can run* — not *the run is getting anywhere*. A rule
that keeps re-matching its own precondition (replanning gaps that replanning doesn't close is the
usual one) emits `CONTINUE` forever, and a `/loop` will honor it all night. So `/flow-next` carries the
loop's only cross-iteration memory, a `## Run` block in `STATE.md`, and checks three rails before doing
any work: a **stuck** detector on a signature of what the routing actually matched (unchanged for
`max_repeats` iterations → `BLOCKED`, not another lap), an **iteration** cap, and an optional
**wall-clock** cap. Tune per project with `"autonomy": {"max_iterations": 40, "max_repeats": 3,
"max_hours": null}` in `.planning/config.json`. An absent block is a cold start; a *malformed* one is
`BLOCKED`, never read as zero — a counter that can't be read is not a counter that says zero. Full rail
semantics and the stuck-signature format: [`autonomy.md`](../plugins/devflow/references/autonomy.md).

## Gates you can answer from anywhere
`FLOW: GATE | <position>` tells a driver that a human is needed, but position alone never said *what
was being asked* or *what the choices were*, and the contract forbids parsing skill prose to find out.
So every gate also writes a `## Gate` block — `type`, `asked`, enumerated `options` with their
consequences, `default` — the one structured exception to that rule. `flow-status --all` prints the
question and its options in the "needs a human" footer, `--json` exposes them as data, and `asked` is
the same string that lands in `DECISIONS.md` when the gate is answered, so question and answer join on
it. A driver may surface options; it may never pick one.

## Human gates that never auto-proceed
A fixed list of gates never auto-proceeds, even under `/goal` or `/loop` — they span checkpoint decisions, secret-scan hits, anything outward-facing, and anything destructive in git. Enumerating them here would go stale the moment the list changes, and it already had. The authoritative gate list and gate-record
fields are specified in [`autonomy.md`](../plugins/devflow/references/autonomy.md); checkpoint types
(decision / human-action / human-verify) in
[`checkpoints.md`](../plugins/devflow/references/checkpoints.md).

## Session hygiene (`/clear`)
Unlike GSD, DevFlow does **not** need a `/clear` between every step. Each command loads ~1–5k tokens
(not 20–26k), the heavy work runs in fresh-context subagents, and all state persists in `.planning/` —
so a fresh session resumes cold (every skill reads `STATE.md` first). Clearing is a cheap convenience,
not a requirement.

- **Driving manually**: `/clear` at phase boundaries, or when `/context` looks heavy — not between plan → execute → verify of the same phase. After a clear, run `/flow-status` to re-orient (or just run the next `/flow-` command; they self-orient).
- **Autonomous (`/goal`, `/loop`)**: do **not** `/clear` mid-run — it kills the goal/loop and its accumulated context. Let it reach a `GATE`/`DONE`, then `/clear` and start the next run. One autonomous run ≈ one phase or milestone.
