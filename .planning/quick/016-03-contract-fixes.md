<!-- .planning/quick/016-03-contract-fixes.md -->
---
phase: quick-016
plan: 03
wave: 3
depends_on: []
files_modified:
  - plugins/devflow/references/plan-format.md
  - plugins/devflow/agents/flow-plan-checker.md
  - plugins/devflow/agents/flow-executor.md
  - plugins/devflow/agents/flow-planner.md
  - plugins/devflow/skills/flow-plan/SKILL.md
  - plugins/devflow/skills/flow-execute/SKILL.md
  - plugins/devflow/templates/plan.md
autonomous: true
requirements: [B1, B4, dedup]
must_haves:
  truths:
    - "every reference to the split tool uses {devflow_root}/scripts/, the form that resolves in a consuming project"
    - "the falsify protocol is scoped so it cannot corrupt or be corrupted by a parallel same-wave executor"
    - "the soft-target rule is stated once, in plan-format.md, and cited elsewhere"
    - "plan-format.md contains no paragraph still framing 4KB as a cap"
  artifacts: [plugins/devflow/references/plan-format.md, plugins/devflow/agents/flow-executor.md]
  key_links: ["flow-executor's falsify step and /flow-execute's parallel wave model agree"]
---

<objective>
Fix the two remaining blocking review findings that live in contract prose, and collapse the
rule duplication four lenses flagged.
</objective>

<context>
- /home/brianf/Work/devflow/.planning/ARCHITECTURE.md — law. "Docs are pointers, never copies" is the governing Principle for most of this plan.
- /home/brianf/Work/devflow/plugins/devflow/references/hosts.md — for how `{devflow_root}` is resolved.
- /home/brianf/Work/devflow/plugins/devflow/skills/flow-status/SKILL.md line ~44 and hosts.md line ~40 — the CORRECT form to copy: `{devflow_root}/scripts/flow-fleet.py`.

BLOCKING B1 (conventions + architecture lenses, independently): four references to the split tool
use `plugins/devflow/scripts/flow-split-plan.py` — the repo-source path. In a consuming project
the plugin lives in the plugin cache and that path resolves to nothing. Every other shipped script
reference uses `{devflow_root}/scripts/…`. `check-links.py` stays green because the path exists in
THIS repo, so the gate is structurally blind to it. Locations: plan-format.md lines ~3, ~5, ~22
and flow-plan/SKILL.md line ~22. Give the invocation in the `flow-fleet.py` form:
`python3 {devflow_root}/scripts/flow-split-plan.py <phase-dir> <plan> --after K`.

BLOCKING B4 (architecture lens): the new falsify protocol has each executor deliberately break the
working tree, run a command, and revert — but `/flow-execute` spawns all same-wave executors in
PARALLEL against ONE shared checkout. Concretely: executor A applies its mutation and runs the
suite while executor B runs its own real `<verify>`, which now fails through no fault of B. Worse
and quieter: B's own falsify run fails BECAUSE OF A's mutation, so B records a passing negative
control for a verify that is actually vacuous — the exact inverse of what the rule establishes.
And flow-executor.md's mandated "confirm with `git diff` that the working tree carries only the
task's intended change" is unsatisfiable in any parallel wave, since the tree legitimately carries
A's in-flight edits.

DEDUP findings (reuse + conventions + architecture lenses):
- plan-format.md line ~5 restates line ~3's rule AND its anecdote almost verbatim, and has already
  drifted — it still says "the cap", "an over-cap plan", "satisfy the cap" two lines after line 3
  declares 4KB a soft target. Reviewers all said: delete the line-5 paragraph, keeping only its
  unique detail (the contradicting-truths example) as a clause in line 3.
- The soft-target rule now exists in full in four places (plan-format.md ×2, flow-planner.md ~38,
  flow-plan/SKILL.md ~22) with no owner named.
- flow-plan-checker.md ~14 restates plan-format's disallowed-recording list; the "report every
  contradicting site" rule exists in both the checker and flow-plan/SKILL.md with neither citing
  the other; rule 5b restates plan-format's `<human-check>` exemption and banned-class summary,
  a third copy of which is in templates/plan.md.
