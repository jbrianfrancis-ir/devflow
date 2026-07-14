---
name: flow-migrate
description: Convert a GSD (open-gsd/gsd-core) project's .planning/ to DevFlow format - history and context preserved, originals archived. Use once per GSD project, instead of /flow-new.
---

# flow-migrate

Converts this project from GSD to DevFlow. Nothing is deleted: originals move to `.planning/archive/gsd/` and git history is untouched. Read `${CLAUDE_PLUGIN_ROOT}/references/migrate-gsd.md` first — it is the mapping contract.

**Pre-flight**: `.planning/` exists and looks like GSD (e.g. `gsd_state_version` in STATE.md frontmatter, or milestone dirs) — already-DevFlow → point to `/flow-status`; neither → point to `/flow-new`. Working tree clean. Git repo required.

1. **Branch** (per conventions.md): resolve the base branch (`dev` else `main`), create `flow/migrate-from-gsd` off it.

2. **Preview**: inventory `.planning/` top-level + phase dirs (names and counts only — don't read bodies here). Show the user the plan: what converts, what archives, the resumed position, and this warning: **after migration, never run `/gsd-*` commands in this project again** (both systems own `.planning/`). Get explicit confirmation — this is a GATE even in auto mode.

3. **Migrate**: spawn `flow-migrator` with paths: `${CLAUDE_PLUGIN_ROOT}/references/migrate-gsd.md`, `${CLAUDE_PLUGIN_ROOT}/templates/` (dir), `${CLAUDE_PLUGIN_ROOT}/references/conventions.md`, and the repo root. Keep only its ≤15-line report in context.

4. **Confirm ARCHITECTURE.md**: show the drafted file with its `{confirm}` markers; the user edits/approves versions and constraints (AskUserQuestion for the marked pins). It is not binding until approved. If the project has a UI, offer `/flow-design`.

5. **Verify the migration**: check every new `.planning/` file exists and is within its template cap; STATE.md position matches the migrator's report; requirement IDs in ROADMAP all exist in REQUIREMENTS.md; archive dir contains everything that isn't converted (nothing vanished: file count in ≈ converted + archived). Any mismatch → BLOCKED, fix before committing.

6. **Commit** on the migration branch: `chore(flow): migrate from GSD (originals in .planning/archive/gsd/)`, push origin, and route to `/flow-pr` (the merge is the human's acceptance of the migration). Print: converted/archived counts, resumed position, and next steps — typically `/flow-status`, then `/flow-map --refresh` if MAP.md was thin, then resume the roadmap.

End with the status line per `${CLAUDE_PLUGIN_ROOT}/references/autonomy.md` — migrated: `FLOW: GATE | migrated from GSD, PR pending | next: /flow-pr`; preview declined: `GATE`; verification mismatch: `BLOCKED`.
