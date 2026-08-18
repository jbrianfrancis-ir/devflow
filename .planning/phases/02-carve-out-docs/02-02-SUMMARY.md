<!-- .planning/phases/02-carve-out-docs/02-02-SUMMARY.md — cap 1.5KB. Frontmatter first: others read only frontmatter. -->
---
plan: 02-02
status: complete            # complete | partial | blocked
agent: executor/claude/sonnet    # role/provider/model that executed this plan — matches the commit trailers
commits: [f26061b, 5509881]      # short SHAs, one per task
deviations: []
human_checks: []
deferred: []
---
Carved `docs/execution-model.md` (graph execution, smoke gate, state/JOURNAL.md, map staleness,
conventions, architecture constraints, design constraints — seven README paragraphs, one D-16 fold-in
from "Many streams at once") and `docs/provenance.md` (attribution, decision log, export, split into
sections) out of README's Flow section, one task per commit, each a complete D-14 move (verified
per-commit and across the full plan, all shas clean). Reference pointers to `plan-format.md`,
`verification.md`, `conventions.md`, and `autonomy.md` use clickable markdown links, not backticks,
matching the house-style fix from 572767c. All four gates (G1–G4) green after every commit;
`docs/execution-model.md` is 20 lines (well under the 250-line cap) because README's paragraphs were
already dense summaries — nothing further to compress. README's Flow section is down to its heading,
the diagram, and the `/flow-oracle` paragraph, matching MAPPING.md's plan for this wave.