- flow-plan-checker.md 5b/6b call findings "blocking", but the checker's declared return contract
  is `PASS` or numbered one-line issues with NO severity field, and /flow-plan step 4 treats every
  issue identically — the word carries no meaning to any consumer.
- flow-planner.md ~23 still says "Each task's `<verify>` is a command or observable check" with no
  mention of `<falsify>`, now stale against plan-format.md and templates/plan.md.
</context>

<tasks>

<task type="auto">
  <name>Task 1: fix the split-tool path in all four places</name>
  <files>plugins/devflow/references/plan-format.md, plugins/devflow/skills/flow-plan/SKILL.md</files>
  <action>
Replace every `plugins/devflow/scripts/flow-split-plan.py` with
`{devflow_root}/scripts/flow-split-plan.py`, matching hosts.md and flow-status/SKILL.md. Where a
reference is an instruction to run it, give the full invocation form
`python3 {devflow_root}/scripts/flow-split-plan.py <phase-dir> <plan> --after K` once — in
plan-format.md, the rule's owner — and leave the others as bare path references.
  </action>
  <verify>
`grep -rn 'plugins/devflow/scripts/flow-split-plan' plugins/devflow/` returns NOTHING (exit 1).
`grep -rn '{devflow_root}/scripts/flow-split-plan' plugins/devflow/` returns the replacements.
`python3 scripts/check-links.py` → 0 failures; the `{devflow_root}` form is rewritten to
`plugins/devflow/…` by the checker, so it must still resolve.
  </verify>
  <falsify>
check-links.py passed on the WRONG path too — that is the whole finding, so its passing proves
nothing by itself. Establish it grades the new form: change one `{devflow_root}/scripts/flow-split-plan.py`
to `{devflow_root}/scripts/flow-split-plann.py`, run check-links.py, confirm a non-zero failure
count naming that token, restore, confirm 0. Record both numbers.
  </falsify>
  <done>No repo-source path remains; the {devflow_root} form is used everywhere and shown to be link-checked.</done>
</task>

<task type="auto">
  <name>Task 2: reconcile the falsify protocol with parallel execution</name>
  <files>plugins/devflow/agents/flow-executor.md, plugins/devflow/skills/flow-execute/SKILL.md</files>
  <action>
Read `skills/flow-execute/SKILL.md`'s wave-spawning step first to see exactly what it promises
about parallelism and shared checkouts.

Scope the protocol so it is sound under parallel execution. In flow-executor.md:
- The falsify mutation applies ONLY to files in this task's own `<files>`, and the `<verify>` you
  run under mutation must be one whose result depends on those files. State that a whole-suite
  command (`npm test`, `dotnet test`) run under mutation is NOT a valid negative control in a
  parallel wave, because another executor's in-flight edits can produce the failure you are
  attributing to your own mutation — a passing negative control for a vacuous verify, which is
  worse than no negative control at all. Prefer a check scoped to the task's own files; when only
  a whole-suite command exists, say the negative control is inconclusive and report it as
  not-established rather than claiming it.
- The pre-commit cleanliness check becomes `git diff -- <this task's files>` rather than a whole
  tree `git diff`, for the same reason: in a parallel wave the tree legitimately carries another
  executor's work, so a whole-tree check is unsatisfiable and would be routinely ignored — a rule
  nobody can follow is a rule that trains people to skip rules.

In flow-execute/SKILL.md, add one sentence where waves are spawned: executors in the same wave
share one checkout, so a plan's `<falsify>` mutations must stay inside its own `files_modified` —
which the disjoint-files rule already guarantees — and a wave whose plans cannot honor that is a
wave that should have been split.

Do not restate plan-format.md's authoring rules in either file; the executor consumes falsify
clauses, it does not write them.
  </action>
  <verify>
