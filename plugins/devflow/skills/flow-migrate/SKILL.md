---
name: flow-migrate
description: Convert a GSD (open-gsd/gsd-core) project's .planning/ to DevFlow format - history and context preserved, originals archived. Use once per GSD project, instead of /flow-new. Supports --provider native|claude|codex.
---

# flow-migrate

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

**Agent provider**: accept `--provider native|claude|codex`. Resolve and dispatch every role in this run exactly as `{devflow_root}/references/hosts.md` specifies. The selected provider applies to all delegated roles unless this skill explicitly calls an external consultation engine. A missing or failed peer is fail-closed; report `FLOW: BLOCKED` with remediation and never fall back silently.

Converts this project from GSD to DevFlow. Nothing is deleted: originals move to `.planning/archive/gsd/` and git history is untouched. Read `{devflow_root}/references/migrate-gsd.md` first — it is the mapping contract.

**Pre-flight**: `.planning/` exists and looks like GSD (e.g. `gsd_state_version` in STATE.md frontmatter, or milestone dirs) — already-DevFlow → point to `/flow-status`; neither → point to `/flow-new`. Working tree clean. Git repo required.

1. **Branch** (per conventions.md): resolve the base branch (`dev` else `main`), create `flow/migrate-from-gsd` off it.

2. **Preview**: inventory `.planning/` top-level + phase dirs (names and counts only — don't read bodies here).

   **Resolve the GSD skill roster** — step 3 writes it to `.claude/settings.json` as `skillOverrides`. Enumerate from your own skill listing, else glob the host skill directories for `gsd-*`. Then **filter every name against `^gsd-[a-z0-9-]+$` and drop what does not match**, listing each dropped name in the preview and the migration report. Skill names reach this roster from directory names, and skills are discovered at *project* scope as well as user scope — so on a migration, which by definition runs against a repo you did not write, part of this roster is attacker-controlled input on its way into a machine-level config file. The migrator composes that file as text and has no escaping layer, so a name carrying a quote and a brace writes whatever the repo author chose — `permissions.allow` included — into settings every future session loads. The pattern is the whole defence; a name that cannot pass it is not a skill this guard was meant to cover.

   Distinguish **empty** from **could not enumerate** (conventions.md → Fail-closed guards). A host with no GSD skills installed is a legitimate empty roster: write no key. A skill listing you could not read, or a glob that errored, is *not* an empty roster — report `GSD roster not verified — guard not established`, treat it as attention-needed, and do not tell the user the block is in force.

   Show the user the plan: what converts, what archives, the resumed position, how many `/gsd-*` skills get disabled in this repo, any names dropped by the filter, and this warning: **after migration, never run `/gsd-*` commands in this project again** (both systems own `.planning/`) — enforced by the `skillOverrides` block in Claude Code, advisory only in Codex, which has no equivalent setting. Claim enforcement only when the roster was actually established. Get explicit confirmation — this is a GATE even in auto mode.

3. **Migrate**: first **snapshot** `.claude/settings.json` to `.planning/archive/gsd/settings.pre-migration.json` if it exists (step 5 diffs against this; without it the "kept every prior key" check has nothing to compare and can only ever pass). Then spawn `flow-migrator` with paths: `{devflow_root}/references/migrate-gsd.md`, `{devflow_root}/templates/` (dir), `{devflow_root}/references/conventions.md`, the repo root, and the snapshot path — plus the step-2 GSD skill roster, already filtered (an empty roster means write no `skillOverrides` key, not an empty one). Keep only its ≤15-line report in context.

4. **Confirm ARCHITECTURE.md**: show the drafted file with its `{confirm}` markers; the user edits/approves versions and constraints (use the host question mechanism for the marked pins). It is not binding until approved. If the project has a UI, offer `flow-design` using the host command prefix.

5. **Verify the migration**: check `.claude/settings.json` still parses as JSON, carries the bootstrap keys and a `skillOverrides: "off"` entry for every name in the step-2 roster, contains no `skillOverrides` key that fails `^gsd-[a-z0-9-]+$`, and holds every key present in the step-3 snapshot — **diffed against that file, not asserted**. No snapshot and a pre-existing settings file → the check is `not run`, which is BLOCKED, never pass (conventions.md → Fail-closed guards): a settings file the migration corrupted breaks the project for every future session, which is why this is checked before the planning files; check every new `.planning/` file exists and is within its template cap; STATE.md position matches the migrator's report; requirement IDs in ROADMAP all exist in REQUIREMENTS.md; archive dir contains everything that isn't converted (nothing vanished: file count in ≈ converted + archived). Any mismatch → BLOCKED, fix before committing.

6. **Commit** on the migration branch: start `.planning/JOURNAL.md` with the migration line (`{devflow_root}/templates/journal.md`), then `chore(flow): migrate from GSD (originals in .planning/archive/gsd/)`, push origin, and route to `/flow-pr` (the merge is the human's acceptance of the migration). Print: converted/archived counts, resumed position, and next steps — typically `/flow-status`, then `/flow-map --refresh` if MAP.md was thin, then resume the roadmap.

End with the status line per `{devflow_root}/references/autonomy.md` — migrated: `FLOW: GATE | migrated from GSD, PR pending | next: /flow-pr`; preview declined: `GATE`; verification mismatch: `BLOCKED`.
