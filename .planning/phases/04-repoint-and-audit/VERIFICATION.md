<!-- Written retroactively on 2026-08-20 (quick 003). Phase 04 ran as ad-hoc work in a single
     commit (923cae8) with no plans, no plan-check rounds, and no verifier agent — a deliberate
     right-sizing call recorded in that commit's own message. It therefore has no PLAN.md and no
     NN-MM-SUMMARY.md, and this file doubles as the phase record: what ran, and whether REQ-06
     and REQ-08 actually hold. Their accept criteria are commands, and the commands are re-run
     here at c663ca1+ rather than taken from the commit's claims. -->
---
phase: 04-repoint-and-audit
status: pass
smoke: pass
gaps: []
unverified:
  - "REQ-06's 'every load-bearing sentence preserved' rests on a section-by-section human read of the pre-project README against README + the twelve docs/ pages, done once at 923cae8. It is judgement, not a command, so nothing re-runs it — including this pass. The mechanical half (no orphaned pages, all references resolve) is verified below; the editorial half is not re-provable after the fact."
---

## What ran
No plans. One commit — `923cae8 docs: repoint stale references and close phase 04 as ad-hoc work` — covering both requirements. The commit message states the right-sizing decision plainly: three edits in two files, and the ceremony would have cost more than the task. Recorded here because a phase directory that exists only to say "this ran ad-hoc" is still worth more than an absent one, which reads as work that was skipped.

## Smoke
`python3 scripts/validate-plugin.py && python3 -m unittest discover -s tests && python3 scripts/check-links.py` → **exit 0**; `0 failures, 197 references checked`.

## Truths
| requirement | result | evidence |
|---|---|---|
| REQ-08 — every inbound reference to relocated content repointed, links **and prose**; accept: `git grep -in readme` outside `.planning/` and `tests/` names no section that moved | VERIFIED | Re-ran the grep filtered for moved-section names (`Autonomous operation`, `Session hygiene`, `## Flow`, `README's <Section>`): the only hit is `docs/README.md:7`, prose reading "after the README's install commands" — `## Install` still exists, so it names a live section, not a moved one. |
| REQ-08 — the two named files specifically | VERIFIED | `plugins/devflow/skills/flow-status/SKILL.md` now points at `docs/autonomy.md` → Session hygiene (the page that owns it), not the README. `.github/ISSUE_TEMPLATE/config.yml` no longer promises autonomy recipes the README dropped. Both changed in 923cae8. |
| REQ-08 — remaining `readme` hits are out of scope, not overlooked | VERIFIED | All other hits are under `.planning/`, which the accept criterion excludes: planning artifacts quoting the old structure as historical record. |
| REQ-06 — no substantive claim lost, mechanically | VERIFIED | All twelve `docs/` pages are reachable from `docs/README.md` (verified in phase 03's record — 11 entries, one per page, none self-linking); link checker `0 failures` over 197 references, so nothing points into a page that was dropped. |
| REQ-06 — no substantive claim lost, editorially | HUMAN (non-inferable) | Done once at 923cae8 as a section-by-section read; the apparent gaps were deliberate, already-recorded edits (corrected subagent/size numerals, de-enumerated role list). Not re-provable by command — see `unverified`. |

## Human checks
- [ ] Optional, low priority — spot-check the pre-project README (`git show 5ffe726:README.md`) against README + `docs/` if you ever want the editorial half of REQ-06 independently confirmed. Nothing depends on it; the milestone is closed either way.

## Learnings
- A phase run ad-hoc still needs a directory. ROADMAP marked 04 `verified` for two days with nothing on disk behind it, and the gap was invisible until someone went looking — exactly the drift `/flow-audit` exists to catch.
