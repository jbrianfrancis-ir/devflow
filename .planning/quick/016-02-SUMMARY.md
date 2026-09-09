<!-- .planning/quick/016-02-SUMMARY.md -->
---
plan: quick-016-02
status: complete
agent: executor/claude/sonnet
commits: [989b9b6, 5f82743, c00544c]
deviations: []
human_checks: []
deferred:
  - "Hit reports (file, pattern_class) carry no line number, matching the credential path
    Task 1 said to mirror exactly, though conventions.md/must_haves say 'file+line+class'."
  - "conventions.md still says Forbidden-pattern enforcement covers tracked files incl.
    .planning/; Task 1 scoped this implementation to the outgoing diff only. Unreconciled;
    likely 016-03's (contract fixes)."
---
Task 1 falsified live: pre-fix guard exited 0 on a staged FORBIDDENLITERAL (real bug).
Added load_forbidden_patterns()/iter_forbidden_entries(), threaded into scan()'s existing
hit path (re.compile'd, never shelled): hit exits 2 naming file+prose never the literal;
malformed regex exits 2 could-not-check; missing ARCHITECTURE.md and a clean diff with
patterns configured both exit 0. Removing the re.error handler un-blocked the fixture.
Task 2: 6 tests added (40->46 in test_flow_hooks; full suite 217 OK, 2 pre-existing skips).
Disabling the pattern loop turned 2 of them red by name.
Task 3: SKILL.md cut to a pointer; conventions.md gained the data-not-shell rule, dropped
duplicated text. check-links 232 refs/0 failures before+after; validate-plugin OK.
