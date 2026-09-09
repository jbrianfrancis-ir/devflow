<!-- .planning/quick/015-03-checker-rules.md -->
---
phase: quick-015
plan: 03
wave: 2
depends_on: [015-02]
files_modified:
  - plugins/devflow/references/plan-format.md
  - plugins/devflow/agents/flow-plan-checker.md
  - plugins/devflow/skills/flow-plan/SKILL.md
autonomous: true
requirements: [R5, R6, R4-wiring]
must_haves:
  truths:
    - "resolving a backstop_truth requires the resolution to land as a must_haves.truths entry the verifier grades, not a YAML comment or a human-check"
    - "resolving a backstop truth emits the complete list of contradicting sites across the phase, not the first one found"
    - "the checker resolves every NN-MM mention in plan prose; a reference to a nonexistent plan is blocking"
    - "a reference asserting another plan does X, where X is in neither that plan's files_modified nor its truths, is blocking"
    - "/flow-plan can spawn flow-prober for an assumption headed for an ARCHITECTURE.md pin, and records an unprobeable assumption as unverified"
  artifacts:
    - plugins/devflow/references/plan-format.md
    - plugins/devflow/agents/flow-plan-checker.md
  key_links:
    - "flow-plan-checker's new checks cite plan-format.md for their rule text"
    - "/flow-plan's research step offers flow-prober alongside flow-researcher"
---

<objective>
R5: a resolved human decision must reach the plans and be graded, not just be recorded.
R6: cross-plan references must resolve. Plus wire the R4 prober into /flow-plan.
</objective>

