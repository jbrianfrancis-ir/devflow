<!-- .planning/PROJECT.md — cap 2KB. Overwrite sections, don't append. -->
# DevFlow Documentation Restructure

## What
DevFlow's `README.md` has grown to 167 lines / 31.6KB and carries nine distinct
topics, from installation to a dense attribution appendix. This project splits it
into focused documents under `docs/`, leaving a README that does what a README is
supposed to do — get someone installed, running, and oriented — and adds a
stdlib-only CI check so the resulting web of internal links cannot silently rot.

Primary reader: a developer evaluating or adopting DevFlow from its GitHub page.

## Core value
A newcomer reaches a working first phase from the README alone, and every reader
who wants depth finds exactly one authoritative page for the topic they came for.

## Out of scope
- Rewriting DevFlow's behavior, skills, agents, or references — this is documentation only.
- A docs build system or hosted site (MkDocs/Docusaurus/Jekyll); `docs/` stays plain markdown read on GitHub.
- Restructuring `plugins/devflow/references/*.md` — those are agent-facing prompt contracts, not reader docs.
- Moving or editing `docs/blitzos.md` and `docs/status-contract.md`; they are existing external-consumer contracts.
- Editing `NOTICE`, `LICENSE`, or any `plugin.json` / `marketplace.json` version field.
- External-URL link checking (makes CI depend on third-party uptime).
- Translations / i18n.

## Key decisions
| ID | Decision | Why | Date |
|----|----------|-----|------|
| D-01 | README keeps install, quickstart, full command table, config basics, docs index, license/ack pointers — target ≤110 lines | The command table is the at-a-glance surface that makes DevFlow legible; losing it costs more than the lines it spends | 2026-08-17 |
| D-02 | `docs/` stays flat topic files plus a `docs/README.md` index | Matches the existing two docs; keeps every inbound link one level deep and avoids relocating current files | 2026-08-17 |
| D-03 | Acknowledgements move to `docs/acknowledgements.md`; README keeps a one-line pointer; `NOTICE` untouched | NOTICE is the legal artifact — narrative credit muddies its purpose | 2026-08-17 |
| D-04 | Internal-link check is `scripts/check-links.py`, stdlib-only | Repo has zero third-party dependencies; a lychee/npm action would break that property | 2026-08-17 |
| D-05 | Inbound references updated repo-wide, including prose mentions, not just markdown links | `flow-status/SKILL.md` names README sections in prose — a link checker cannot catch those | 2026-08-17 |
| D-06 | No deployable surface: `/flow-harden`, `/flow-uat`, `/flow-release` are N/A; integration ends at merge | This repo ships as a plugin via marketplace, not a deployment | 2026-08-17 |
