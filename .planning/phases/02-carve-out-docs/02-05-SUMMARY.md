<!-- .planning/phases/02-carve-out-docs/02-05-SUMMARY.md — cap 1.5KB. Frontmatter first: others read only frontmatter. -->
---
plan: 02-05
status: complete            # complete | partial | blocked
agent: executor/claude/sonnet    # role/provider/model that executed this plan — matches the commit trailers
commits: [daed293, 1da9692]      # short SHAs, one per task
deviations: []
human_checks: []
deferred: []
---
Carved `docs/autonomy.md` (status line, five recipes, loop rails, structured gate, human-gate list,
session hygiene) from README's Autonomous operation + Session hygiene sections, linking
`references/autonomy.md` and `references/checkpoints.md` as source of truth rather than restating the
grammar/rail semantics/gate list (REQ-12). Then moved all 8 Acknowledgements paragraphs **verbatim**
(byte-identical lines, checked against `e23403c:README.md` lines 151–165) to `docs/acknowledgements.md`,
owned outright with no reference links (REQ-12b); README's `## Acknowledgements` heading now carries one
pointer line naming both the page and `NOTICE`, still ending in the MIT line. `NOTICE` untouched. D-14
verified clean at both commits (the full anchor-pair loop over both plan shas printed nothing); G1–G4
green after each (179 references checked, up from 174 at phase start). Phase closes: README's only `##`
headings are Install, Commands, Flow, Acknowledgements (4); `docs/*.md` lists 11 files; out-of-scope
`plugins/devflow/references/`, `docs/blitzos.md`, `docs/status-contract.md` unchanged from base.
