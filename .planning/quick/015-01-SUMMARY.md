<!-- .planning/quick/015-01-SUMMARY.md — cap 1.5KB. Frontmatter first: others read only frontmatter. -->
---
plan: quick-015-01
status: complete
agent: executor/claude/sonnet
commits: [4a5d4cc, c2b9da9, 8481267, 42f5287]
deviations: ["[Rule 1] task 2's original falsify passed vacuously: dropping only the mnemonicPrefix override still exited 2 via task 1's could-not-parse fallback. Strengthened both new prefix-config tests to also assert pattern: present / could not parse absent in stderr; re-falsified, mutation now fails as required."]
human_checks: []
deferred: []
---
Guard: every `git diff` now goes through `run_git_diff()` (GIT_DIFF_FORMAT_ARGS pins
-c mnemonicPrefix/noprefix=false, --no-ext-diff, --src/--dst-prefix); a non-empty
unparseable diff returns COULD_NOT_PARSE -> exit 2, never allow.
Falsify exit codes (mnemonic/noprefix/defaults): original 0/0/2, fixed 2/2/2 (both under
real ambient global config and isolated). Tests: 33->36 (+3), suite OK both before/after;
the 5 previously-deferred SecretScanGuardTests failures are now fixed by task 1.
R8: architecture.md documents optional `— pattern: <regex>` on Forbidden bullets;
conventions.md's secret-scan section enforces it across tracked files incl. .planning/;
flow-hooks/SKILL.md documents the same guard doing it (no 4th guard/token).
validate-plugin.py: 22 skills, exit 0 (falsified via corrupted frontmatter -> exit 1,
restored); check-links.py: 0 failures, 227 refs.
