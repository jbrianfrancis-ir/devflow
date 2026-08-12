---
name: flow-quick
description: Do a small ad-hoc task with Flow guarantees (atomic commits, deviation rules, logged) without phase ceremony. Args - task description. Use for fixes and small features outside the roadmap. Supports --provider native|claude|codex.
---

# flow-quick

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

**Agent provider**: accept `--provider native|claude|codex`. Resolve and dispatch every role in this run exactly as `{devflow_root}/references/hosts.md` specifies. The selected provider applies to all delegated roles unless this skill explicitly calls an external consultation engine. A missing or failed peer is fail-closed; report `FLOW: BLOCKED` with remediation and never fall back silently.

Context rules: read `.planning/STATE.md` first (no `.planning/` → this still works, just skip logging and warn once). Keep output terse.

**Triage** the task:

- **Trivial** (≤2 files, obvious approach, no new dependencies): do it directly in this session. One atomic commit `type(quick): description` (secret-scan the staged diff first, per conventions.md — hit → GATE, no commit). Append one line to `.planning/quick/LOG.md`: `- NNN | YYYY-MM-DD | description | commit SHA` (create the file if missing; NNN = next number).

- **Non-trivial** (3+ files, needs sequencing, or touches architecture): write a mini-plan to `.planning/quick/NNN-slug.md` — same format as `{devflow_root}/templates/plan.md` but 3–5 tasks, `wave: 1`, no dependencies (read `{devflow_root}/references/plan-format.md` only if unsure of the task format). Spawn one `flow-executor` with: the mini-plan path, STATE path (+ `.planning/ARCHITECTURE.md` when present), summary template `{devflow_root}/templates/summary.md`, checkpoints reference `{devflow_root}/references/checkpoints.md`, conventions `{devflow_root}/references/conventions.md`, and "SUMMARY goes next to the plan". Handle CHECKPOINT returns as in /flow-execute. Append the LOG line when done.

- **Actually roadmap-sized** (new subsystem, spans requirements): say so and recommend adding a phase (`/flow-plan`) instead. Don't sneak big work through quick.

If the task looks like a bug hunt (symptom, unknown cause), suggest `/flow-debug` instead.

Deviation rules, commit discipline, package-install caution, and the `.planning/ARCHITECTURE.md` + `{devflow_root}/references/conventions.md` constraints (work on the feature branch, code under `src/`) apply exactly as in normal execution (the executor owns them; in the trivial path, you do).

End with the status line per `{devflow_root}/references/autonomy.md` — done: `FLOW: CONTINUE | quick NNN committed | next: {resume prior work per STATE}`; checkpoint: `GATE`.
