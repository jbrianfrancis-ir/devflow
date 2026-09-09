---
plan: quick-015-04
status: complete
agent: executor/claude/sonnet
commits: [f0975b1, be9098b, 8caa7ae]
deviations: []
human_checks: []
deferred: []
---
Implemented `plugins/devflow/scripts/flow-split-plan.py` (stdlib-only): splits an
over-cap plan, shifts/renumbers the phase tail, rewrites `plan:`/`depends_on`/prose
`NN-MM` references, splits `files_modified`/`must_haves` by task attribution (ambiguous
entries stay on source with a printed warning), refuses to write on any dangling
reference or wave-order violation, and reports each written plan's byte size.

Task 1 falsify: forced dangling `depends_on` -> exit 2, fixture byte-identical after.
Hand-deleted a `must_haves.truths` entry -> union check correctly reported inequality
(15 -> 14, missing entry named).

Task 2: `tests/test_flow_split_plan.py`, 7 tests, full suite 193 tests OK (2 skipped,
pre-existing). All 7 behaviours' mutations caught (see commit be9098b for detail) —
note mutation 2 (depends_on rewrite disabled) surfaced as a FileNotFoundError, not a
direct assertion failure, because the tool's own wave-ordering guard refused the
inconsistent result before writing; still a caught mutation, via a different guard.

Task 3: plan-format.md + flow-plan/SKILL.md point at the tool as the split remedy and
state split-don't-trim; step 4 re-checks size after any hand edit. check-links.py:
231 references checked (was 225), 0 failures; typo'd path confirmed red (2 failures),
restored to 0. validate-plugin.py exit 0, 13 agents.

No version bump in this plan (deferred to the one manifest bump at end of quick-015).
