---
name: flow-handsoff
description: Start a hands-off autonomous run in one command - drives /flow-next until the project reaches DONE, GATE, or BLOCKED, or the host's stop-hook cap trips. Claude Code only; no Codex equivalent. Use instead of assembling /goal and /flow-next by hand.
hooks:
  Stop:
    - hooks:
        - type: prompt
          prompt: |
            A DevFlow hands-off run may be active. Allow the turn to end when ANY of the following holds. Block it only when none of them do.

            0. **No run is in flight.** Any of: no `FLOW-HANDSOFF: RUN START` marker appears in the transcript; the most recent marker is followed by an assistant turn ending in a terminal `FLOW:` status line (`DONE`, `GATE`, or `BLOCKED`); the most recent marker is followed by a `FLOW-HANDSOFF: RUN END` marker; or **any user message after the most recent marker asked to stop, pause, abort, or interrupt**. That last clause is what makes an abort stick: a stop request releases the turn it was typed on under condition 3, and without it the run would silently resume on the user's next unrelated message. This hook stays registered for the whole session and cannot be cleared with `/goal clear`, so a run that is over — finished or revoked — must never block a turn that has nothing to do with it.
            1. The last assistant message ends with a `FLOW:` status line whose state is `DONE`, `GATE`, or `BLOCKED`. All three are terminal for a hands-off run; only `CONTINUE` means keep going.
            2. Seven or more assistant turns have elapsed since the most recent `FLOW-HANDSOFF: RUN START` marker. Seven, not eight: the marker turn is itself the first block, so releasing at eight would land one turn after the host's own cap had already cut the turn.
            3. The **most recent user message** asks to stop, pause, abort, or interrupt, or answers a gate question. Judge that message alone, never the earlier transcript — the user's intent always wins and must not latch from a previous turn.
            4. The last two consecutive assistant turns produced no `FLOW:` status line and made no tool progress. The driver is broken, and trapping the session helps nobody.

            Otherwise a run is in flight: block stopping, and invoke the `flow-next` skill for exactly one more step.
---

# flow-handsoff

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

The one-command form of the hands-off run that `autonomy.md` → Suggested invocations otherwise asks the user to assemble by hand (`/goal <condition>`, then `/flow-next`). The `Stop` hook in this skill's frontmatter **is** the goal: the host registers it for the session when this skill loads, and it blocks the turn from ending while `/flow-next` still reports `CONTINUE`.

Read `{devflow_root}/references/autonomy.md` before the first step — the status line and the human-gate list are the contract this run is driven by, and nothing here overrides them. **Every gate in that list is still a human gate.** A hands-off run stops at them; it never answers one.

**Claude Code only.** Session `Stop` hooks are a Claude mechanism and ARCHITECTURE.md permits exactly this one (skill-scoped, `type: prompt`). On Codex there is no equivalent: do not start a run, print the manual form (`$flow-next`, re-invoked per step) and stop with `FLOW: GATE | hands-off runs need Claude Code | next: $flow-next, one step at a time`. Say which host the user is on rather than failing quietly — a user who believes a run is driving itself when it is not will come back to an untouched project.

## The real limit is the host's, not this skill's
Claude Code force-ends a turn after **8 consecutive `Stop`-hook blocks** (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`, default 8). That is the true ceiling on a single run: **at most 7 `/flow-next` steps**, after which the host would end the turn even though the run may still be reporting `CONTINUE`. The hook releases at seven so the run reports its own stop one turn *before* the host's cap, rather than being cut off mid-step by a warning the user has no branch to interpret. Setting the hook's cap equal to the host's would land exactly one turn too late.

Tell the user this number when the run starts. A skill that promises to drive to completion and quietly stops at 8 leaves them with a half-driven project and no reason to look. Re-running `/flow-handsoff` starts a fresh run from wherever the last one reached; the project's own `## Run` rails in `STATE.md` (`autonomy.max_iterations`, default 40) still bound the total across runs, and those are the caps to tune — this skill never edits them.

## Before the first step
1. **Project must exist.** No `.planning/` → `FLOW: GATE | no project — /flow-new is interactive | next: /flow-new`. Do not start a run against a repo with nothing to drive.
2. **Reset the rails.** Reset `STATE.md`'s `## Run` block the way `/flow-status --reset-run` does (`Iteration: 1`, fresh `Started`, `Repeats: 0`). A new hands-off run is a new run; inheriting a stale count from an abandoned one burns the cap before any work happens.
3. **Print the run-start marker** on its own line, exactly: `FLOW-HANDSOFF: RUN START`. The hook counts turns from this marker and uses it to tell an in-flight run from a finished one. Without it the hook cannot scope itself, and a run that has already ended keeps blocking unrelated turns for the rest of the session.
4. **Report the shape of the run before driving it**: the position from `STATE.md`, the caps actually in force (8 steps this run, `autonomy.max_iterations` across runs), and that the session will not stop on its own before one of those bounds or a terminal state. The user is handing over a session — say what they are handing over.

## The run
Invoke `flow-next` for exactly one step, let it emit its status line, and end the turn. The hook decides whether the turn actually ends. Do not chain steps inside one turn and do not re-implement the routing — `/flow-next` owns it, rails included.

## When it stops
State plainly which condition ended the run and what the human should do:
- `DONE` — the roadmap is verified (or released). Nothing is pending.
- `GATE` — surface the `## Gate` block's `asked` and `options` verbatim. Never pick one. Answering it does not resume the run; `/flow-handsoff` again starts the next one.
- **User stopped it** — print `FLOW-HANDSOFF: RUN END` and `FLOW: GATE | run stopped by the user at {position} | next: /flow-handsoff to resume, or /flow-status`. Emit these on the turn the stop is honoured, not later: the marker is what tells the hook the run is over, and without it the next unrelated message drags the session back into a run the user revoked.
- `BLOCKED` — say what stopped moving and point at `/flow-debug`.
- **Step cap (8) reached** — the run is not finished and nothing is wrong. Say which step it reached and that `/flow-handsoff` resumes from there.
- **Host cut the turn** — if the turn ends with the host's stop-hook warning rather than one of the above, the run exceeded the block cap. Report it as a cap stop, not as a completed run.

**Clearing the run early.** `/goal clear` does **not** clear this hook — the host's clear path skips hooks owned by a skill, by design, so `/goal` cannot disarm something it did not arm. Ask the model to stop (condition 3) or end the session. Between runs the hook stays registered but inert: condition 0 releases every turn once the last run reached a terminal state. Tell the user this when the run starts, not when they are trying to escape it.

End with the status line per `{devflow_root}/references/autonomy.md`: the terminal state the run reached (`DONE`/`GATE`/`BLOCKED`), `FLOW: GATE | no project …` when pre-flight fails, `FLOW: GATE | hands-off runs need Claude Code | next: $flow-next, one step at a time` on Codex, and `FLOW: CONTINUE | step cap reached at {position} | next: /flow-handsoff` when the run stopped at the cap with work still to do. Every turn this skill ends must carry one — the hook's own release conditions key off it.
