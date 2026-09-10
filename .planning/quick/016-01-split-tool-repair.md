<!-- .planning/quick/016-01-split-tool-repair.md -->
---
phase: quick-016
plan: 01
wave: 1
depends_on: []
files_modified:
  - plugins/devflow/scripts/flow-split-plan.py
  - tests/test_flow_split_plan.py
autonomous: true
requirements: [R9-repair]
must_haves:
  truths:
    - "the tool splits a plan written from templates/plan.md, preserving its leading HTML path comment on both output plans"
    - "the tool works on untracked plan files, which is their state when /flow-plan offers the split"
    - "an ISO date or line range in plan prose does not make the tool refuse to split"
    - "frontmatter keys the tool does not model (user_setup and any other) survive the split"
    - "the split-off plan depends on its source when their tasks share files, so the two never run in the same wave"
    - "tests are built from hand-written fixtures, not from the tool's own serializer"
    - "each test fails against a deliberately broken implementation of the behavior it covers"
  artifacts: [plugins/devflow/scripts/flow-split-plan.py, tests/test_flow_split_plan.py]
  key_links: ["tests assert the partition of tasks and must_haves between source and new plan"]
---

<objective>
Repair the five blocking defects an independent review reproduced in flow-split-plan.py, and
rewrite its tests so they can actually fail.
</objective>

<context>
- /home/brianf/Work/devflow/.planning/ARCHITECTURE.md — law. Python 3.9+ STDLIB ONLY, no deps.
- /home/brianf/Work/devflow/plugins/devflow/templates/plan.md — the shape of a real plan. LINE 1 IS AN HTML COMMENT.
- /home/brianf/Work/devflow/plugins/devflow/references/plan-format.md — frontmatter contract, waves.
- /home/brianf/Work/devflow/plugins/devflow/skills/flow-plan/SKILL.md step 4 — the only call site.
- /home/brianf/Work/devflow/tests/test_flow_hooks.py — house test style.

FIVE BLOCKING DEFECTS, each REPRODUCED by review. Do not re-derive; fix them.
B5 `split_frontmatter` (~line 43) demands `---` on line 1. Every plan from templates/plan.md
   starts with `<!-- .planning/phases/... -->`, so the tool aborts with "missing frontmatter
   opening '---'" on every real plan. Same throw for tail plans (~line 423). The tool's own
   `rewrite_header_comment` (~line 215) assumes that comment EXISTS — the two are mutually
   contradictory. Also `src_text_out = src_fm_out + src_body_out` (~line 400) discards anything
   before the frontmatter, dropping the comment even when parsing succeeds.
B6 `git_mv` (~line 463) fails on untracked files: `fatal: not under version control`. Plans are
   uncommitted when /flow-plan step 4 offers the split (they commit at step 6), so the split is
   impossible at its only call site.
B7 `NN_MM_RE = \b(\d{2,})-(\d{2,})\b` (~line 230) has no phase-prefix anchor, so `validate`
   treats `2026-09-09` and `lines 12-40` as plan references and refuses to write:
   "dangling reference to nonexistent plan 12-40". Any date or range in any plan in the phase
   permanently blocks that phase's splits.
B8 `format_frontmatter` (~line 132) rebuilds from a fixed eight-field list, silently dropping
   `user_setup` (plan-format.md declares it: external things the human must configure —
   accounts, secrets — surfaced before execution). Any unmodelled key is lost the same way.
B3 (architecture) The new plan is written with the source's `wave` and `depends_on` VERBATIM and
   no edge back to the source (~line 387), so tasks that were strictly ordered inside one plan
   become two same-wave plans /flow-execute runs in parallel. The tool already computes
   `moving_files ∩ staying_files` (~line 336) and uses it only for a warning.

TWO should-fix, same file:
- The write phase has no rollback for OSError (~line 476): `except PlanError` at ~468 covers only
  git_mv, so a failing `Path.rename` or `tmp.write_text`/`tmp.replace` escapes uncaught AFTER
  renames are on disk — the half-renumbered state the module docstring calls impossible.
- Both output plans inherit `autonomous` (~line 389), so when the only checkpoint task moves out
  the source stays `autonomous: false` with no checkpoint task.

TESTS ARE THE OTHER HALF. Review mutated the implementation and found the existing 7 tests pass
against BOTH of these: (a) `staying_tasks, moving_tasks = tasks, tasks[args.after:]` — source
keeps every task, new plan duplicates them, nothing ever gets smaller; (b) `split_list` returning
`[], [everything]` — nothing moves and the new plan ships with empty `must_haves.truths`. The
union-comparison test is blind to WHERE entries land, so it cannot tell a correct split from no
split. And fixtures are built with the tool's own `format_frontmatter`, so the serializer is only
ever compared against itself.
</context>

