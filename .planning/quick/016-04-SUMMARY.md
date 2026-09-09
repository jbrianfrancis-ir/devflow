---
plan: quick-016-04
status: complete
agent: executor/claude/sonnet
commits: [88edf73, 86e5db6, 6f589d4]
deviations: []
human_checks: []
deferred: []
---
Task 1 judgment call: checked `claude --help` (v2.1.266) — no `--sandbox`, and `--add-dir`
only adds allowed directories, doesn't confine below cwd, and never confines Bash (which a
prober needs to build anything; `--restricted` removes Bash unless named, but doesn't
confine it either). No flag genuinely constrains writes without breaking the role, so I took
the scoped-claim branch: hosts.md, flow-prober.md, and flow-agent.py's comments now say
codex sandboxes the scratch root for real (`--sandbox`/`--cd`) while claude only roots cwd
there, held by the prompt contract.

Task 2: folded SCRATCH_ROLES into the shared parse loop; missing/unparseable literal is now
`err(...)` instead of an empty-set fallback. Mutations (1) rename and (2) reformat-with-brace-
in-comment: pre-fix validator exit 0 on both (fails open, confirmed); post-fix exit 1 on both,
naming SCRATCH_ROLES. Mutation (3) remove prober from WRITE_ROLES: exit 1 on both pre- and
post-fix (message: "SCRATCH_ROLES not also in WRITE_ROLES: ['prober']").

Task 3: added 3 offline tests (13→16 in FlowAgentTests, 15→18 total incl. gated smoke tests);
`DEVFLOW_SMOKE` still gates the only live-CLI tests. Full suite: 220 tests OK. Falsified both
ways: removing scratch handling breaks the new rooting test; deleting prober from hosts.md's
Write-roles list still trips the validator's role-list cross-check.
