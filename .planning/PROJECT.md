<!-- .planning/PROJECT.md — cap 2KB; this file is ~2.7KB, over deliberately (D-11).
     Overwrite sections, don't append. -->
# DevFlow Documentation Restructure

## What
`README.md` has grown to 167 lines / 31.6KB across nine topics. Split it into focused pages
under `docs/`, leave a README that gets someone installed and oriented, and add a stdlib-only
CI check so the resulting link web cannot silently rot.
Primary reader: a developer evaluating DevFlow from its GitHub page.

## Core value
A newcomer reaches a working first phase from the README alone; anyone wanting depth finds
exactly one authoritative page per topic.

## Out of scope
- Behavior changes to skills, agents, or references — documentation only.
- A docs build system or hosted site; `docs/` stays plain markdown read on GitHub.
- Restructuring `plugins/devflow/references/*.md` — agent prompt contracts, not reader docs.
- Moving or editing `docs/blitzos.md`, `docs/status-contract.md` — existing external contracts.
- Editing `NOTICE`, `LICENSE`, or any manifest version field.
- External-URL link checking; translations.

## Key decisions
| ID | Decision | Why | Date |
|----|----------|-----|------|
| D-01 | README = install, quickstart, command table, config, index, pointers; ≤110 lines | The table is the at-a-glance surface that makes DevFlow legible | 2026-08-17 |
| D-02 | `docs/` = flat topic files + `docs/README.md` index | Matches existing docs; links stay one level deep; nothing relocates | 2026-08-17 |
| D-03 | Acknowledgements → `docs/acknowledgements.md`; `NOTICE` untouched | NOTICE is the legal artifact; narrative credit muddies it | 2026-08-17 |
| D-04 | Link check is `scripts/check-links.py`, stdlib only | Zero third-party deps; lychee/npm would break that | 2026-08-17 |
| D-05 | Inbound refs updated repo-wide including prose | `flow-status/SKILL.md` names README sections in prose; no checker catches those | 2026-08-17 |
| D-06 | No deployable surface: harden/uat/release N/A | Ships as a marketplace plugin, not a deployment | 2026-08-17 |
| D-07 | Checker validates backticked repo-relative paths, not just `[](…)` | 619 backticked refs vs 2 markdown links — syntax-only protects nothing | 2026-08-17 |
| D-08 | `{devflow_root}/…` resolves to `plugins/devflow/…` and is validated | ~80 real refs no other check covers | 2026-08-17 |
| D-09 | Skip rules evaluated per resolution base, never root alone; no allowlist file | Root-only skipping silently unchecked 10 real refs (measured); an allowlist drifts | 2026-08-17 |
| D-10 | `docs/` summarizes and links to `references/*.md` as source of truth; normative detail never restated | Resolves REQ-12; honors "docs are pointers, never copies" and keeps prompt contracts out of scope | 2026-08-17 |
| D-14 | Phase 02 is a true move — content leaves README in the same commit it lands in docs/ | No window where the same prose lives twice; matches "docs are pointers, never copies" | 2026-08-18 |
| D-15 | No repo path reference may sit inside a fenced code block in docs/; verified by a truth | check-links.py masks fences, so a path moved into one loses CI coverage silently | 2026-08-18 |
| D-18 | Phase 03 writes `## Quick start` and `## Configuration` fresh, minimal, each linking out | Neither has a source to move; restructure-not-rewrite governed phase 02's move, not sections that never existed. SC-04 depends on Quick start | 2026-08-18 |
| D-19 | Port G3 to full parity with `_code_fence_mask` BEFORE any fenced block lands under `docs/` | LEARNINGS binds this on the first phase to add a fence; phase 03 is it. A guard that reads clean while blind is worse than none | 2026-08-18 |
| D-20 | README's opening condensed to 2–3 sentences; displaced prose MOVES to the docs/ pages owning those topics, not deleted | Serves REQ-03 and SC-01 without losing content phase 04's audit would flag | 2026-08-18 |
| D-17 | REQ-12b's enumeration corrected: providers/model tiers HAS a reference counterpart (hosts.md) | Factual error, not an open choice — hosts.md carries both sections, so D-10's summarize-and-link governs | 2026-08-18 |
| D-16 | Topics REQ-05 does not name fold into the nearest named page; planner states the mapping | Keeps 8 files and the 250-line cap without widening the requirement | 2026-08-18 |
| D-13 | `ARCHITECTURE.md` `## Link checking` reconciled to describe the implementation exactly | Three review rounds showed every omitted clause was a place the guard could fail while reporting green; a constraint doc that omits rules is untrue, not shorter | 2026-08-18 |
| D-12 | Anchor-slug backstop abstention accepted; rule left unproven rather than asserted | Repo contains no duplicate/inline-code/setext headings, so nothing grades it; resolving it by reading the slugger would be circular | 2026-08-18 |
| D-11 | REQUIREMENTS/PROJECT/ARCHITECTURE and the phase-01 plans exceed their size caps, accepted | Compressed twice; the remainder is normative and detail already caught a real defect. Cutting to hit a byte count trades correctness for a number | 2026-08-17 |
