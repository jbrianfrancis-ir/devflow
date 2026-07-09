---
name: flow-quick
description: Do a small ad-hoc task with Flow guarantees (atomic commits, deviation rules, logged) without phase ceremony. Args - task description. Use for fixes and small features outside the roadmap.
---

# flow-quick

Context rules: read `.planning/STATE.md` first (no `.planning/` → this still works, just skip logging and warn once). Keep output terse.

**Triage** the task:

- **Trivial** (≤2 files, obvious approach, no new dependencies): do it directly in this session. One atomic commit `type(quick): description`. Append one line to `.planning/quick/LOG.md`: `- NNN | YYYY-MM-DD | description | commit SHA` (create the file if missing; NNN = next number).

- **Non-trivial** (3+ files, needs sequencing, or touches architecture): write a mini-plan to `.planning/quick/NNN-slug.md` — same format as `${CLAUDE_PLUGIN_ROOT}/templates/plan.md` but 3–5 tasks, `wave: 1`, no dependencies (read `${CLAUDE_PLUGIN_ROOT}/references/plan-format.md` only if unsure of the task format). Spawn one `flow-executor` with: the mini-plan path, STATE path (+ `.planning/ARCHITECTURE.md` when present), summary template `${CLAUDE_PLUGIN_ROOT}/templates/summary.md`, checkpoints reference `${CLAUDE_PLUGIN_ROOT}/references/checkpoints.md`, conventions `${CLAUDE_PLUGIN_ROOT}/references/conventions.md`, and "SUMMARY goes next to the plan". Handle CHECKPOINT returns as in /flow-execute. Append the LOG line when done.

- **Actually roadmap-sized** (new subsystem, spans requirements): say so and recommend adding a phase (`/flow-plan`) instead. Don't sneak big work through quick.

If the task looks like a bug hunt (symptom, unknown cause), suggest `/flow-debug` instead.

Deviation rules, commit discipline, package-install caution, and the `.planning/ARCHITECTURE.md` + `${CLAUDE_PLUGIN_ROOT}/references/conventions.md` constraints (work on the feature branch, code under `src/`) apply exactly as in normal execution (the executor owns them; in the trivial path, you do).

End with the status line per `${CLAUDE_PLUGIN_ROOT}/references/autonomy.md` — done: `FLOW: CONTINUE | quick NNN committed | next: {resume prior work per STATE}`; checkpoint: `GATE`.
