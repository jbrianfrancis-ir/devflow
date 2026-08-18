# Installation

Start a new Codex thread after installation and invoke skills with `$flow-new`,
`$flow-plan`, `$flow-execute`, and the other `$flow-*` names. Codex cloud is not
part of the initial support contract.

Claude projects remain **self-bootstrapping**: `/flow-new` and `/flow-migrate` merge a `.claude/settings.json` declaration so fresh Claude sessions install DevFlow. Codex v1 uses the user-installed marketplace above and does not mutate user configuration from a project skill. Both also write `CLAUDE.md` and `AGENTS.md` pointer files at the repo root — marker-merged, never overwriting your content — so a session that never runs a `flow-*` skill still finds `.planning/`. They point at the artifacts rather than restating them; a copy of your constraints in an auto-loaded file goes stale and does more damage than no file at all. The declaration's exact JSON and the pointer-file merge rules are specified in [`conventions.md`](../plugins/devflow/references/conventions.md).

**Context repos (BlitzOS-style)**: DevFlow projects slot into [BlitzOS](https://github.com/blitzdotdev/blitzos)-style context repos — thin private repos that let cloud agents boot already knowing your repos and their state. Detection, company-brain rendering, `FLOW:` status parsing, session-record mapping, and the bootstrap contract are specified in [`docs/blitzos.md`](blitzos.md).