<context>
- /home/brianf/Work/devflow/.planning/ARCHITECTURE.md  (law; "docs are pointers, never copies")
- /home/brianf/Work/devflow/plugins/devflow/references/plan-format.md  (## must_haves, ### backstop_truths, ## Gates)
- /home/brianf/Work/devflow/plugins/devflow/agents/flow-plan-checker.md  (checks 1, 1b, 3, 5, 5b, 6)
- /home/brianf/Work/devflow/plugins/devflow/skills/flow-plan/SKILL.md  (step 1 Discuss, step 2 Research, step 4 Check)
- /home/brianf/Work/devflow/plugins/devflow/agents/flow-prober.md  (created by plan 015-02 — read it before wiring)

R5's motivating case: a human resolved a backstop_truth — never re-display a stored credential.
It was recorded in DECISIONS.md, REQUIREMENTS.md and PROJECT.md. Four plans still specified
displaying it, one with a mandatory reveal control that made the resolution unsatisfiable. A
decision recorded but not propagated is worse than one never asked, because the audit trail says
it was settled.

R6's two historical cases, both load-bearing, both must be caught by the rule as written:
(a) plan 01-01 said "plan 01-05 replaces its body with the settings screen" when no 01-05 existed —
an executor following it leaves a placeholder awaiting a plan that never runs;
(b) "01-08 adds the Keychain entitlement wiring" when 01-08 touched only test files.
</context>

<tasks>

<task type="auto">
  <name>Task 1: R5 — a resolved backstop truth becomes a graded truth</name>
  <files>plugins/devflow/references/plan-format.md, plugins/devflow/skills/flow-plan/SKILL.md</files>
  <action>
In plan-format.md's `### backstop_truths` section, add the resolution rule. The section already
explains why the tag must be structured rather than prose ("a truth the verifier will grade green
like any other") — the resolution rule is the same argument applied to the answer, so state it as
the closing of that loop, not as a new idea:

- When a human resolves a backstop truth, the resolution lands as a `must_haves.truths` entry,
  where the verifier grades it. Not a YAML comment, not a note in the objective, not a
  `<human-check>` — each of those records the answer somewhere nothing reads back.
- The backstop entry is removed from `backstop_truths` when it moves to `truths`; one truth
  belongs to exactly one list, which the file already says — point at that rule, don't restate it.
- Note the interaction with the frozen-anchors rule that must_haves are frozen once execution
  starts: a resolution before execution is the normal path; after execution starts it is the
  documented human gate, not a quiet edit.

In flow-plan/SKILL.md step 1 (Discuss), where an answered marker is already resolved in
REQUIREMENTS.md and logged as D-NN, extend that sentence: the answer ALSO lands as a
`must_haves.truths` entry in the plan that implements it, and every plan in the phase is
re-scanned for statements the resolution now contradicts. Report **every** contradicting site,
not the first — the acceptance criterion is the complete list, because the motivating failure was
four plans contradicting one resolution and a reveal control that made it unsatisfiable. An
unresolvable contradiction (a plan whose stated component cannot satisfy the resolution) is an
escalation, not something the planner quietly reconciles.
  </action>
  <verify>
`grep -ni 'backstop' plugins/devflow/references/plan-format.md` still matches the section, and
reading it shows the resolution rule; `grep -ni 'contradict' plugins/devflow/skills/flow-plan/SKILL.md` matches
inside step 1 — confirm by reading step 1, not by the grep alone.
`python3 scripts/check-links.py` → 0 failures, reference count >= 225.
`python3 scripts/validate-plugin.py` → exit 0, 13 Claude agents.
  </verify>
  <falsify>
`git show HEAD:plugins/devflow/skills/flow-plan/SKILL.md | grep -ci contradict` must print 0, and
`git show HEAD:plugins/devflow/references/plan-format.md | grep -ci 'resolution'` — if non-zero,
that grep does not distinguish before from after. Substitute a distinctive phrase you actually
wrote, re-run, and report the substitution in your SUMMARY. Do not skip this: a grep for a common
word is exactly the vacuous guard this whole change set exists to stop.
  </falsify>
  <done>plan-format.md requires a resolved backstop truth to become a graded truths entry; step 1 re-scans the phase and reports every contradicting site; both greps shown to distinguish before from after.</done>
</task>

<task type="auto">
  <name>Task 2: R5 + R6 checker rules</name>
  <files>plugins/devflow/agents/flow-plan-checker.md</files>
  <action>
Add two checks in the file's existing terse one-line-per-check voice. This file is dense and
every line is load-bearing — do not restate plan-format.md's rule text, cite it. Do not touch the
`Return exactly one of:` contract or the frontmatter.

- Extend check **1b** (unresolved markers) with the resolved case: when a marker on this phase's
  requirements has been RESOLVED, the resolution appears as a `must_haves.truths` entry in the
  plan implementing it, and no plan in the phase states something the resolution contradicts.
  Report **every** contradicting site, not the first — a partial list reads as a complete one.
  A resolution recorded only as a comment, an objective note, or a human-check is an issue.
- Add check **6b, Cross-plan references**: resolve every `NN-MM` mention in plan prose. A
  reference to a plan that does not exist in this phase is blocking. A reference asserting another
  plan does X, where X appears in neither that plan's `files_modified` nor its `must_haves.truths`,
  is blocking. Give the rule its reason in a clause: an executor following such a reference leaves
  work parked on a plan that will never do it. Both historical shapes must be caught — a
  nonexistent target, and an existing target that does not do the named thing.
  </action>
  <verify>
`grep -n '6b' plugins/devflow/agents/flow-plan-checker.md` matches;
`grep -ni 'contradict' plugins/devflow/agents/flow-plan-checker.md` matches;
`grep -q 'Return exactly one of' plugins/devflow/agents/flow-plan-checker.md` exits 0 (contract intact);
`head -6 plugins/devflow/agents/flow-plan-checker.md | grep -q 'model: opus'` exits 0.
`python3 scripts/validate-plugin.py` → exit 0.
Then a behavioural check, since greps only prove text exists: write two throwaway plan stubs in a
scratch dir OUTSIDE the repo — one referencing a nonexistent `99-99`, one asserting `NN-MM adds X`
where that plan's frontmatter lists neither — and confirm by reading your new rule that both are
blocking under it as written. Quote the rule and the two stubs in your SUMMARY.
  </verify>
  <falsify>
`git show HEAD:plugins/devflow/agents/flow-plan-checker.md | grep -c '6b'` must print 0 and
`| grep -ci contradict` must print 0. If either is non-zero, substitute a distinctive phrase and
report it. Additionally confirm validate-plugin.py grades this file: set `model: opus` to
`model: bogus`, run the validator, confirm it errors naming the allowed values, and restore.
  </falsify>
  <done>Check 1b covers resolved markers and requires every contradicting site; check 6b catches both historical reference shapes; contract and frontmatter intact; validator shown to grade the file.</done>
</task>

<task type="auto">
  <name>Task 3: wire flow-prober into /flow-plan</name>
  <files>plugins/devflow/skills/flow-plan/SKILL.md</files>
  <action>
Read `plugins/devflow/agents/flow-prober.md` first (plan 015-02 created it) so this matches its
actual contract rather than an assumed one.

In step 2 (Research), which currently offers `flow-researcher` for unknowns worth verifying, add
the probe path: `flow-researcher` reads documentation; `flow-prober` runs something. Spawn
flow-prober for an assumption **destined to become an ARCHITECTURE.md pin** — the requirement's
own trigger — passing it ONE assumption per probe, since its contract requires changing one
variable at a time. Two assumptions means two probes.

State the outcome handling, which is the part that matters: a probe returns command, exit code and
verbatim output, and an assumption it could not probe is recorded as **unverified** rather than
pinned. Say where that lands so it is not lost — the RESEARCH.md this step already writes is the
natural home; an unverified assumption that reaches ARCHITECTURE.md as a pin is the failure this
prevents.

Keep it proportionate to the step's existing length — this is one added path in a short step, not
a new section. Follow the skill's existing rule of passing subagents paths, never contents.
  </action>
  <verify>
`grep -n 'flow-prober' plugins/devflow/skills/flow-plan/SKILL.md` matches inside step 2 — confirm
by reading step 2; `grep -ni 'unverified' plugins/devflow/skills/flow-plan/SKILL.md` matches.
`python3 scripts/check-links.py` → 0 failures, reference count >= 225 (a link to the agent file,
if you added one, resolves).
`python3 scripts/validate-plugin.py` → exit 0, 13 Claude agents.
`python3 -m unittest discover -s tests 2>&1 | tail -3` → OK, 0 failures.
  </verify>
  <falsify>
`git show HEAD:plugins/devflow/skills/flow-plan/SKILL.md | grep -c 'flow-prober'` must print 0.
Then prove check-links.py covers this file: temporarily point a link in the step at a nonexistent
path, run it, confirm a non-zero failure count, restore, confirm 0. If it does not catch it, this
file's links are unguarded — report that rather than assuming they are checked.
  </falsify>
  <done>Step 2 offers flow-prober for pin-bound assumptions, one assumption per probe, and routes an unprobeable one to RESEARCH.md as unverified; links green and shown to be graded.</done>
</task>

</tasks>