`grep -ni 'parallel\|same wave' plugins/devflow/agents/flow-executor.md` matches the new text;
read the falsify sentence and confirm it scopes to the task's own files; confirm the `git diff`
instruction is now file-scoped.
`grep -ni 'falsify' plugins/devflow/skills/flow-execute/SKILL.md` matches.
`python3 scripts/validate-plugin.py` → exit 0, 13 agents, 22 skills. `python3 scripts/check-links.py` → 0 failures.
  </verify>
  <falsify>
`git show HEAD:plugins/devflow/skills/flow-execute/SKILL.md | grep -ci falsify` must print 0, and
`git show HEAD:plugins/devflow/agents/flow-executor.md | grep -ci 'same wave'` must print 0. If
either is non-zero, substitute a distinctive phrase you wrote and report the substitution.
Then confirm validate-plugin grades flow-executor.md: corrupt its frontmatter `model:` value, run
the validator, confirm it errors, restore.
  </falsify>
  <done>The mutation and the cleanliness check are both scoped to the task's own files; the whole-suite case is called inconclusive rather than passing; /flow-execute names the shared-checkout constraint.</done>
</task>

<task type="auto">
  <name>Task 3: one rule, one owner</name>
  <files>plugins/devflow/references/plan-format.md, plugins/devflow/agents/flow-planner.md, plugins/devflow/skills/flow-plan/SKILL.md, plugins/devflow/agents/flow-plan-checker.md, plugins/devflow/templates/plan.md</files>
  <action>
Apply ARCHITECTURE's "docs are pointers, never copies" to the duplication the review found. In
every case plan-format.md is the owner and the others cite it.

- plan-format.md: DELETE the line-5 paragraph. Fold its one unique detail — the contradicting
  truths, one asserting credentials repopulate on relaunch beside another forbidding it — into
  line 3's existing anecdote as a clause. Then re-read the whole file and confirm no paragraph
  still frames 4KB as a cap or gate.
- flow-planner.md and flow-plan/SKILL.md: replace the restated soft-target rule and its rationale
  with a citation ("size is a soft target per plan-format.md"), keeping ONLY the actor-specific
  instruction — planner: measure once, never between edits; skill: never fold size into the issue
  list, never respawn the planner for it.
- flow-plan-checker.md: have check 1b cite plan-format.md's resolution rule instead of re-listing
  the disallowed recording forms. State the "report every contradicting site, not the first" rule
  in ONE place and cite it from the other. In 5b, keep the checker-specific detection hints (the
  grep-passing-on-empty-output shape, the bare-suite-name shape) and drop the restated
  `<human-check>` exemption and banned-class summary.
- flow-plan-checker.md: remove the word "blocking" from 5b and 6b — the declared return contract
  has no severity field and /flow-plan treats all issues identically, so the word promises a
  distinction no consumer implements. Do NOT add a severity field; that is a larger change than
  this repair.
- flow-planner.md ~23: add `<falsify>` to its restatement of the task elements, or drop the
  restatement and point at plan-format.md. Prefer pointing.
- templates/plan.md: leave the `<falsify>` placeholder text; a template SHOWING the field is not
  duplication of the rule.
  </action>
  <verify>
`grep -ci 'over-cap\|the cap' plugins/devflow/references/plan-format.md` → 0 matches for cap
framing (read the file to confirm; the word may legitimately survive in another sense).
`grep -c 'blocking' plugins/devflow/agents/flow-plan-checker.md` → 0.
`grep -ci 'falsify' plugins/devflow/agents/flow-planner.md` → at least 1.
`python3 scripts/validate-plugin.py` → exit 0. `python3 scripts/check-links.py` → 0 failures.
Then read plan-format.md end to end and confirm the soft-target rule appears exactly once.
  </verify>
  <falsify>
`git show HEAD:plugins/devflow/agents/flow-plan-checker.md | grep -c blocking` must be non-zero
(proving the grep can see the word at all, and that you removed real occurrences). If it prints 0,
your grep is wrong — fix it. Same for `git show HEAD:plugins/devflow/references/plan-format.md | grep -ci 'over-cap'`,
which must be non-zero before your change.
  </falsify>
  <done>Each rule stated once with an owner; no cap framing survives; "blocking" removed from the checker; both greps shown to have been non-zero before.</done>
</task>

</tasks>
