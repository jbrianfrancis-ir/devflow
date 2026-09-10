<!-- .planning/quick/014-verify-negative-controls.md — quick mini-plan. Executor prompt: complete, unambiguous. -->
---
phase: quick-014
plan: 014
wave: 1
depends_on: []
files_modified:
  - plugins/devflow/references/plan-format.md
  - plugins/devflow/templates/plan.md
  - plugins/devflow/agents/flow-plan-checker.md
  - plugins/devflow/agents/flow-executor.md
  - plugins/devflow/agents/flow-planner.md
  - plugins/devflow/skills/flow-plan/SKILL.md
  - plugins/devflow/.claude-plugin/plugin.json
  - plugins/devflow/.codex-plugin/plugin.json
  - .claude-plugin/marketplace.json
autonomous: true
requirements: [R1, R2, R3]
must_haves:
  truths:
    - "plan-format.md requires a <falsify> clause on every command-based <verify>, and states that <human-check> verifies are exempt"
    - "plan-format.md forbids resting a new test's verify on an aggregate marker (TEST SUCCEEDED / BUILD SUCCEEDED / exit 0 / '0 failures' / a bare suite name) and requires a string only execution can emit"
    - "flow-plan-checker rejects, as a blocking issue, a verify with no falsify and a new-test verify satisfiable without running the test"
    - "flow-executor runs the falsify mutation, confirms the check fails, reverts, then runs the real verify — and treats a mutation that does not fail as a blocking stop, not a pass"
    - "flow-plan's revision gate diffs must_haves.truths / artifacts / files_modified across a revision round and rejects the round when a removed entry is unjustified"
    - "flow-planner's contract states that a revision response must name and justify every removed truth, artifact, or files_modified entry"
  artifacts:
    - plugins/devflow/references/plan-format.md
    - plugins/devflow/templates/plan.md
    - plugins/devflow/agents/flow-plan-checker.md
    - plugins/devflow/agents/flow-executor.md
    - plugins/devflow/skills/flow-plan/SKILL.md
  key_links:
    - "templates/plan.md's task block carries <falsify> next to <verify>"
    - "flow-plan-checker's task check cites plan-format.md's falsify + execution-only rules"
    - "flow-plan SKILL step 4 performs the deletion diff before spawning the checker on a revision round"
---

<objective>
Close the "False Green" P0 set: make a plan's own guards provably capable of failing (R1),
ban test verifies that pass without the test running (R2), and stop revision rounds from
silently deleting proven work (R3).
</objective>

<context>
Source spec (read for intent, do not copy prose): the False Green requirements — R1 negative
control, R2 execution-only assertion, R3 revision deletion diff. Summarized in each task below;
you do not need the original.

Paths:
- /home/brianf/Work/devflow/.planning/ARCHITECTURE.md   (law — Principles + Forbidden bind)
- /home/brianf/Work/devflow/.planning/STATE.md
- /home/brianf/Work/devflow/plugins/devflow/references/plan-format.md
- /home/brianf/Work/devflow/plugins/devflow/references/conventions.md  (see "Fail-closed guards" — R1/R2 extend that principle to planner-authored guards)
- /home/brianf/Work/devflow/plugins/devflow/templates/plan.md
- /home/brianf/Work/devflow/plugins/devflow/agents/flow-plan-checker.md
- /home/brianf/Work/devflow/plugins/devflow/agents/flow-executor.md
- /home/brianf/Work/devflow/plugins/devflow/agents/flow-planner.md
- /home/brianf/Work/devflow/plugins/devflow/skills/flow-plan/SKILL.md

Binding constraints from ARCHITECTURE.md, restated because they decide task 5:
- Editing anything under `plugins/devflow/**` — markdown included — REQUIRES a version bump in
  all three manifests in ONE commit. Tasks 1–4 all touch shipped content, so task 5 is not
  optional bookkeeping; it is what makes the change legal.
- "Docs are pointers, never copies": state each rule in exactly one file. plan-format.md owns the
  rule text; the checker and executor cite it, they do not restate it.
- Python stays stdlib-only. Do NOT add a script for any of this — these are prose contracts.
</context>

<tasks>

<task type="auto">
  <name>Task 1: plan-format.md and templates/plan.md carry the falsify clause and the execution-only rule</name>
  <files>plugins/devflow/references/plan-format.md, plugins/devflow/templates/plan.md</files>
  <action>
