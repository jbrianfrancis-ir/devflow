---
name: flow-next
description: Advance the project exactly one step (plan, execute, replan gaps, or harden) and stop with a FLOW status line. The driver for autonomous operation via /goal or /loop. Use to make progress without deciding what comes next.
---

# flow-next

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

Read `{devflow_root}/references/autonomy.md` first — it defines the status line, the human gates, and /loop etiquette. Then read `.planning/STATE.md`.

**One step per invocation.** Do the single next step below, then stop with the `FLOW:` status line. Never chain a second step — bounded turns keep /goal evaluation and /loop iterations predictable.

## Rails first (before any work)
Determine which routing rule below would fire, then apply the rails from `autonomy.md` → Loop rails against `STATE.md`'s `## Run` block and `.planning/config.json` → `autonomy` (defaults `max_iterations: 40`, `max_repeats: 3`, `max_hours: null`).

1. Build the `Signature` for the rule about to fire: `rule<N>:phase<NN>:plans<d/t>:verif<status>`.
2. Same as the recorded one → `Repeats + 1`. Different → `Repeats: 0`.
3. `Repeats >= max_repeats` → stop: `FLOW: BLOCKED | no progress across {K} iterations at rule {N} | next: /flow-debug {what is not moving}`. Do **not** run the step; running it again is what the rail exists to prevent.
4. `Iteration >= max_iterations`, or `max_hours` elapsed since `Started` → stop: `FLOW: GATE | {cap} reached at {position} | next: raise the cap in config.json, or take it manually`.
5. Otherwise increment `Iteration`, write the `## Run` block back, and continue to routing.

Absent block → cold start: `Iteration: 1`, `Started: {now}`, `Repeats: 0`. Malformed block → `FLOW: BLOCKED | STATE ## Run block unreadable | next: fix or delete the block, then rerun` — never assume zero.

Routing (first match wins):
1. No `.planning/` → do nothing. `FLOW: GATE | no project — /flow-new is interactive | next: /flow-new`
2. STATE shows an unresolved checkpoint or blocker → `FLOW: GATE | {what's needed} | next: {command}` (or `BLOCKED` if it's an error to investigate, suggesting `/flow-debug`). A populated `## Gate` block is itself an unresolved gate: surface its `asked` + `options` to the human verbatim and never answer it. **One exception, and only one**: a gate that asks whether a PR has been reviewed and merged is asking about an observable fact, and `gh pr view <n>` observes it (autonomy.md → External state is a cache, never evidence, and *Observation answers a fact, never an authorization*). Found merged → the gate is answered; clear it and continue routing rather than re-asking a question with no remaining answer. Every other gate — including any gate about a deploy — stays human even if the world appears to have moved: "may I release?" is not answered by observing that something released.
3. Current phase has no plans → run the `/flow-plan N --auto` flow (invoke the flow-plan skill with `N --auto`).
4. Plans exist without SUMMARYs → run `/flow-execute N --auto`.
5. VERIFICATION has gaps → run `/flow-plan N --gaps`.
6. Phase verified, more phases remain → step 3 for the next phase.
7. All phases verified, no `.planning/deploy/PIPELINE.md` → run `/flow-harden`. **Does not fire when the project has no deployable surface** — see *Deploy N/A* below.
8. Ready to integrate — hardened, or all phases verified on a deploy-N/A project — and no PR URL recorded in STATE → run `/flow-pr` (it gates on human confirmation before opening the PR).

**If STATE records a PR, re-read it live before rules 9-12 evaluate** — `gh pr view <n> --json state,mergedAt,mergeStateStatus,reviewDecision,url` — and route on that result, never on the line STATE has recorded (autonomy.md → External state is a cache, never evidence). **Any** failure of that read — `gh` missing, unauthenticated, offline, or the PR not found (deleted, or a number STATE got wrong) → `FLOW: BLOCKED | cannot read PR #N state ({reason}) | next: {gh auth login, or correct the PR number in STATE}, then /flow-next`. Never fall back to the recorded line: rule 8 will not re-fire while STATE still records a PR, so a swallowed error leaves the run with no next step at all.

9. PR **live** open and not green (checks failing/pending, or unresolved bot review threads) → run `/flow-ci`. It is autonomous work: driving a PR to green needs no human.
10. PR **live** open and green / awaiting human review or merge → stop: review and merge are human, and UAT needs the merge plus azd auth. `FLOW: GATE | PR #N green, awaiting review/merge | next: after merge, /flow-uat` (deploy N/A → `next: after merge, /flow-next` — the merge is the end).
11. PR **live** merged → the merge *is* the answer to rule 10's gate. Clear `## Gate` to `none`, reset `## Run` (`Iteration: 1`, fresh `Started`, `Repeats: 0`), record the merge in STATE (Position + Session) and prepend a `.planning/JOURNAL.md` line, then route on: deploy N/A with all phases verified → `FLOW: DONE | PR #N merged, roadmap verified | next: none`; otherwise → `FLOW: CONTINUE | PR #N merged | next: /flow-uat`.
12. PR **live** closed unmerged → `FLOW: GATE | PR #N closed without merging | next: decide whether to reopen or re-branch` — a closed PR is a human decision, not a routing hop, and never a route to `/flow-uat`: nothing reached the base branch.

**Deploy N/A.** When `.planning/config.json` → `deploy.tool` is `null`, the project has nothing to deploy (autonomy.md → Projects with no deployable surface). Rule 7 does not fire, rule 8 keys off *verified* instead of *hardened* so the work still routes to a PR, and a merged PR is terminal. Only an explicit `null` qualifies: missing, unreadable, or non-null config all mean the project deploys and the deploy chain applies unchanged.

If the step itself ends at a gate (checkpoint, escalation, gaps needing a decision), report that state — the invoked skill's outcome decides CONTINUE vs GATE/BLOCKED — and make sure it left the `## Gate` block populated. All phases verified and deploy pipeline released → `FLOW: DONE`; on a deploy-N/A project, all phases verified with the work merged → `FLOW: DONE`, because verified *is* the end state and there is no pipeline to wait on.

When a gate is answered, clear `## Gate` to `none` and reset `## Run` (`Iteration: 1`, fresh `Started`, `Repeats: 0`): a human touching the run is the strongest possible evidence it is no longer stuck.

Under `/loop`: apply the loop etiquette from autonomy.md (stop the loop on GATE/BLOCKED/DONE, explain why).
