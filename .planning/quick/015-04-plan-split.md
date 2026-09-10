<!-- .planning/quick/015-04-plan-split.md -->
---
phase: quick-015
plan: 04
wave: 3
depends_on: [015-03]
files_modified:
  - plugins/devflow/scripts/flow-split-plan.py
  - tests/test_flow_split_plan.py
  - plugins/devflow/references/plan-format.md
  - plugins/devflow/skills/flow-plan/SKILL.md
autonomous: true
requirements: [R9]
must_haves:
  truths:
    - "an over-cap plan can be split into two by one supported command, without hand-editing every downstream plan"
    - "splitting renumbers the tail plans and rewrites plan/wave/depends_on and cross-references so nothing dangles"
    - "the size check re-runs after any hand edit, not only after a planner round"
    - "the split tool refuses to write anything when the split would leave a dangling reference"
  artifacts:
    - plugins/devflow/scripts/flow-split-plan.py
    - tests/test_flow_split_plan.py
  key_links:
    - "plan-format.md's cap paragraph points at the split tool as the supported remedy"
---

<objective>
R9: the 4KB plan cap is enforced with no supported remedy, so correct plans get hand-trimmed under
byte pressure — which introduced two contradicting truths in the source phase. Give splitting an
implementation.
</objective>

<context>
- /home/brianf/Work/devflow/.planning/ARCHITECTURE.md  (law: Python 3.9+, STDLIB ONLY, no dependencies; repo tooling under scripts/, shipped tooling under plugins/devflow/scripts/, tests under tests/)
- /home/brianf/Work/devflow/plugins/devflow/scripts/flow-agent.py  (house style for a shipped stdlib script — argparse, terse, no deps)
- /home/brianf/Work/devflow/plugins/devflow/references/plan-format.md  (## Frontmatter, ## Waves, ## Tasks split signals, 4KB cap)
- /home/brianf/Work/devflow/plugins/devflow/skills/flow-plan/SKILL.md  (step 4 runs `wc -c` and folds over-cap files into the issue list)
- /home/brianf/Work/devflow/tests/test_flow_hooks.py  (house style for tests: unittest, real fixtures in temp dirs)

The cap protects executor context, so raising it is not the answer and is out of scope. Splitting
is already the documented remedy; nothing implements it, so it is done by hand across eleven files
and gets skipped under pressure.

YAML: stdlib only means no PyYAML. Plan frontmatter is a small, known shape — parse the fields you
need with line-oriented code (the same pragmatic approach validate-plugin.py takes to frontmatter),
and do not attempt a general YAML parser.
</context>

<tasks>

<task type="auto">
  <name>Task 1: implement flow-split-plan.py</name>
  <files>plugins/devflow/scripts/flow-split-plan.py</files>
  <action>
A stdlib-only Python 3.9+ CLI that splits one over-cap plan into two and repairs the phase around
it. Match `flow-agent.py`'s house style: argparse, module docstring, terse, no dependencies.

Interface: take the phase directory and the plan id to split, plus which tasks move to the new
plan (e.g. `--after 2` meaning tasks 3..n move out). Support `--dry-run` printing what would
change without writing.

Behaviour:
- Insert the new plan immediately after the source plan and **shift the tail**: every plan with a
  higher number moves up by one, and its filename, its `plan:` field, and every `depends_on`
  entry naming a shifted plan are rewritten to match. Rename files with `git mv` when the phase
  dir is inside a git repo, so history follows.
- The new plan inherits the source's `phase`, `wave`, `requirements` and `depends_on`; move the
  extracted tasks' `files_modified` entries to it, and split `must_haves` so each list entry
  follows the plan that now produces it. Where ownership is genuinely ambiguous, leave the entry
  on the SOURCE plan and print a warning naming it — never drop it, and never guess silently.
  A dropped truth is the R3 failure this change set already guarded against; do not reintroduce
  it here.
- Rewrite `NN-MM` cross-references in every plan's prose to their post-shift numbers.
- **Refuse to write anything if the result would dangle**: after computing the new state and
  before touching disk, verify every `depends_on` target exists, every `NN-MM` prose reference
  resolves, and no wave ordering is violated (`wave = max(dependency wave) + 1`). On any failure,
  print what would dangle and exit non-zero having written nothing. All-or-nothing, so a failed
  split never leaves the phase half-renumbered.
- Report the resulting byte size of every plan it wrote, so the caller can see whether the split
  actually got under the cap.

Fail-closed per conventions.md: an unreadable plan, unparseable frontmatter, or a `git mv` that
fails is an error that stops the run — never a partial write and never a silent skip.
  </action>
  <verify>
Build a throwaway phase directory in a scratch dir OUTSIDE the repo: four plans (01-01..01-04)
with real frontmatter, a `depends_on` chain, and prose in 01-01 referencing `01-04`. Split 01-02.
Then assert, by reading the resulting files: 01-04 became 01-05, 01-03 became 01-04, the new plan
is 01-03, every `depends_on` still names an existing plan, 01-01's prose reference now says 01-05,
and no `must_haves` entry from the original four was lost (diff the union of entries before and
after — it must be equal). Run `--dry-run` first and confirm it wrote nothing.
Then delete the scratch dir.
  </verify>
  <falsify>
Two mutations, each restored after:
(1) Make the split produce a dangling reference on purpose — point a `depends_on` in the fixture at
a plan that will not exist post-shift — and confirm the tool exits NON-ZERO and wrote NOTHING
(re-read every fixture file and confirm byte-identical to before the run). If it writes a
half-renumbered phase, the all-or-nothing guarantee is not implemented; fix it, do not report it.
(2) Delete one `must_haves.truths` entry from the tool's output by hand and re-run your
before/after union comparison — it MUST report inequality. If it does not, the comparison is
vacuous and proves nothing about lost entries; fix the check and say so in your SUMMARY.
  </falsify>
  <done>Tool splits and renumbers correctly, rewrites prose references, refuses to write on a dangling result, and its no-lost-entries check was shown to be able to fail.</done>
</task>

<task type="auto">
  <name>Task 2: tests for the split tool</name>
  <files>tests/test_flow_split_plan.py</files>
  <action>
unittest, stdlib only, real fixtures in temp directories — follow `tests/test_flow_hooks.py`'s
shape (a fixture class with `addCleanup`, subprocess invocation of the script, assertions on exit
code and output). Do not mock the filesystem.

Cover: the tail shift renumbers files and `plan:` fields; `depends_on` entries following a shifted
plan are rewritten; prose `NN-MM` references are rewritten; no `must_haves` entry is lost across a
split; `--dry-run` writes nothing; a split that would dangle exits non-zero and writes nothing;
each written plan's reported byte size matches the file on disk.
  </action>
  <verify>
`python3 -m unittest tests.test_flow_split_plan -v 2>&1 | tail -5` → OK, 0 failures, 0 errors, and
the test count is what you wrote. Then the full suite:
`python3 -m unittest discover -s tests 2>&1 | tail -3` → OK, 0 failures, 0 errors.
  </verify>
  <falsify>
For EACH behaviour above, break the tool's implementation of it one at a time and confirm the
corresponding test fails, restoring after each. A test suite that passes against a deliberately
broken tool is the exact defect this whole change set exists to stop, so do not accept "all green"
as evidence on its own. Record in your SUMMARY, per behaviour, the mutation you made and whether
the test caught it — and name any behaviour whose test did NOT catch its mutation rather than
quietly fixing the number.
  </falsify>
  <done>Every listed behaviour has a test, the full suite is OK, and each test was shown to fail against a deliberately broken implementation of the thing it covers.</done>
</task>

<task type="auto">
  <name>Task 3: point the cap at its remedy, and re-check size after hand edits</name>
  <files>plugins/devflow/references/plan-format.md, plugins/devflow/skills/flow-plan/SKILL.md</files>
  <action>
Two small prose edits closing R9's second half.

plan-format.md: where the 4KB cap is described (opening paragraph, and the split signals in
`## Tasks`), name `plugins/devflow/scripts/flow-split-plan.py` as the supported way to split, and
state the rule the source phase violated: **trimming prose to satisfy the cap degrades the plan
the cap exists to protect** — repeated hand-trimming there produced two contradicting truths, one
asserting credentials repopulate on relaunch beside another forbidding it. Split, don't trim.

flow-plan/SKILL.md step 4: the size check currently runs once per planner round. State that it
re-runs after **any** hand edit to a plan, not only after a planner round — a plan edited by hand
between rounds is unmeasured, and that is when trimming happens.

Keep both edits short and pointer-shaped per ARCHITECTURE; the tool's usage lives in the tool.
  </action>
  <verify>
`grep -n 'flow-split-plan' plugins/devflow/references/plan-format.md plugins/devflow/skills/flow-plan/SKILL.md` matches in both;
read step 4 and the cap paragraph to confirm the rules read as intended.
`python3 scripts/check-links.py` → 0 failures, reference count >= 225 — this matters here: you
added backticked repo-relative script paths, which the checker resolves, so a typo in the path
turns it red.
`python3 scripts/validate-plugin.py` → exit 0, 13 Claude agents.
  </verify>
  <falsify>
`git show HEAD:plugins/devflow/references/plan-format.md | grep -c 'flow-split-plan'` must print 0.
Then prove check-links.py actually resolves the script path you wrote: change one character in it
(`flow-split-plan.py` → `flow-split-plann.py`), run check-links.py, confirm a non-zero failure
count naming that token, then restore and confirm 0 failures. If the typo does NOT turn it red,
the path is not being checked — say so in your SUMMARY rather than trusting it.
  </falsify>
  <done>Both files point at the split tool as the remedy and state split-don't-trim; step 4 re-checks size after hand edits; the script path was shown to be link-checked.</done>
</task>

</tasks>
