<!-- .planning/phases/02-carve-out-docs/02-03-SUMMARY.md — cap 1.5KB. Frontmatter first: others read only frontmatter. -->
---
plan: 02-03
status: complete            # complete | partial | blocked
agent: executor/claude/sonnet    # role/provider/model that executed this plan — matches the commit trailers
commits: [335543c, a5aaa14]      # short SHAs, one per task
deviations: []
human_checks: []
deferred: []
---
Carved `docs/requirements-clarity.md` (confident sentences, markers → backstop_truths → abstention,
Assumptions/SC-NN, `/flow-audit`) out of README's "Saying unknown out loud" section, and opened
`docs/review.md` with three sections — review before the code exists (`/flow-plan --panel`), review
that isn't self-review (`/flow-pr` lenses), second opinions (`/flow-oracle`, D-16 fold-in) — one task
per commit, each a complete D-14 move (verified per-commit and across the full plan, both shas clean).
Pages link `plan-format.md` and `verification.md` (requirements-clarity) and `plan-format.md` and
`oracle.md` (review) as source of truth instead of restating field rules, abstention procedure, or
consult-bundle mechanics. All four gates (G1–G4) green after every commit. `docs/review.md` carries a
single `# Review` H1 and leaves its three sections in place for 02-04 to append adversarial review,
adjudication, and PR-to-green after them; README's "Flow" and "Many streams at once" headings are
untouched, matching MAPPING.md's plan for this wave.
