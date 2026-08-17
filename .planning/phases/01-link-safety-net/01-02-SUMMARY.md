---
plan: 01-02
status: complete
agent: executor/claude/sonnet
commits: [de9e446, 9206aed]
deviations: []
human_checks: []
deferred: []
---
Built `tests/test_check_links.py` (13 tests, stdlib `unittest`), loading
`scripts/check-links.py` via `importlib.util.spec_from_file_location` and driving
01-01's `check(root)` seam against tempdir git fixtures — never the CLI, never
this repo. Covers: the anti-tautology clean-fixture case; one failing case per
reference kind (link, anchor, backticked path, `{devflow_root}` path) each
asserting file/line/target; the anchor positive; both scope exclusions
(templates/, `.planning/`); and all five skip rules R1-R5.

R5 got two assertions in one fixture per the plan's explicit warning: a token
whose first segment matches the referring file's own directory (not the fixture
root) is checked and fails, while a token matching no base at all is skipped —
proving the per-base rule against the wrong root-only reading, not just its
skip half. Each skip-rule fixture also plants a real top-level entry matching
the token's first segment so it pins its named rule specifically, not an
incidental R5 skip.

One implementation detail worth flagging for future readers: `{devflow_root}/...`
targets are substituted to `plugins/devflow/...` *before* being reported, so a
failure's `target` field shows the resolved path, not the original placeholder
token — confirmed by running the suite, not assumed.

`python3 -m unittest tests.test_check_links -v`: OK, 13/13. Full discovery (49
tests, 2 skipped via `DEVFLOW_SMOKE` gate) and `python3 -S -E -m unittest
discover -s tests -v` both OK. `git status --porcelain -- scripts tests docs
plugins README.md` empty after the suite runs.
