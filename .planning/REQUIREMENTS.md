<!-- .planning/REQUIREMENTS.md — cap 3KB. One line per requirement. -->
# Requirements

## Must have (v1)
- REQ-01: `README.md` has only Install, Quick start, Commands, Configuration, Documentation, License/Acknowledgements — accept: no other `##`; every removed topic reachable from the index.
- REQ-02: The 20-row `/flow-*` command table stays in README, content unchanged — accept: 20 rows, same columns.
- REQ-03: README opens with 2–3 sentence positioning + both install blocks — accept: installable without scrolling past the first screen.
- REQ-04: `docs/README.md` indexes every `docs/*.md` with a one-line "what it answers" — accept: link count = `docs/*.md` − 1; all resolve.
- REQ-05: Deep-dive topics land in `docs/` topic files (execution model, requirements clarity, review, parallel work, autonomy, providers, provenance, installation detail) — accept: one home per topic; no topic split across files.
- REQ-06: No substantive claim in today's README is lost — accept: section-by-section diff of old README vs new README + new pages; every load-bearing sentence preserved, or deleted with a recorded reason.
- REQ-07: Acknowledgements move verbatim to `docs/acknowledgements.md`; README keeps a one-line pointer to it and `NOTICE` — accept: `NOTICE` byte-identical.
- REQ-08: Every inbound reference to relocated content repointed — links **and prose** — at minimum `plugins/devflow/skills/flow-status/SKILL.md` (names "README's Autonomous operation", "README → Session hygiene") and `.github/ISSUE_TEMPLATE/config.yml` (`about:` promises a command reference + autonomy recipes) — accept: `git grep -in readme` outside `.planning/` and `tests/` names no section that moved.
- REQ-09: `scripts/check-links.py` validates internal references across tracked `.md`, stdlib only, exit non-zero naming file/line/target — accept: a deliberately broken reference of each kind below fails it.
  - REQ-09a: `[text](target)` relative paths and `#anchor` fragments, resolved against the filesystem and target headings (GitHub slug rules).
  - REQ-09b: **Backticked repo-relative paths** — a backticked token with `/` and a `.md`/`.py`/`.json`/`.yml` extension. Load-bearing: 619 backticked refs vs 2 markdown links, so a syntax-only checker protects nothing.
  - REQ-09c: `{devflow_root}/…` resolves to `plugins/devflow/…` and is validated (~80 otherwise-unprotected refs).
  - REQ-09d: Scope = all tracked `.md` except `plugins/devflow/templates/**` and `.planning/**` (both describe a consuming project, not this repo).
  - REQ-09e: Non-repo-relative refs — bare filenames, consuming-project artifacts, external URLs — skipped **by rule, not allowlist**; no committed exception file that can drift.
- REQ-10: `.github/workflows/lint.yml` runs the link check on push to `main` and on PRs — accept: a PR with a broken internal reference fails `lint`.
- REQ-11: `ARCHITECTURE.md` `## Smoke` gains the link check **no earlier than** the commit that makes `scripts/check-links.py` runnable — accept: smoke runs all three steps and exits 0, and exits 0 at every intermediate commit of the phase (the point is that no commit ever names a script that does not yet exist; a later commit in the same phase is fine).
- REQ-12: Each `docs/` topic page relates to `plugins/devflow/references/*.md` by [NEEDS CLARIFICATION: (a) docs summarizes + links to the reference as source of truth — no duplication, two files per topic; (b) docs owns the reader-facing explanation, references stays agent-only prompt contract — one place to read, same fact twice in repo; (c) the docs page *is* the reference, references shrinks to a pointer — one home per fact, but edits agent-facing files this project put out of scope] — accept: whichever is chosen, no DevFlow behavior fact appears in full in two files.

## Success criteria
- SC-01: `README.md` ≤ 110 lines and ≤ 14KB.
- SC-02: Zero unresolvable internal references across scoped markdown — `scripts/check-links.py` exits 0.
- SC-03: No `docs/` file exceeds 250 lines — moving the pile instead of splitting it reintroduces the exact failure being fixed.
- SC-04: A first-time reader goes from the top of README to a running `/flow-new` without opening `docs/`.
- SC-05: Repo still has zero third-party dependencies — no `pip install`, no npm, no CI action beyond `actions/checkout@v4`.

## Assumptions
- `docs/blitzos.md` and `docs/status-contract.md` stay at their paths with their contents; the index links them alongside new pages.
- Register is preserved — dense, terse, load-bearing. This is a restructure, not a rewrite: moved sentences move intact.
- Relative links only; no absolute URLs to this repo's own content.
- No badges added — there are none today, and inventing them is a separate decision.
- The ASCII flow diagram stays in README under Quick start; it is orientation, not depth.
- Anchor checking uses GitHub slug rules (lowercase, spaces→hyphens, punctuation stripped).
- `tests/test_flow_agent.py`'s `README.md` mentions are fixture strings, not doc references — left alone.

## Out of scope
See `PROJECT.md` → Out of scope: behavior changes, a docs site generator, restructuring `references/`,
moving the two existing docs, editing `NOTICE`/`LICENSE`/manifests, external-URL checking, translations.