<tasks>

<task type="auto">
  <name>Task 1: parse and preserve real plan files</name>
  <files>plugins/devflow/scripts/flow-split-plan.py</files>
  <action>
Fix B5 and B8 together — both are frontmatter fidelity.

`split_frontmatter`: accept and RETURN any leading preamble before the opening `---` (the HTML
path comment, blank lines, anything). Re-emit it ahead of the rebuilt frontmatter on BOTH output
plans, so the source keeps its comment and the new plan gets one. Make `rewrite_header_comment`
consistent with this rather than assuming the comment is always there — a plan with no preamble
must still split.

`format_frontmatter`: carry through every key it does not model. Emit the modelled fields in the
current order, then any unmodelled key verbatim. `user_setup` in particular must survive on the
source plan; state in a comment why (it surfaces credentials a human must set before execution,
so losing it silently starts a phase without them).
  </action>
  <verify>
Build a fixture phase dir OUTSIDE the repo whose plans are copied from
`plugins/devflow/templates/plan.md` (real shape: HTML comment line 1) with `user_setup` added to
one. Split it. Assert: both output plans start with an HTML comment line; `user_setup` is present
in the source plan's frontmatter with its original value; the tool exits 0.
  </verify>
  <falsify>
Run the SAME fixture against the pre-fix tool (`git show HEAD:plugins/devflow/scripts/flow-split-plan.py`
written to a temp path). It MUST exit non-zero with "missing frontmatter opening '---'". If it
does not, your fixture is not shaped like a real plan — fix the fixture, not the assertion, and
say so in your SUMMARY. Then re-add `user_setup` handling removal only, and confirm the
user_setup assertion alone fails.
  </falsify>
  <done>Real template-shaped plans split; preamble preserved on both outputs; unmodelled frontmatter keys survive; pre-fix tool shown to abort on the same fixture.</done>
</task>

<task type="auto">
  <name>Task 2: work on untracked plans, and stop matching dates as plan ids</name>
  <files>plugins/devflow/scripts/flow-split-plan.py</files>
  <action>
B6: choose the mover per file. Use `git ls-files --error-unmatch <path>` (or equivalent) to ask
whether the file is tracked; tracked → `git mv` so history follows, untracked → `Path.rename`.
A mixed phase dir must work. Keep the existing rollback behavior for whichever mover ran.

B7: anchor the reference regex to the phase. Build the plan-reference pattern from the phase
`prefix` the tool already computes for `compute_rename_map`, so only `<prefix>-<MM>` tokens are
treated as plan references. `2026-09-09`, `12-40`, `AB-01-03` and `5.01-04.x` must all survive a
split untouched — review verified the current regex rewrites the last two. Apply the same anchored
pattern in BOTH `validate` and the prose rewriter, so they cannot disagree about what a reference
is.
  </action>
  <verify>
Two fixtures OUTSIDE the repo. (1) Untracked: `git init` a repo, write plan files, do NOT add
them, run the split — exits 0 and the files are renumbered on disk. (2) Prose: a plan containing
`see RFC dated 2026-09-09`, `lines 12-40`, `ticket AB-01-03` and `version 5.01-04.x` plus one
REAL reference to a plan that shifts — split, then assert the real reference was rewritten and all
four decoys are byte-identical.
  </verify>
  <falsify>
Against the pre-fix tool: fixture (1) must fail with a `git mv` / "not under version control"
error, and fixture (2) must fail with "dangling reference to nonexistent plan". Record both
messages. If either pre-fix run SUCCEEDS, you have not reproduced the defect the review found —
stop and report that rather than claiming a fix.
  </falsify>
  <done>Untracked and tracked plans both split; only `<prefix>-MM` tokens are treated as references; all four decoy shapes survive; pre-fix tool shown to fail both fixtures.</done>
</task>

<task type="auto">
  <name>Task 3: the split-off plan must not race its source</name>
  <files>plugins/devflow/scripts/flow-split-plan.py</files>
  <action>
B3: the new plan currently inherits the source's `wave` and `depends_on` with no edge back, so an
ordered plan becomes two parallel ones. plan-format.md: same-wave plans "must be fully
independent: disjoint files_modified, and no shared mutable resource".

