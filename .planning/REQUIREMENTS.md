<!-- .planning/REQUIREMENTS.md — cap 3KB. One line per requirement. -->
# Requirements

## Must have (v1)
- REQ-01: `README.md` contains only Install, Quick start, Commands, Configuration, Documentation index, and License/Acknowledgements pointers — accept: those headings present, no other `##` section, every removed topic reachable from the index.
- REQ-02: The full 20-row `/flow-*` command table stays in `README.md`, unchanged in content — accept: 20 command rows, same Loop/Command/Does columns as today.
- REQ-03: `README.md` opens with a 2–3 sentence positioning statement and the install blocks for both Claude Code and Codex — accept: a reader can install without scrolling past the first screen.
- REQ-04: `docs/README.md` exists as an index linking every file in `docs/`, each with a one-line description of what it answers — accept: link count equals `docs/*.md` count minus itself; every link resolves.
- REQ-05: Deep-dive content removed from README lands in topic files under `docs/` — execution model, requirements clarity, review, parallel work, autonomy, providers, provenance, installation detail — accept: each topic has exactly one home; no topic split across two files.
- REQ-06: No substantive claim in today's `README.md` is lost — accept: a section-by-section diff of the current README against the new README + new docs pages shows every load-bearing sentence preserved or deliberately deleted with a reason recorded.
- REQ-07: Acknowledgements move to `docs/acknowledgements.md` verbatim; `README.md` keeps a one-line pointer to it and to `NOTICE` — accept: `NOTICE` byte-identical to today.
- REQ-08: Every inbound reference to relocated content is repointed — markdown links **and** prose mentions — covering at minimum `plugins/devflow/skills/flow-status/SKILL.md` (lines naming "README's Autonomous operation" and "README → Session hygiene") and `.github/ISSUE_TEMPLATE/config.yml` (`about:` text promising a command reference and autonomy recipes) — accept: `git grep -in readme` outside `.planning/` and `tests/` returns no reference to a section that no longer exists there.
- REQ-09: `scripts/check-links.py` validates internal markdown links and `#anchor` fragments across tracked `.md` files using only the Python standard library, exiting non-zero on any unresolvable target — accept: run against a deliberately broken link, it exits non-zero and names the file, line, and target.
- REQ-10: `.github/workflows/lint.yml` runs the link check on push to `main` and on pull requests — accept: a PR containing a broken internal link fails the `lint` job.
- REQ-11: `.planning/ARCHITECTURE.md` `## Smoke` is extended to include the link check, in the same change that adds `scripts/check-links.py` — accept: smoke command runs all three steps and exits 0.

<!-- Open question — do not resolve by guessing. -->
- REQ-12: Each `docs/` topic page relates to the authoritative contract in `plugins/devflow/references/*.md` by [NEEDS CLARIFICATION: (a) summarizing for readers and linking to the reference as the source of truth — honors "docs are pointers, never copies" but means two files per topic; (b) owning the reader-facing explanation fully, with references/ kept strictly as agent prompt contracts and never linked from docs/ — one place to read but the same fact stated twice in the repo; (c) docs/ page IS the reference, with references/*.md reduced to a pointer — one home per fact, but changes agent-facing prompt files, which this project put out of scope] — accept: whichever is chosen, no fact about DevFlow behavior appears in full in two files.

## Success criteria
- SC-01: `README.md` is at most 110 lines and at most 14KB.
- SC-02: Zero unresolvable internal links or anchors across all tracked markdown, proven by `scripts/check-links.py` exiting 0.
- SC-03: No file in `docs/` exceeds 250 lines — the failure mode being fixed is one document carrying too many topics, and it is reintroduced by moving the pile rather than splitting it.
- SC-04: A reader who has never seen DevFlow can go from the top of `README.md` to a running `/flow-new` without opening any file in `docs/`.
- SC-05: The repo still has zero third-party dependencies — no `pip install`, no npm, no new CI action beyond `actions/checkout@v4`.

## Assumptions
- `docs/blitzos.md` and `docs/status-contract.md` stay at their current paths with their current contents; the new index links them alongside the new pages.
- The existing prose register — dense, terse, load-bearing, no filler — is preserved when text moves; this is a restructure, not a rewrite, so moved sentences move intact.
- Relative links only between repo files; no absolute `https://github.com/jbrianfrancis-ir/devflow/...` URLs to this repo's own content.
- No badges are added to the README unless the user asks; there are none today and inventing CI/version badges is a separate decision.
- The ASCII flow diagram (`/flow-new ──► /flow-plan 1 ──► …`) stays in the README under Quick start — it is orientation, not depth.
- Anchor checking assumes GitHub's heading-to-anchor slug rules (lowercase, spaces to hyphens, punctuation stripped).
- `tests/test_flow_agent.py`'s mentions of `README.md` are test fixture strings, not documentation references, and are left alone.

## Out of scope
See `PROJECT.md` → Out of scope. In short: behavior changes, a docs site generator,
restructuring `references/`, moving the two existing docs, editing `NOTICE`/`LICENSE`/manifests,
external-URL checking, and translations.
