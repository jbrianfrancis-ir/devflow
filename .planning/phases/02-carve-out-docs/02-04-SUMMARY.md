<!-- .planning/phases/02-carve-out-docs/02-04-SUMMARY.md — cap 1.5KB. Frontmatter first: others read only frontmatter. -->
---
plan: 02-04
status: complete            # complete | partial | blocked
agent: executor/claude/sonnet    # role/provider/model that executed this plan — matches the commit trailers
commits: [a875b98, 04742de]      # short SHAs, one per task
deviations: []
human_checks: []
deferred: []
---
Finished `docs/review.md` with the four remaining review surfaces — adversarial review, adjudication
in a third context, the three ledger rules, PR to green — appended after plan 02-03's three sections,
one `# Review` H1 kept. Then carved `docs/parallel-work.md` (lead sentence, fleet board, workstreams)
and retired README's entire "Many streams at once" section, including its heading; the false "Four
pieces address that:" connector was dropped and the reason recorded in the commit message per
MAPPING.md's deliberate-deletion note. Both pages link `adjudication.md` and `conventions.md` instead
of restating vocabularies/tables (REQ-12/12a); `parallel-work.md` also links sibling
`status-contract.md` for the `FLOW:` parsing contract. D-14 verified clean at both commits; G1–G4 green
after each (174 references checked, up from 162 at phase start). `git ls-files` confirms
`docs/parallel-work.md` tracked.
