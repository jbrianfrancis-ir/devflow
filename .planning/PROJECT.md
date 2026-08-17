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
| D-11 | REQUIREMENTS/PROJECT/ARCHITECTURE and the phase-01 plans exceed their size caps, accepted | Compressed twice; the remainder is normative and detail already caught a real defect. Cutting to hit a byte count trades correctness for a number | 2026-08-17 |