In plan-format.md's `## Tasks` section, extend the `<verify>` sentence and add two rules.

(a) NEGATIVE CONTROL. Every `<task>` whose `<verify>` is a command carries a sibling
`<falsify>` naming ONE concrete mutation that makes that command fail — the specific edit
("delete the `lineLimit` modifier from PingOutcomeRow.swift"), not a category ("break the
file"). A `<verify>` holding only `<human-check>` is exempt and says so explicitly. State the
reason in one line: a guard nobody has seen fail is a guard nobody has established can fail,
and reading it does not settle that — this is `conventions.md`'s three-outcome rule
("could not check" is not "pass") applied to the guards DevFlow asks planners to write, rather
than only to DevFlow's own.

(b) EXECUTION-ONLY ASSERTION. When a plan's `files_modified` adds or creates a test, its
`<verify>` may not rest on an aggregate marker — name `** TEST SUCCEEDED **`, `BUILD SUCCEEDED`,
`exit 0`, "0 failures", and a non-zero test count as the banned class. It must assert a string
**only the test's execution can produce**, and the plan must pin whatever identifier that string
contains (the suite/test name as declared in the source) so the expected string is knowable at
plan time. Add the one-line trap that makes this rule non-obvious: a bare suite NAME is not
enough either, because a compiler line naming the same file ("Compiling KeychainCredentialTests.swift")
sits in the same log — the requirement is the CLASS of string (emitted only by the runner),
not the naming. Keep this to ~4 sentences; do not paste the full three-draft table.

Also add one sentence under `## Tasks` split signals or the cap paragraph noting that falsify
clauses add bytes and count against the 4KB cap — split rather than trim a falsify away.

In templates/plan.md, add `<falsify>` to the `<task type="auto">` block immediately after
`<verify>`, with a placeholder comment in the same voice as the neighbouring fields:
`<falsify>{concrete mutation that makes the verify command fail — executor applies it, confirms failure, reverts. Omit only when verify is a human-check.}</falsify>`
  </action>
  <verify>
Run from the repo root:
`grep -c 'falsify' plugins/devflow/references/plan-format.md` → at least 3, and
`grep -c 'falsify' plugins/devflow/templates/plan.md` → at least 1, and
`grep -qi 'human-check' plugins/devflow/references/plan-format.md` → exits 0, and
`grep -q 'TEST SUCCEEDED' plugins/devflow/references/plan-format.md` → exits 0.
Then `python3 scripts/check-links.py` → 0 failures, and the reference count it prints is >= the
count on the previous commit (it should rise or hold, never collapse).
  </verify>
  <falsify>
Before accepting: temporarily delete the `<falsify>` line you added to templates/plan.md, re-run
the two grep counts, and confirm the templates/plan.md count drops to 0 and the check fails.
Restore the line. If the check still passes with the line gone, the check is vacuous — fix the
check, not the file. Note the observed before/after in your SUMMARY.
  </falsify>
  <done>Both files state the two rules; the template's task block shows a falsify field; check-links is green with no drop in reference count.</done>
</task>

<task type="auto">
  <name>Task 2: flow-plan-checker rejects verifies that cannot fail</name>
  <files>plugins/devflow/agents/flow-plan-checker.md</files>
  <action>
Extend check 5 ("Tasks executable"), or add a check 5b immediately after it, with two blocking
conditions. Keep the file's existing terse one-line-per-check voice — this file is 3.5KB and
every line is load-bearing.

- **Missing negative control**: a `<task>` with a command `<verify>` and no `<falsify>` is an
  issue. So is a `<falsify>` that names no concrete mutation — "make it fail", "break the input",
  or a restatement of the verify — because an executor cannot apply it. A `<verify>` that is only
  a `<human-check>` is exempt.
- **Verify that cannot fail / execution-only**: a `<verify>` whose stated pass condition would
  hold in the state it exists to catch is an issue. Name the two observed shapes so the checker
  looks for them: a `grep` whose pass condition is "output is empty" (empty output is also what a
  missing file, a wrong path, or exit 2 produces — the check passes hardest when it is most
  wrong), and, when the plan's `files_modified` adds a test, a verify resting on an aggregate
  marker or a bare suite name rather than a string only the runner emits. Both are blocking, and
  the finding must quote the mutation or the log line that defeats the check.

Cite plan-format.md for the rule text rather than restating it (ARCHITECTURE: docs are pointers).
Do not touch the `Return exactly one of:` contract at the end of the file.
  </action>
  <verify>
`grep -qi 'falsify' plugins/devflow/agents/flow-plan-checker.md` exits 0;
`grep -qi 'output is empty\|empty output' plugins/devflow/agents/flow-plan-checker.md` exits 0;
`grep -q 'Return exactly one of' plugins/devflow/agents/flow-plan-checker.md` exits 0 (contract intact);
`head -6 plugins/devflow/agents/flow-plan-checker.md | grep -q 'model: opus'` exits 0 (frontmatter intact).
Then `python3 scripts/validate-plugin.py` → exit 0, no error lines.
  </verify>
  <falsify>
Before accepting: temporarily change `model: opus` in the frontmatter to `model: bogus` and run
`python3 scripts/validate-plugin.py`. If it does NOT report an error, the validator does not grade
frontmatter — record that in your SUMMARY as an unproven check rather than claiming the verify
covers it. Revert to `model: opus` either way, and confirm the file is byte-identical to your
intended content with `git diff` before committing.
  </falsify>
  <done>Checker names both blocking conditions, points at plan-format.md for the rule, and its return contract and frontmatter are unchanged.</done>
</task>

<task type="auto">
  <name>Task 3: flow-executor runs the negative control before trusting the verify</name>
  <files>plugins/devflow/agents/flow-executor.md</files>
  <action>
In the `Flow:` paragraph, change the per-task sequence so the guard is established before it is
believed. New order per task: implement → **if the task has a `<falsify>`: apply the mutation,
run `<verify>`, confirm it FAILS, revert the mutation** → run `<verify>` for real → commit.

State the fail-closed rule explicitly, because it is the whole point: a mutation that does not
make the verify fail means the verify is vacuous — that is a **blocking stop**, returned as a
CHECKPOINT (decision) naming the task, the mutation applied, and the output that still passed.
It is NOT a deviation to log and move past, and it is NOT a pass. Equally, if the mutation cannot
be applied or reverted cleanly, that is "could not check" per conventions.md — report it as not
run and stop; never treat it as satisfied.

Add one line making the revert non-negotiable: the mutation must be reverted before the real
verify runs and before anything is staged — confirm with `git diff` that the working tree carries
only the task's intended change. A falsify mutation reaching a commit is the defect this was
meant to prevent, inverted.

Keep it tight — this file is 5.5KB of dense contract. Do not restate plan-format.md's authoring
rules; the executor consumes falsify clauses, it does not write them.
  </action>
  <verify>
`grep -qi 'falsify' plugins/devflow/agents/flow-executor.md` exits 0;
`grep -qi 'revert' plugins/devflow/agents/flow-executor.md` exits 0;
`grep -q 'CHECKPOINT' plugins/devflow/agents/flow-executor.md` exits 0;
`head -6 plugins/devflow/agents/flow-executor.md | grep -q 'model: sonnet'` exits 0.
`python3 scripts/validate-plugin.py && python3 -m unittest discover -s tests -q` → exit 0, OK.
  </verify>
  <falsify>
Before accepting: confirm the grep for 'falsify' returns nothing on the PREVIOUS version of the
file — `git show HEAD:plugins/devflow/agents/flow-executor.md | grep -ci falsify` must print 0.
That establishes the grep is reading your change and not matching something that was already
there. Record both numbers in your SUMMARY.
  </falsify>
  <done>Executor's per-task flow runs the mutation first, treats a non-failing mutation as a blocking CHECKPOINT, and requires a clean revert before staging.</done>
</task>

<task type="auto">
  <name>Task 4: revision rounds diff for silent deletion</name>
  <files>plugins/devflow/skills/flow-plan/SKILL.md, plugins/devflow/agents/flow-planner.md</files>
  <action>
R3: a full-rewrite revision round silently dropped a whole task that had been added in an earlier
round in response to an empirical finding; nobody noticed for three rounds.

In flow-plan/SKILL.md step 4 (the revision gate), before respawning the planner, add: capture the
current `must_haves.truths`, `must_haves.artifacts` and `files_modified` entries from every plan's
frontmatter. When the revised set comes back, diff those three lists. Any entry present before and
absent after must be named and justified in the planner's response; an unjustified removal is
folded into the round's issue list as blocking — phrased so it is checked BEFORE the checker is
spawned, since a round that deleted proven work should not spend a top-tier agent.

State the reason in one line: the revision cap works (it stops and escalates); what it lacks is a
regression guard, so a round can be "clean" and still be a net loss.

Make it deterministic in the same spirit as the existing size check in that step ("it is a byte
count: measure it deterministically rather than paying a top-tier agent to estimate its own
output") — this is a set difference over frontmatter lists, so the orchestrator does it directly.
Do NOT add a Python script for it.

In flow-planner.md, add one line to the revision-mode contract: a revision response must name and
justify every truth, artifact, or `files_modified` entry it removed. Removing one silently is a
rejected round. If a rewrite genuinely supersedes an entry, say which entry replaces it.
  </action>
  <verify>
`grep -qi 'removed\|removal\|deletion' plugins/devflow/skills/flow-plan/SKILL.md` exits 0 AND the
matching text sits inside step 4 — confirm by reading the step, not by the grep alone;
`grep -qi 'files_modified' plugins/devflow/skills/flow-plan/SKILL.md` exits 0;
`grep -qi 'remov' plugins/devflow/agents/flow-planner.md` exits 0.
Then `python3 scripts/check-links.py` → 0 failures, reference count not lower than before.
  </verify>
  <falsify>
Before accepting: the grep terms above are weak (common words). Establish they are actually reading
your change — run `git show HEAD:plugins/devflow/skills/flow-plan/SKILL.md | grep -ci files_modified`
and `git show HEAD:plugins/devflow/agents/flow-planner.md | grep -ci remov`. If either is already
non-zero, the grep does not distinguish before from after: replace that check with a grep for a
distinctive phrase you actually wrote, re-run it, and report the substituted check in your SUMMARY.
This is exactly the R2 defect class — do not skip it.
  </falsify>
  <done>Step 4 diffs the three lists before the checker runs and rejects unjustified removals; the planner's revision contract requires naming removals; every verify used was shown to distinguish before from after.</done>
</task>

<task type="auto">
  <name>Task 5: bump the manifests and run the full smoke</name>
  <files>plugins/devflow/.claude-plugin/plugin.json, plugins/devflow/.codex-plugin/plugin.json, .claude-plugin/marketplace.json</files>
  <action>
Tasks 1–4 all edit shipped content under `plugins/devflow/**`, which ARCHITECTURE.md's manifest
Principle makes a bump-requiring change. This is a backward-compatible feature addition to the
plan contract (a new optional-to-omit-only-for-human-checks field plus new checker rules), so bump
the MINOR: 0.21.0 → 0.22.0, in all three files, in this one commit. Change nothing else in them.
  </action>
  <verify>
`grep -h '"version"' plugins/devflow/.claude-plugin/plugin.json plugins/devflow/.codex-plugin/plugin.json` and
`grep '"version"' .claude-plugin/marketplace.json` all show `0.22.0` — three files, one value.
Full smoke, exactly as ARCHITECTURE.md's `## Smoke` defines it:
`python3 scripts/validate-plugin.py && python3 -m unittest discover -s tests -v && python3 scripts/check-links.py`
Pass looks like: exit 0 from all three; validator prints no error lines; unittest reports `OK` with
0 failures and 0 errors; checker prints no failure lines. Paste the unittest tail and the
check-links summary line into your SUMMARY — the counts are the evidence, not "smoke green".
  </verify>
  <falsify>
Before accepting: this repo ships `scripts/check-version-bump.py`, whose whole job is to catch a
missing bump. Prove it is actually watching. Temporarily revert ONE manifest to 0.21.0 and run
`python3 scripts/check-version-bump.py` (read its usage first — it resolves a base ref, so give it
the base it needs, e.g. against `main`). Confirm it reports a failure. Restore 0.22.0 and confirm
it passes. If it cannot run here or does not fail on the mismatch, say so plainly in your SUMMARY
as "version gate not established locally" — do not report it as verified.
  </falsify>
  <done>All three manifests read 0.22.0; the full smoke command passes with counts recorded; the version gate was exercised against a deliberate mismatch or its non-establishment is stated.</done>
</task>

</tasks>
