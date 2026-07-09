---
name: flow-next
description: Advance the project exactly one step (plan, execute, replan gaps, or harden) and stop with a FLOW status line. The driver for autonomous operation via /goal or /loop. Use to make progress without deciding what comes next.
---

# flow-next

Read `${CLAUDE_PLUGIN_ROOT}/references/autonomy.md` first — it defines the status line, the human gates, and /loop etiquette. Then read `.planning/STATE.md`.

**One step per invocation.** Do the single next step below, then stop with the `FLOW:` status line. Never chain a second step — bounded turns keep /goal evaluation and /loop iterations predictable.

Routing (first match wins):
1. No `.planning/` → do nothing. `FLOW: GATE | no project — /flow-new is interactive | next: /flow-new`
2. STATE shows an unresolved checkpoint or blocker → `FLOW: GATE | {what's needed} | next: {command}` (or `BLOCKED` if it's an error to investigate, suggesting `/flow-debug`).
3. Current phase has no plans → run the `/flow-plan N --auto` flow (invoke the flow-plan skill with `N --auto`).
4. Plans exist without SUMMARYs → run `/flow-execute N --auto`.
5. VERIFICATION has gaps → run `/flow-plan N --gaps`.
6. Phase verified, more phases remain → step 3 for the next phase.
7. All phases verified, no `.planning/deploy/PIPELINE.md` → run `/flow-harden`.
8. Hardened, no PR URL recorded in STATE → run `/flow-pr` (it gates on human confirmation before opening the PR).
9. PR open / not yet merged → stop: UAT needs the merge + a human (azd auth, acceptance testing). `FLOW: GATE | awaiting merge, then UAT | next: /flow-uat`

If the step itself ends at a gate (checkpoint, escalation, gaps needing a decision), report that state — the invoked skill's outcome decides CONTINUE vs GATE/BLOCKED. All phases verified and deploy pipeline released → `FLOW: DONE`.

Under `/loop`: apply the loop etiquette from autonomy.md (stop the loop on GATE/BLOCKED/DONE, explain why).
