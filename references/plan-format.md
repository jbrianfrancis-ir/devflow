# Plan format

A plan is an executor prompt: complete, unambiguous, executable by an agent with no other context. File: `.planning/phases/NN-slug/NN-MM-PLAN.md`, cap 4KB, structure in `templates/plan.md`.

## Frontmatter
All required unless noted: `phase`, `plan`, `wave`, `depends_on`, `files_modified`, `autonomous`, `requirements` (REQ-IDs from the roadmap — never empty), `must_haves.{truths,artifacts,key_links}`. Optional `user_setup`: external things the human must configure (accounts, secrets) — surfaced before execution starts.

## Waves
`wave = 1` if `depends_on` is empty, else `max(wave of each dependency) + 1`. Same-wave plans execute in parallel, so their `files_modified` must be disjoint — if two independent plans touch the same file, separate their waves or merge them.

## Tasks
2–4 tasks per plan. Each `<task>` has `name` / `files` / `action` / `verify` / `done`. `<action>` must be specific enough to implement without guessing; `<verify>` must be a command or directly observable check.

**Split signals** — always split into more plans when: more than 4 tasks; multiple subsystems (DB + API + UI = separate plans); any task touching >5 files; discovery mixed with implementation; checkpoint mixed with implementation. Never shrink scope to fit a plan — split instead.

## must_haves (goal-backward)
Derive from the phase goal, not from the tasks: `truths` = observable behaviors that prove the goal ("user can log in and stays logged in after refresh"), `artifacts` = files that must exist, `key_links` = critical connections ("LoginForm submits to /api/auth"). The verifier checks these directly — existence of files proves nothing.

## Checkpoints
`type="checkpoint:decision"` — the user must choose between approaches. `type="checkpoint:human-action"` — the user must do something the agent can't (create an account, set a secret, verify a package). Human *verification* of built work is NOT a checkpoint task: put it in `<verify><human-check>…</human-check></verify>` so it batches to end-of-phase (each mid-flight stop costs a full executor cold-start). Set `autonomous: false` when any checkpoint task exists.

## Gates (used by every orchestrating skill)
- **Pre-flight**: check preconditions before starting work; on failure block with a message, create nothing.
- **Revision**: producer ↔ checker loop, max 3 iterations; escalate early if the issue count stops shrinking.
- **Escalation**: pause, present options with enough context to decide, wait for the user.
- **Abort**: stop immediately, preserve state, report why.
