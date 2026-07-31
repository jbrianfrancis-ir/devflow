# Plan format

A plan is an executor prompt: complete, unambiguous, executable by an agent with no other context. File: `.planning/phases/NN-slug/NN-MM-PLAN.md`, cap 4KB, structure in `templates/plan.md`.

## Frontmatter
All required unless noted: `phase`, `plan`, `wave`, `depends_on`, `files_modified`, `autonomous`, `requirements` (REQ-IDs from the roadmap — never empty), `must_haves.{truths,artifacts,key_links}`. Optional `user_setup`: external things the human must configure (accounts, secrets) — surfaced before execution starts.

## Waves (the dependency graph)
A phase's plans form a graph: plans are nodes, `depends_on` entries are edges, waves are the graph's parallel layers. An edge is real only when this plan **consumes something the dependency produces** — a file, an export, a schema, a migration, a running service. **Fake-edge test**: if a plan would execute identically without the dependency's output, the edge doesn't exist — drop it. Never sequence plans just because they were written in that order.

`wave = 1` if `depends_on` is empty, else `max(wave of each dependency) + 1`. Same-wave plans execute in parallel, so they must be fully independent: disjoint `files_modified`, and no shared mutable resource (migration chain, lockfile, generated file, port, seed data). A shared resource is a **hidden edge** — separate the waves or merge the plans. Phase wall-clock is the sum of its waves, so build the widest graph the real edges allow.

## Tasks
2–4 tasks per plan. Each `<task>` has `name` / `files` / `action` / `verify` / `done`. `<action>` must be specific enough to implement without guessing; `<verify>` must be a command or directly observable check.

**Split signals** — always split into more plans when: more than 4 tasks; multiple subsystems (DB + API + UI = separate plans); any task touching >5 files; discovery mixed with implementation; checkpoint mixed with implementation. Never shrink scope to fit a plan — split instead.

## must_haves (goal-backward)
Derive from the phase goal, not from the tasks: `truths` = observable behaviors that prove the goal ("user can log in and stays logged in after refresh"), `artifacts` = files that must exist, `key_links` = critical connections ("LoginForm submits to /api/auth"). The verifier checks these directly — existence of files proves nothing.

must_haves are the phase's **anchors** — signals that can't argue back. Once execution starts they are frozen: a gap is closed by changing the code, never by editing a truth to match what got built (that needs a human gate).

## Checkpoints
`type="checkpoint:decision"` — the user must choose between approaches. `type="checkpoint:human-action"` — the user must do something the agent can't (create an account, set a secret, verify a package). Human *verification* of built work is NOT a checkpoint task: put it in `<verify><human-check>…</human-check></verify>` so it batches to end-of-phase (each mid-flight stop costs a full executor cold-start). Set `autonomous: false` when any checkpoint task exists.

## Gates (used by every orchestrating skill)
- **Pre-flight**: check preconditions before starting work; on failure block with a message, create nothing.
- **Revision**: producer ↔ checker loop, max 3 iterations; escalate early if the issue count stops shrinking.
- **Escalation**: pause, present options with enough context to decide, wait for the user.
- **Abort**: stop immediately, preserve state, report why.
