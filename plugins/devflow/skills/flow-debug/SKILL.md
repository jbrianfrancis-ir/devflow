---
name: flow-debug
description: Systematic debugging with persistent hypothesis state that survives sessions. Args - symptom description, or no args to resume the newest open debug file. Use when cause is unknown. Supports --provider native|claude|codex.
---

# flow-debug

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

**Agent provider**: accept `--provider native|claude|codex`. Resolve and dispatch every role in this run exactly as `{devflow_root}/references/hosts.md` specifies. The selected provider applies to all delegated roles unless this skill explicitly calls an external consultation engine. A missing or failed peer is fail-closed; report `FLOW: BLOCKED` with remediation and never fall back silently.

Context rules: read `.planning/STATE.md` first if present. Keep output terse.

1. **State file**: no args → resume the newest `status: open` file in `.planning/debug/`; none → ask for the symptom. New symptom → create `.planning/debug/NNN-slug.md` from `{devflow_root}/templates/debug.md`: symptom, repro (get a reliable reproduction FIRST — no repro means gathering evidence, not testing fixes), initial hypotheses table (2–4, ranked by likelihood × cheapness to test).

2. **Loop** until a hypothesis is confirmed:
   - Pick the highest-value untested hypothesis.
   - Test it with the cheapest decisive evidence (log, breakpoint-equivalent, minimal repro, bisect). For heavy investigation spawn `flow-executor` in **investigate mode** (prompt: debug file path + the hypothesis + "gather evidence only, no commits") and merge its findings into the file.
   - Record evidence; mark hypothesis confirmed/refuted. All refuted → widen: add hypotheses one abstraction level up (config, environment, caller) rather than re-testing the same layer. Still stuck after a widen round → offer `/flow-oracle` seeded with the debug file (an external second opinion beats a third blind round); merge surviving suggestions back as new hypotheses.
   - Update the file every iteration — it must let a fresh session resume cold.

3. **Fix**: on confirmed root cause, fix via the /flow-quick flow (trivial → direct; bigger → mini-plan + executor), commit message referencing the debug file. Verify the original repro now passes, then make it permanent: convert the repro into a regression test under `tests/` (fails before the fix, passes after) in the same commit — skip only when it genuinely needs a real environment, and say why in Resolution.

4. **Close**: set `status: resolved`, fill Resolution (root cause + fix commit). If the root cause implies a lasting rule, add one bullet to `.planning/LEARNINGS.md`.

End with the status line per `{devflow_root}/references/autonomy.md` — resolved: `FLOW: CONTINUE | debug NNN resolved | next: {per STATE}`; needs the user or a real environment: `GATE`; dead end: `BLOCKED`.
