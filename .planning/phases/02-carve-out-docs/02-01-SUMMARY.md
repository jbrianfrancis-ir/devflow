<!-- .planning/phases/02-carve-out-docs/02-01-SUMMARY.md — cap 1.5KB. Frontmatter first: others read only frontmatter. -->
---
plan: 02-01
status: complete            # complete | partial | blocked
agent: executor/claude/sonnet    # role/provider/model that executed this plan — matches the commit trailers
commits: [767ca10, 4ae7d41]      # short SHAs, one per task
deviations: []
human_checks: []
deferred: []
---
Carved `docs/installation.md` (Codex-cloud, self-bootstrap, BlitzOS context-repo paragraphs) and
`docs/providers.md` (Provider selection, Model tiers) out of README's Install section, one task per
commit, each a complete D-14 move (verified per-commit, both shas clean). BlitzOS link rewritten to
sibling form; providers.md links `hosts.md` per D-17 instead of restating its role table or dispatch
mechanics. All four gates (G1–G4) green after every commit; README's Install section is down to its
heading, two sub-headings, and two fenced install blocks, matching MAPPING.md's `done` state exactly.
