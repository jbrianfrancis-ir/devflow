# Autonomy protocol

How Flow composes with Claude Code's `/goal` and `/loop`. Skills cannot start loops or set goals — they emit transcript-verifiable status and behave predictably when driven.

## Status line
Every orchestrating skill ends its final message with exactly one line:

```
FLOW: <state> | <position> | next: <command>
```

States (the `/goal` evaluator matches these tokens):
- `CONTINUE` — more autonomous work is available; the next command can run without human input.
- `GATE` — human input required: checkpoint decision/human-action (incl. package legitimacy), a secret-scan hit, PR to upstream, UAT acceptance + sign-off, production confirmation, azd login. Include what's needed in `<position>`.
- `BLOCKED` — an error needs investigation before anything can proceed.
- `DONE` — roadmap fully verified (or released, after /flow-release).

Example: `FLOW: CONTINUE | phase 2/4 executed, verification pass | next: /flow-plan 3`

## Human gates — never auto-proceed, even in auto mode or under /goal//loop
Checkpoint `decision` and `human-action` tasks; failed-package verification; a fail-closed secret-scan hit (credential material in an outgoing diff — see `conventions.md`); UAT acceptance results and SIGNOFF.md; production release confirmation; opening a pull request to upstream; pushing tags; anything destructive in git. Also a hard rule (not a gate): never commit to the base branch (`dev`/`main`) — always a feature branch (see `conventions.md`).

## Under /loop (dynamic mode)
After emitting the status line: `CONTINUE` → reschedule soon and keep going next iteration. `GATE`/`BLOCKED`/`DONE` → stop the loop (ScheduleWakeup `stop: true`) and state plainly why it stopped and what the human should do.

## Suggested invocations (what skills print, users run)
- Drive to completion: `/goal FLOW says DONE or GATE, or stop after 40 turns` then `/flow-next`
- Background cadence: `/loop /flow-next`
- Watch a deployment: `/loop 15m curl the UAT health endpoints and report any change`
