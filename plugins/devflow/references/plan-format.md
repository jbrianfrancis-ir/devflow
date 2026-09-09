# Plan format

A plan is an executor prompt: complete, unambiguous, executable by an agent with no other context. File: `.planning/phases/NN-slug/NN-MM-PLAN.md`, structure in `templates/plan.md`. **4KB is a soft target, not a gate.** Measure it once with `wc -c` when the plans are on disk — a byte count is not a judgment call, and a planner that re-measures its own prose after every edit burns a top tier on arithmetic. A plan over the target is a signal to **split** (`plugins/devflow/scripts/flow-split-plan.py`), never a reason to spend a revision round: never re-run the planner, and never trim prose, to chase a byte count. Trimming to fit degrades the plan the target exists to protect — repeated hand-trimming under byte pressure is what produced two contradicting truths in the phase this rule came from. If splitting is not natural, the plan ships over target and the size is reported once, not re-litigated. The split signals below are what actually keep a plan near it.

**The supported remedy for an over-cap plan is `plugins/devflow/scripts/flow-split-plan.py`, not hand-trimming.** Trimming prose to satisfy the cap degrades the plan the cap exists to protect: repeated hand-trimming under byte pressure in this phase's own source is what produced two contradicting truths in one phase — one asserting credentials repopulate on relaunch, another forbidding it — because the trimming pass that made each plan fit never checked what the other plan still said. Split, don't trim.

## Frontmatter
All required unless noted: `phase`, `plan`, `wave`, `depends_on`, `files_modified`, `autonomous`, `requirements` (REQ-IDs from the roadmap — never empty), `must_haves.{truths,artifacts,key_links}` plus optional `must_haves.backstop_truths`. Optional `user_setup`: external things the human must configure (accounts, secrets) — surfaced before execution starts.

## Waves (the dependency graph)
A phase's plans form a graph: plans are nodes, `depends_on` entries are edges, waves are the graph's parallel layers. An edge is real only when this plan **consumes something the dependency produces** — a file, an export, a schema, a migration, a running service. **Fake-edge test**: if a plan would execute identically without the dependency's output, the edge doesn't exist — drop it. Never sequence plans just because they were written in that order.

`wave = 1` if `depends_on` is empty, else `max(wave of each dependency) + 1`. Same-wave plans execute in parallel, so they must be fully independent: disjoint `files_modified`, and no shared mutable resource (migration chain, lockfile, generated file, port, seed data). A shared resource is a **hidden edge** — separate the waves or merge the plans. Phase wall-clock is the sum of its waves, so build the widest graph the real edges allow.

## Tasks
2–4 tasks per plan. Each `<task>` has `name` / `files` / `action` / `verify` / `done`, plus `<falsify>` alongside `<verify>` whenever `<verify>` is a command (see Negative control below). `<action>` must be specific enough to implement without guessing; `<verify>` must be a command or directly observable check.

**Negative control.** Every `<task>` whose `<verify>` is a command carries a sibling `<falsify>` naming ONE concrete mutation that makes that command fail — the specific edit ("delete the `lineLimit` modifier from PingOutcomeRow.swift"), not a category ("break the file"). A `<verify>` holding only `<human-check>` is exempt from `<falsify>` — say so explicitly when omitting it. Reason, in one line: a guard nobody has seen fail is a guard nobody has established can fail, and reading it does not settle that — this is `conventions.md`'s three-outcome rule ("could not check" is not "pass") applied to the guards a plan asks the executor to write, not only to DevFlow's own.

**Execution-only assertion.** When a plan's `files_modified` adds or creates a test, its `<verify>` may not rest on an aggregate marker — `** TEST SUCCEEDED **`, `BUILD SUCCEEDED`, `exit 0`, "0 failures", and a non-zero test count are the banned class. It must assert a string only the test's execution can produce, and the plan must pin whatever identifier that string contains (the suite/test name as declared in the source) so the expected string is knowable at plan time. A bare suite NAME is not enough either: a compiler line naming the same file ("Compiling KeychainCredentialTests.swift") sits in the same log — the requirement is the CLASS of string (emitted only by the runner), not the naming.

