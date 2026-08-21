---
name: flow-handsoff
description: Start a hands-off autonomous run in one command - drives /flow-next until the project reaches DONE, GATE, or BLOCKED, or the turn cap trips. Use instead of assembling /goal and /flow-next by hand.
hooks:
  Stop:
    - hooks:
        - type: prompt
          prompt: |
            A DevFlow hands-off run is active. Allow the turn to end when ANY of these holds; otherwise block it.

            1. The last assistant message ends with a `FLOW:` status line whose state is `DONE`, `GATE`, or `BLOCKED`. All three are terminal for a hands-off run: DONE finished it, GATE needs a human answer, BLOCKED needs a human to investigate. Only `CONTINUE` means keep going.
            2. Forty or more assistant turns have elapsed since this run started.
            3. The user has asked to stop, pause, abort, or interrupt, or has answered a gate question. The user's intent always wins; never block a turn against it.
            4. The last two consecutive assistant turns produced no `FLOW:` status line and made no tool progress. The driver is broken, and trapping the session helps nobody.

            Otherwise the run is mid-flight: block stopping, and invoke the `flow-next` skill for exactly one more step.
---

# flow-handsoff

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

The one-command form of the hands-off run that `autonomy.md` → Suggested invocations otherwise asks the user to assemble by hand (`/goal <condition>`, then `/flow-next`). The `Stop` hook in this skill's frontmatter **is** the goal: the host registers it for the session when this skill loads, and it blocks the turn from ending while `/flow-next` still reports `CONTINUE`.

Read `{devflow_root}/references/autonomy.md` before the first step — the status line and the human-gate list are the contract this run is driven by, and nothing here overrides them. **Every gate in that list is still a human gate.** A hands-off run stops at them; it never answers one.

**Claude Code only.** Session `Stop` hooks are a Claude mechanism. On Codex there is no equivalent: do not start a run, print the manual form (`$flow-next`, re-invoked per step) and stop. Say which host the user is on rather than failing quietly — a user who thinks a run is driving itself when it is not will come back to an untouched project.

## Before the first step
1. **Project must exist.** No `.planning/` → `FLOW: GATE | no project — /flow-new is interactive | next: /flow-new`. Do not register a run against a repo with nothing to drive.
2. **Reset the rails.** Reset `STATE.md`'s `## Run` block the way `/flow-status --reset-run` does (`Iteration: 1`, fresh `Started`, `Repeats: 0`). A new hands-off run is a new run; inheriting a stale iteration count from an abandoned one burns the cap before any work happens.
3. **Report the shape of the run before driving it**: the position from `STATE.md`, the caps actually in force from `.planning/config.json` → `autonomy`, and the fact that the session will not stop on its own until a terminal state. The user is handing over a session — say what they are handing over.

The turn cap in the hook is a fixed backstop of 40, deliberately independent of `autonomy.max_iterations` so that a bug in the rails cannot produce an unstoppable session. The rail in `.planning/config.json` is the one to tune (`autonomy.max_iterations`, default 40); this skill never edits it. When the two differ, whichever binds first ends the run — report the rail's cap, not the hook's, since the rail is what normally fires.

## The run
Invoke `flow-next` for exactly one step, let it emit its status line, and stop the turn. The hook decides whether the turn actually ends. Do not chain steps inside one turn and do not re-implement the routing — `/flow-next` owns it, rails included.

## When it stops
State plainly which condition ended the run and what the human should do:
- `DONE` — the roadmap is verified (or released). Nothing is pending.
- `GATE` — surface the `## Gate` block's `asked` and `options` verbatim. Never pick one.
- `BLOCKED` — say what stopped moving and point at `/flow-debug`.
- Turn cap — the run is not finished; `/flow-handsoff` again resumes it from the same position.

**Clearing the run early.** `/goal clear` does **not** clear this hook — the host's clear path skips hooks owned by a skill, by design, so `/goal` cannot disarm something it did not arm. Ask the model to stop (condition 3) or end the session; there is no third way. Tell the user this when the run starts, not when they are trying to escape it.
