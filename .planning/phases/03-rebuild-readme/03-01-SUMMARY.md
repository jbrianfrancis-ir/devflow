---
plan: 03-01
status: complete
agent: executor/claude/sonnet
commits: [5c76d79, 6de3a09]
deviations: []
human_checks: []
deferred: []
---
Built `scripts/check-fenced-paths.py` (D-19 fence guard) by importing `_code_fence_mask` /
`_frontmatter_mask` from `scripts/check-links.py` via importlib — no reimplemented fence rule, so
phase-02's three drifts (no same-char close, no tab indent, toggle inversion) can't recur. Fail-closed:
missing/unreadable checker exits 2, "could not check", never "0 violations". Reports coverage:
`N violations, F files scanned, L fenced lines`.

`tests/test_check_fenced_paths.py`: 9 tests on `scan(root)` tempdir fixtures — backtick/tilde/tab
fences, the toggle-inversion assertion pair (measured phase-02 awk backwards on both halves),
unterminated fence, nonexistent path, frozen-page exclusion, this repo clean, guard-unavailable.
Mutation-checked and reverted (not committed): stubbing the toggle-on-any-char behavior fails the
inversion test; dropping `~~~` recognition fails the tilde test — suite isn't vacuous.

G1–G4 run clean from repo root at every commit: G1 `0 failures, 179 references checked` (unmoved,
plan adds no markdown); G2 silent; G3 `0 violations, 10 files scanned, 12 fenced lines` (probed value
matched exactly); G4 silent. No fence violation found in the tree as-is — nothing to report. `unittest
discover` picked up the new suite (92 → 101 tests). G3 is now the committed script for the rest of the
phase.