**Split signals** — always split into more plans when: more than 4 tasks; multiple subsystems (DB + API + UI = separate plans); any task touching >5 files; discovery mixed with implementation; checkpoint mixed with implementation. `<falsify>` clauses add real bytes — split rather than trim a falsify away, and never drop one to fit the soft target. Never shrink scope to fit a plan — split instead, with `plugins/devflow/scripts/flow-split-plan.py`.

## must_haves (goal-backward)
Derive from the phase goal, not from the tasks: `truths` = observable behaviors that prove the goal ("user can log in and stays logged in after refresh"), `artifacts` = files that must exist, `key_links` = critical connections ("LoginForm submits to /api/auth"). The verifier checks these directly — existence of files proves nothing.

must_haves are the phase's **anchors** — signals that can't argue back. Once execution starts they are frozen: a gap is closed by changing the code, never by editing a truth to match what got built (that needs a human gate).

### backstop_truths (non-inferable behavior)
An optional fourth list: truths whose **correct answer is not derivable from the requirements**. Not "hard to test" — *under-specified*. Do adjacent intervals `[1,2]` and `[2,3]` merge? Is a "character" a grapheme or a code unit? Does a retry re-run the whole batch or the failed item? The requirements don't say, so any implementation is defensible and nothing in the plan settles it.

They arrive two ways: the planner notices the spec never settled something, or REQUIREMENTS.md already carries an open `[NEEDS CLARIFICATION: …]` marker on one of the phase's requirements — a question someone judged would change what gets built and nobody answered. The second kind is not a judgment call: an unresolved marker on a requirement this phase implements **always** produces a backstop truth.

Write them in `backstop_truths` **and not in `truths`** — one truth belongs to exactly one list. The planner tags them at plan time, because plan time is the only moment anyone is reasoning about what the spec does *not* pin down; by verification time the code exists and reads as obviously correct.

The tag must be **structured, never prose**. A truth marked non-inferable by appending "(needs a held-out test)" to its text is a truth the verifier will grade green like any other — the signal has to survive as a field it can branch on, not a parenthetical it has to notice.

Why the separate list rather than asking the verifier to be careful: a verifier cannot detect a gap it does not perceive, so self-assessed caution barely helps — the abstention has to be **triggered from outside** its own judgment. Same reason `depends_on` is declared rather than inferred.

Keep the list small. Everything in it costs a human check, so a phase where most truths are non-inferable is a phase whose requirements need work, not more tags.

**Resolution closes the loop.** The reason the tag must be structured, never prose, is that a truth the verifier will grade green like any other is what makes it a truth at all — the same argument applies to the answer once a human supplies one. When a human resolves a backstop truth, the resolution lands as a `must_haves.truths` entry, where the verifier grades it. Not a YAML comment, not a note in the objective, not a `<human-check>` — each of those records the answer somewhere nothing reads back. The entry leaves `backstop_truths` the moment it joins `truths`: one truth belongs to exactly one list, per the rule above. This interacts with must_haves being frozen once execution starts (see `## must_haves`): a resolution before execution is the normal path; a resolution after execution starts is the documented human gate that rule already requires, never a quiet edit.

## Checkpoints
`type="checkpoint:decision"` — the user must choose between approaches. `type="checkpoint:human-action"` — the user must do something the agent can't (create an account, set a secret, verify a package). Human *verification* of built work is NOT a checkpoint task: put it in `<verify><human-check>…</human-check></verify>` so it batches to end-of-phase (each mid-flight stop costs a full executor cold-start). Set `autonomous: false` when any checkpoint task exists.

## Gates (used by every orchestrating skill)
- **Pre-flight**: check preconditions before starting work; on failure block with a message, create nothing.
- **Revision**: producer ↔ checker loop, max 3 iterations; escalate early if the issue count stops shrinking. `/flow-plan --panel` adds parallel judgment lenses (scope, feasibility, coherence) inside the same budget — a plan can be perfectly well-formed and still be the wrong plan, and that is the one defect no structural check can see.
- **Escalation**: pause, present options with enough context to decide, wait for the user.
- **Abort**: stop immediately, preserve state, report why.
