---
plan: 01-03
status: complete
agent: executor/claude/sonnet
commits: [4f1a251, 915460b]
deviations: []
human_checks: ["On the PR for this phase, confirm lint ran the link-check step and passed, then that a commit carrying a deliberately broken internal reference turns lint red before it is reverted (REQ-10's acceptance is only observable on a real PR)."]
deferred: []
---
Extended `.planning/ARCHITECTURE.md` `## Smoke` Command to `… && python3 scripts/check-links.py`
(pre-flight confirmed the script exists and exits 0 first, per REQ-11) and deleted the now-spent
reservation comment; `## Link checking` untouched (`git diff` confirmed no hunk there).

Added a `Check internal links` step running `python3 scripts/check-links.py` to the `validate` job
in `.github/workflows/lint.yml`, after the existing two steps. No new `uses:`, no pip/install/
setup-python (`grep -c 'uses:'` = 1; SC-05); triggers unchanged (push to `main` + `pull_request`,
REQ-10).

Verified: smoke command run verbatim exits 0 (49 tests OK, 2 skipped via DEVFLOW_SMOKE, checker
"0 failures"). All three lint.yml step commands exit 0 locally in order. Appended a backticked
`scripts/nope.py` to README.md → checker exits 1 naming the line; `git checkout README.md`
restored exit 0. Repo clean except the two untracked phase SUMMARYs left for orchestrator
bookkeeping.
