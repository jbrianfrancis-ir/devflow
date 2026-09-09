<!-- .planning/quick/016-01-SUMMARY.md — cap 1.5KB. Frontmatter first: others read only frontmatter. -->
---
plan: quick-016-01
status: complete
agent: executor/claude/sonnet
commits: [7698063, c1579bd, 9fadd92, bd26c29]
deviations:
  - "[Rule 1] discover_plans: added path.is_file() check — a directory matching
    NN-MM-PLAN.md was misparsed as a plan (blocked the forced-OSError fixture)."
  - "[Rule 1] rename phase's except now also catches OSError, for the same
    all-or-nothing guarantee Task 3 asked for on the write phase."
human_checks: []
deferred: []
---
Fixed all 5 blocking defects (B3, B5-B8) + 2 should-fix items in
flow-split-plan.py. Reproduced each pre-fix ("missing frontmatter opening '---'",
"fatal: not under version control", "dangling reference to nonexistent plan
12-40"). Verified: preamble+user_setup preserved; untracked/mixed git repos
split; date/range/ticket/version decoys survive while real refs rewrite;
ordered splits get depends_on+later wave, disjoint don't; autonomous
recomputed per side; forced IsADirectoryError mid-write rolls back cleanly.

Rewrote tests: 21 hand-fixture tests (was 7, serializer-derived). Both review
mutations reproduced and caught by named tests. Full suite: 211 tests, 0
failures/errors (2 pre-existing unrelated skips).