The tool already computes the moved/staying file intersection. Use it as the decision: when the
moved tasks' `<files>` intersect the staying tasks' `<files>`, the new plan gets
`depends_on: [<source-id>]` and `wave: <source wave> + 1`, and every plan whose wave must follow
is cascaded. When the sets are disjoint the plans are genuinely independent and may share the
source's wave — say so in a comment, because that is the case the fake-edge rule in plan-format.md
tells you not to over-constrain.

Whatever you choose, `validate` must prove it before writing: no cycles, and
`wave == max(dependency wave) + 1` for every plan in the phase.

Also fix the two should-fix items in this file:
- Recompute `autonomous` per side from whether that side's tasks contain a `type="checkpoint:*"`
  task, rather than both sides inheriting the source's value.
- Extend the write-phase rollback to `OSError`, not just `PlanError`, and write every file to a
  `.tmp` sibling before renaming, so a mid-write failure cannot leave the phase half-renumbered.
  The module docstring already promises all-or-nothing; make that true.
  </action>
  <verify>
Fixture OUTSIDE the repo with an ordered plan: T1 creates `src/db/repo.ts`, T2 tests it, T3 adds a
route importing `src/db/repo.ts`, T4 tests the route — so moved and staying tasks share a file.
Split `--after 2`. Assert the new plan has `depends_on: [<source>]` and a wave strictly greater
than the source's, and that the tail's waves are consistent. Then a second fixture whose moved and
staying tasks touch disjoint files: assert it is NOT given a spurious edge.
Then force an OSError mid-write (e.g. make one target path a directory) and assert the phase dir
is byte-identical afterwards.
  </verify>
  <falsify>
Revert your edge logic so the new plan copies `wave`/`depends_on` verbatim, re-run the first
fixture, and confirm the assertion FAILS (the two plans land in the same wave). Restore.
Separately, remove the OSError from the rollback `except` and confirm the mid-write fixture leaves
the directory changed — proving that test grades the guarantee rather than passing by luck.
  </falsify>
  <done>Ordered splits produce a real edge and a later wave; disjoint splits do not; autonomous recomputed per side; all-or-nothing holds against a forced OSError, and each was shown to fail when the fix is removed.</done>
</task>

<task type="auto">
  <name>Task 4: rewrite the tests so they can fail</name>
  <files>tests/test_flow_split_plan.py</files>
  <action>
The existing suite passes against a tool that never moves anything. Rewrite it so it grades
behavior.

- **Hand-written fixtures.** Stop building fixtures with the tool's own `format_frontmatter`.
  Write plan files as literal strings in the test, shaped like `templates/plan.md` (HTML comment
  line 1, real frontmatter, `<tasks>` with `<task>` elements). At least one test must pin the new
  plan's frontmatter against a literal expected block, so a drifting serializer cannot round-trip
  green.
- **Assert the partition, not the union.** The new plan CONTAINS the moved tasks (renumbered
  Task 1..n) and the source NO LONGER does; the source shrank in bytes; each side's
  `must_haves`/`files_modified` name that side's files. The union check may stay as an
  additional no-loss assertion but must not be the only one.
- Cover, each with its own test: preamble preserved; `user_setup` survives; untracked files split;
  decoy tokens (`2026-09-09`, `12-40`, `AB-01-03`, `5.01-04.x`) unchanged while a real reference
  is rewritten; ordered split gets a depends_on edge and a later wave; disjoint split does not;
  `autonomous` recomputed per side; `--dry-run` writes nothing; a dangling result writes nothing;
  a forced OSError mid-write leaves the directory byte-identical.
  </action>
  <verify>
`python3 -m unittest tests.test_flow_split_plan -v 2>&1 | tail -5` → OK, 0 failures, and the test
count is higher than the 7 it replaces. Then the full suite:
`python3 -m unittest discover -s tests 2>&1 | tail -3` → OK, 0 failures, 0 errors.
  </verify>
  <falsify>
Run BOTH mutations the review used, one at a time, restoring after each:
(a) `staying_tasks, moving_tasks = tasks, tasks[args.after:]` — source keeps every task and the
new plan duplicates them;
(b) `split_list` returning `[], [everything]` — nothing ever moves.
Each MUST now fail at least one test, and you must name which test caught it. If either still
passes the whole suite, the rewrite did not achieve its purpose — keep going, and report the
mutation that still survives rather than reporting the suite green.
  </falsify>
  <done>Suite is hand-fixture based, asserts the partition, covers every repaired defect, and both review mutations are caught by named tests.</done>
</task>

</tasks>
