---
name: flow-debug
description: Systematic debugging with persistent hypothesis state that survives sessions. Args - symptom description, or no args to resume the newest open debug file. Use when cause is unknown.
---

# flow-debug

Context rules: read `.planning/STATE.md` first if present. Keep output terse.

1. **State file**: no args → resume the newest `status: open` file in `.planning/debug/`; none → ask for the symptom. New symptom → create `.planning/debug/NNN-slug.md` from `${CLAUDE_PLUGIN_ROOT}/templates/debug.md`: symptom, repro (get a reliable reproduction FIRST — no repro means gathering evidence, not testing fixes), initial hypotheses table (2–4, ranked by likelihood × cheapness to test).

2. **Loop** until a hypothesis is confirmed:
   - Pick the highest-value untested hypothesis.
   - Test it with the cheapest decisive evidence (log, breakpoint-equivalent, minimal repro, bisect). For heavy investigation spawn `flow-executor` in **investigate mode** (prompt: debug file path + the hypothesis + "gather evidence only, no commits") and merge its findings into the file.
   - Record evidence; mark hypothesis confirmed/refuted. All refuted → widen: add hypotheses one abstraction level up (config, environment, caller) rather than re-testing the same layer.
   - Update the file every iteration — it must let a fresh session resume cold.

3. **Fix**: on confirmed root cause, fix via the /flow-quick flow (trivial → direct; bigger → mini-plan + executor), commit message referencing the debug file. Verify the original repro now passes.

4. **Close**: set `status: resolved`, fill Resolution (root cause + fix commit). If the root cause implies a lasting rule, add one bullet to `.planning/LEARNINGS.md`.

End with the status line per `${CLAUDE_PLUGIN_ROOT}/references/autonomy.md` — resolved: `FLOW: CONTINUE | debug NNN resolved | next: {per STATE}`; needs the user or a real environment: `GATE`; dead end: `BLOCKED`.
