<!-- .planning/STATE.md — cap 1.5KB. Rewrite sections in place; never append. -->
# State

## Position
Phase: {N} of {total} ({name}) | Plans: {done}/{total} | Status: {planning|ready|executing|verifying|verified|hardened|uat|released}
Last: {YYYY-MM-DD} — {one line: what happened}
Next: {command to run}

## Gate
<!-- `none`, or the block below whenever a skill emits FLOW: GATE. Clear it the moment it is answered.
     The one structured exception to "never parse skill prose" — a driver reads this to learn what is
     asked and which answers are on the table. It may surface them; it may never pick one.
     type: decision|human-action|approval · max 4 options, one line each · omit plan/task when not plan-scoped:
       type: decision
       asked: {the question — same text that lands in DECISIONS.md `asked`}
       options:
         1. {option} — {consequence}
         2. {option} — {consequence}
       default: {none|N}
       plan: {NN-MM} | task: {N} -->
none

## Run
<!-- Autonomous-loop rails, owned by /flow-next — other skills leave it alone. Absent = cold start
     (iteration 1). MALFORMED = BLOCKED, never assumed zero: a counter that cannot be read is not a
     counter that says zero. Reset by an answered gate or /flow-status --reset-run. -->
Iteration: {N} | Started: {YYYY-MM-DDTHH:MMZ} | Repeats: {K}
Signature: {rule<N>:phase<NN>:plans<d/t>:verif<status>}

## Decisions
<!-- max 5 recent bullets; full log lives in PROJECT.md -->
- {phase}: {decision} (D-NN)

## Blockers
- none

## Session
Stopped: {where work stopped}
Resume: {hint for next session}
