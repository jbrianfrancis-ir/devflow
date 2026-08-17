# Phase 01 plan check — round 3 (final)

## Verdict
PASS

## Round 2 issues

1. **RESOLVED** — R5 is now stated per-base. 01-01 Task 1 reads: "the token's first segment is neither `.`/`..` nor a top-level entry of **any of the token's resolution bases** — the same bases resolution uses below: `root`, the referring file's own directory, and `<root>/plugins/devflow/` when the file lives under it. Entries come from `git -C <root> ls-files`, never a literal list. Apply R5 per base, not against `root` alone", with both worked examples spelled out (`templates/journal.md` from a file under `plugins/devflow/` survives; `codebase/MAP.md` and `deploy/PIPELINE.md` are skipped). The stated cost is now accurate and narrow: "a first-segment typo goes unseen only when the mistyped segment matches no top-level entry of any of that token's bases (`docz/x.md`)… a first segment that names a real directory but a missing file under it — including a broken `templates/nope.md` written from inside `plugins/devflow/`" is still reported. The 01-02 test gap is closed too: `truths[5]` and Task 2 now require **two** R5 assertions and say so explicitly — "A suite carrying only the skip half would pass under the wrong root-only reading and does not satisfy this", and Task 2 ends "Assertion (a) is what distinguishes the correct rule from the root-only one; do not drop it for a skip-only case." Verified empirically below.

2. **RESOLVED** — 01-01 `must_haves.truths[3]` now reads: "`[x](#install)` appended to README.md — a heading that exists — exits 0; `git checkout README.md` restores the file." The restore is graded by the truth itself, matching `truths[2]`, `truths[4]` and 01-03 `truths[2]`. `## Install` exists at README.md:9, so the positive probe is grounded.

## Empirical R5 verification

I implemented the plan's rule set (kinds REQ-09a/b/c, the `{devflow_root}` rewrite, R1–R5, multi-base resolution) as a throwaway script and ran it over the scoped tree (`git ls-files '*.md'` minus `plugins/devflow/templates/**` and `.planning/**`), with a `--mode root-only` switch reproducing round 1's wrong reading. Scope measured: **93 tracked files, 50 scoped `.md`**.

| | per-base R5 (revised) | root-only R5 (round 1) |
|---|---|---|
| tokens resolved & checked | **161** | 151 |
| tokens skipped by R5 | **13** | 23 |
| failures reported | **1** | 1 |

- **Exactly one failure**, and it is the expected one: `plugins/devflow/references/autonomy.md:5: ../docs/status-contract.md`. Nothing else fires. Baseline claim in 01-01 Task 2 holds.
- **The 10 recovered refs are exactly the D-08 class** the round-2 issue named. Per-base checks, root-only skips: `references/conventions.md`, `references/oracle.md` (flow-consultant.md:8), `references/autonomy.md` (checkpoints.md:24), `templates/state.md` (autonomy.md:23), `templates/decisions.md` (autonomy.md:32, conventions.md:84, migrate-gsd.md:34), `templates/journal.md` (conventions.md:81), `templates/agent-pointer.md` (conventions.md:89), `templates/plan.md` (plan-format.md:3). Spot-probed: `templates/journal.md` from `references/autonomy.md` → `ok` (resolves to `plugins/devflow/templates/journal.md`); `references/autonomy.md` from `references/checkpoints.md` → `ok`.
- **All 13 remaining R5 skips are genuine consuming-project tokens** — `codebase/MAP.md` ×4, `codebase/DOCS.md` ×2, `deploy/PIPELINE.md` ×2, `deploy/UAT-PLAN.md`, `deploy/SIGNOFF.md`, `sessions/INDEX.md` ×2. No in-repo ref is among them.
- **Planted broken `templates/nope.md` written from `plugins/devflow/references/autonomy.md` → `('fail', 'templates/nope.md')`** under the revised rule; `('skip','R5')` under root-only. Also confirmed reportable: `references/nope.md` from inside `plugins/devflow/` → fail; `docs/nope.md` from README → fail. Confirmed still skipped: `docz/nope.md` from README → R5 (the stated, narrow cost).
- 01-01 `truths[2]`/`[3]` probes re-measured non-destructively: `[x](docs/nope.md)` → fail, backticked `scripts/nope.py` → fail, backticked `{devflow_root}/references/nope.md` → fail (rewritten to `plugins/devflow/references/nope.md`), `#no-such-heading`/`#install` reach the anchor path with `## Install` present. `plugins/devflow/templates/plan.md` and `.planning/PROJECT.md` are both outside the enumerated set, so `truths[4]`'s two plants are correctly inert.

**01-02's R5 test distinguishes the two readings.** I built the exact fixture Task 2 specifies — `sub/a.md` containing `` `helpers/missing.py` `` and `` `codebase/MAP.md` ``, with `sub/helpers/present.py` tracked and `sub/helpers/missing.py` absent, `git init` + `git add -A`, `GIT_CONFIG_{GLOBAL,SYSTEM}=/dev/null` — and ran both readings:
- per-base: **1 failure**, `sub/a.md:3: helpers/missing.py`; `codebase/MAP.md` skipped by R5. Both halves of `truths[5]` hold.
- root-only: **0 failures**; both tokens skipped by R5.

So assertion (a) errors out under the round-1 rule while assertion (b) passes under both. The suite genuinely catches the wrong reading.

## Notes
- Coverage clean both ways: roadmap row 01 = REQ-09/10/11, SC-02, SC-05; 01-01 REQ-09+09a–e/SC-02/SC-05, 01-02 REQ-09+09a–e/SC-05, 01-03 REQ-10/11/SC-02/SC-05. Every plan entry exists in REQUIREMENTS.md; no phase 02–04 requirement leaks in. REQ-12's open marker is not on this phase, so its absence from `backstop_truths` stays correct.
- Graph legal and unchanged: 1→2→3, waves 1/2/3 correct by the max+1 rule, no cycles, no same-wave pairs, `files_modified` disjoint. Both of 01-03's edges are real — it runs 01-01's script and 01-02's suite through the smoke command.
- Truths are command-anchored and every mutating probe now names both its introduction and its cleanup (01-01 `truths[2]`,`[3]`,`[4]`; 01-03 `truths[2]`); `.planning/STATE.md`/`JOURNAL.md` remain explicitly barred. 01-02 `truths[8]` keeps the scoped `git status --porcelain` with its rationale.
- Backstop truth survives verbatim and is still legitimate: I re-measured `](#` across the scoped tree — **0 occurrences** — so nothing existing grades duplicate-heading `-1`, inline-code headings, or setext, and REQUIREMENTS.md's one-line slug rule does not settle them.
- Size (8399 / 7354 / 5097): accepted per the orchestrator's ruling and I see no threat to single-context execution — each plan is 2 tasks, no discovery or checkpoint mixing, and the bulk is the R5 specification that this round proves is load-bearing.
