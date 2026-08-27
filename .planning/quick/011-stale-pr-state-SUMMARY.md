---
plan: 11
status: complete
agent: executor/claude/claude-sonnet-5
commits: [1a33720, a90da09, 7d70b65, 8e4d92f]
deviations: []
human_checks: []
deferred: []
---
Closed the stale-external-state hole: autonomy.md now has "External state is a cache,
never evidence" after Human gates. flow-next re-reads PR state live via `gh pr view`
before rules 9-11 (added rule 11 for out-of-band merge, plus a closed-unmerged branch),
`gh` failure is BLOCKED, and rule 2 no longer re-surfaces a gate the live read has
already answered. flow-status's PR rows are now explicitly live-read with a documented
STATE-disagreement and gh-unavailable degrade. Repaired this repo's own STATE.md (was
asserting PRs #30/#31 open; both confirmed MERGED via `gh pr list`), logged the answered
rule-10 gate in DECISIONS.md, and added a JOURNAL.md line. Smoke green: validate-plugin
OK, 161 unittest OK (2 skipped), check-links 0 failures/212 references.
