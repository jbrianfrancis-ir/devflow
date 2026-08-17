<!-- .planning/LEARNINGS.md — cap 20 bullets; consolidate oldest when over. -->
# Learnings

- **The checker ignores everything inside fenced code blocks** — a rule beyond REQ-09e's documented R1–R5. It hides nothing today (measured: 0 otherwise-checkable backticked refs sit inside fences), but phases 02–04 move README prose into `docs/` pages and any path reference that lands inside a fence loses coverage **silently**. Watch for this when carving pages; a fenced example is invisible to CI.
- `check-links.py`'s `main()` resolves the root via `git rev-parse --show-toplevel` from the **cwd**, not the script's location. Smoke and CI are correct only because both run from the repo root. `check(root)` takes an explicit root and is the safe seam for anything programmatic.
- R5's blind spot is load-bearing for the clean baseline: a first-segment typo matching no top-level entry of any base (`docz/x.md`) goes unreported. A later phase that **renames a top-level directory** should expect references to it to go quiet rather than red.
- A link checker scoped to markdown link syntax would have been near-useless here: 619 backticked path refs vs 2 `[](…)` links. Check the reference surface a repo actually uses before building a guard for the one it doesn't.
- A skip rule must be evaluated against every resolution base, never the repo root alone. Root-only silently unchecked 10 real refs under `references/` and `templates/` — and reported green. Measured, not guessed: 161 tokens checked per-base vs 151 root-only.
- A test that only asserts the skip half of a rule passes under both the correct and the broken reading. Assertion pairs — one that must be checked, one that must be skipped — are what make a rule testable. Mutation-proved both directions.
