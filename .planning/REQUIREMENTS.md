<!-- .planning/REQUIREMENTS.md — cap 3KB; this file is ~5KB, over deliberately (D-11).
     Compressed twice already; the remainder is normative. REQ-09e's per-base skip rule in
     particular cost three plan-check rounds to get right, and shortening it back to a slogan
     re-opens the defect. Rationale lives in PROJECT.md's D-NN table, not here. -->
# Requirements

## Must have (v1)
- REQ-01: `README.md` has only Install, Quick start, Commands, Configuration, Documentation, License/Acknowledgements — accept: no other `##`; every removed topic reachable from the index.
- REQ-02: The 20-row `/flow-*` command table stays in README, content unchanged — accept: 20 rows, same columns.
- REQ-03: README opens with 2–3 sentence positioning + both install blocks — accept: installable without scrolling past the first screen.
- REQ-04: `docs/README.md` indexes every `docs/*.md` with a one-line "what it answers" — accept: link count = `docs/*.md` − 1; all resolve.
- REQ-05: Deep-dive topics land in `docs/` topic files (execution model, requirements clarity, review, parallel work, autonomy, providers, provenance, installation) — accept: one home per topic; none split across files.
- REQ-06: No substantive claim in today's README is lost — accept: section-by-section diff of old README vs new README + new pages; every load-bearing sentence preserved, or deleted with a recorded reason.
- REQ-07: Acknowledgements move verbatim to `docs/acknowledgements.md`; README keeps a one-line pointer to it and `NOTICE` — accept: `NOTICE` byte-identical.
- REQ-08: Every inbound reference to relocated content repointed — links **and prose** — at minimum `plugins/devflow/skills/flow-status/SKILL.md` (names "README's Autonomous operation", "README → Session hygiene") and `.github/ISSUE_TEMPLATE/config.yml` (`about:` promises a command reference + autonomy recipes) — accept: `git grep -in readme` outside `.planning/` and `tests/` names no section that moved.
- REQ-09: `scripts/check-links.py` validates internal references across tracked `.md`, stdlib only, exit non-zero naming file/line/target — accept: a deliberately broken reference of each kind below fails it.
  - REQ-09a: `[text](target)` relative paths and `#anchor` fragments, resolved against the filesystem and target headings (GitHub slug rules).
  - REQ-09b: **Backticked repo-relative paths** — a backticked token with `/` and a `.md`/`.py`/`.json`/`.yml` extension.
  - REQ-09c: `{devflow_root}/…` resolves to `plugins/devflow/…` and is validated.
  - REQ-09d: Scope = all tracked `.md` except `plugins/devflow/templates/**` and `.planning/**`.
  - REQ-09e: Non-repo-relative refs skipped **by rule, not allowlist** — no committed exception file. A skip rule is evaluated against **every** resolution base of the token (repo root, the referring file's directory, and `plugins/devflow/` for files under it), never the root alone.
- REQ-10: `.github/workflows/lint.yml` runs the link check on push to `main` and on PRs — accept: a PR with a broken internal reference fails `lint`.
- REQ-11: `ARCHITECTURE.md` `## Smoke` gains the link check **no earlier than** the commit making `scripts/check-links.py` runnable — accept: smoke runs all three steps and exits 0 at every intermediate commit of the phase.
- REQ-12: Where a topic has an authoritative contract in `plugins/devflow/references/*.md`, the `docs/` page **summarizes it and links to it as source of truth** (D-10) — accept: no behavior fact stated in full in both; every such page links to its reference.
  - REQ-12a: "Summarizes" = what it is, why it exists, enough shape to decide whether to read further. Normative detail (exact rules, formats, thresholds, field lists) stays in `references/` and is linked, never restated. A `docs/` page that contradicts its reference is a defect.
  - REQ-12b: Topics with no reference counterpart (installation, fleet board, session hygiene, acknowledgements) are owned outright by their `docs/` page. **Correction (D-17):** providers/model tiers was listed here in error — `plugins/devflow/references/hosts.md` carries `## Provider selection and dispatch` and `## Model tiers`, so REQ-12's summarize-and-link condition governs it, consistent with D-10.
  - REQ-12c: `references/*.md` is not edited by this project, except phase 01's broken-path fix — a path change, not content.

## Success criteria
- SC-01: `README.md` ≤ 110 lines and ≤ 14KB.
- SC-02: Zero unresolvable internal references across scoped markdown — `scripts/check-links.py` exits 0.
- SC-03: No `docs/` file exceeds 250 lines.
- SC-04: A first-time reader goes from the top of README to a running `/flow-new` without opening `docs/`.
- SC-05: Zero third-party dependencies — no `pip install`, no npm, no CI action beyond `actions/checkout@v4`.

## Assumptions
- `docs/blitzos.md` and `docs/status-contract.md` keep their paths and contents; the index links them alongside new pages.
- Register preserved — dense, terse, load-bearing. A restructure, not a rewrite: moved sentences move intact.
- Relative links only; no absolute URLs to this repo's own content.
- No badges added.
- The ASCII flow diagram stays in README under Quick start.
- Anchor checking uses GitHub slug rules (lowercase, spaces→hyphens, punctuation stripped).
- `tests/test_flow_agent.py`'s `README.md` mentions are fixture strings — left alone.

## Out of scope
See `PROJECT.md` → Out of scope.
