---
plan: 01-01
status: complete
agent: executor/claude/sonnet
commits: [0208304, 84e6eb7]
deviations: []
human_checks: []
deferred: []
---
Built `scripts/check-links.py` (stdlib-only): validates `[text](target)` links + `#anchor`
fragments (GitHub slug rules incl. duplicate `-1` suffix and setext headings), backticked
repo-relative paths, and `{devflow_root}/...` refs. Skip rules R1-R5 applied per resolution
base (root, referring file's own dir, `plugins/devflow/` when applicable) per R5's stated
requirement — never against root alone.

Ran against the untouched repo: exactly the one predicted failure surfaced —
`plugins/devflow/references/autonomy.md:5` → `../docs/status-contract.md`, resolving to a
nonexistent `plugins/devflow/docs/status-contract.md`. Classified as pre-existing rot (not a
checker bug) and fixed to the root-relative `docs/status-contract.md`, matching how sibling
`references/conventions.md` writes the same class of reference. No other residue appeared —
no rule needed tightening, no allowlist added.

`python3 scripts/check-links.py` exits 0 on the clean tree and under `-S -E`. All must_haves
probes verified: the four broken kinds (bad link, bad backtick, bad `{devflow_root}` ref, bad
anchor) each fail naming file/line/target; `#install` passes; backticked `scripts/nope.py`
planted in `plugins/devflow/templates/plan.md` and `.planning/PROJECT.md` leaves exit 0 (both
trees out of scope). Existing smoke (`validate-plugin.py` + `unittest discover`) still passes.
