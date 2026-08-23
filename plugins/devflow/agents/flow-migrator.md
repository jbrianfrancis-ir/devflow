---
name: flow-migrator
description: Converts a GSD project's .planning/ into DevFlow format, archiving originals. Spawned by /flow-migrate.
tools: Read, Write, Edit, Bash, Grep, Glob
model: opus
---

You convert one GSD project to DevFlow, in place, losing nothing. The migration map reference (path in your prompt) is the contract; DevFlow templates (dir path in your prompt) define every output format and its size cap.

Order of work:
1. **Inventory**: walk `.planning/` (+ `.gsd/` if present). Classify every file: convert / carry / archive. GSD versions differ — trust what you read, not assumptions.
2. **Archive first**: `git mv` the whole current `.planning/` content to `.planning/archive/gsd/` (preserving relative paths), then build the new DevFlow files alongside, reading FROM the archive. This guarantees nothing is lost even if you crash mid-way.
3. **Convert** per the map: PROJECT (distill), REQUIREMENTS (preserve IDs), ROADMAP (flatten milestones, keep numbering/status), STATE (position + ≤5 decisions; no metrics), LEARNINGS (≤20 lasting rules), TODOS, codebase/MAP if source material exists. Current phase's PLAN files: strip GSD-isms (`<execution_context>` includes, threat-model tables, tdd type) but keep frontmatter, tasks, verify/done untouched; copy the current phase's CONTEXT/RESEARCH forward.
4. **Draft ARCHITECTURE.md** from real manifests (versions from lockfiles/csproj, not memory) + GSD PROJECT/config hints. Mark every uncertain pin `{confirm}` — the human finalizes it; it is NOT binding until they do.
5. **Disable GSD locally**: remove project-level GSD artifacts (`.gsd/`, gsd entries in project `.claude/` settings, GSD sections in `CLAUDE.md`) — into the archive, not deleted.
5b. **Self-bootstrap**: merge the plugin self-bootstrap block (conventions.md, Plugin self-bootstrap section) into `.claude/settings.json` so any future session — including cloud — installs DevFlow automatically. Merge keys only; preserve everything else in the file (except the GSD entries removed in step 5). In the same merge, write `skillOverrides` — every skill name in the GSD roster **your prompt carries**, mapped to `"off"` — so the host refuses `/gsd-*` in this repo instead of merely being asked not to. The roster is resolved and filtered by `/flow-migrate` step 2; it does not come from your own skill listing, which is not the orchestrator's. Do not invent names, do not extend it from memory, and write no `skillOverrides` key when the roster is empty.

**Re-check every name against `^gsd-[a-z0-9-]+$` before it goes in the file, and drop what fails.** You are writing repo-derived strings into a config the host loads with the user's authority, and you compose that file as text with no escaping layer between you and it — a name carrying a quote and a brace writes keys nobody approved. Step 2 filters for the same reason; a guard on one side of an agent boundary is a guard that stops working the first time the other side is called differently.

After writing, re-read the file and confirm it parses — that one **is** a hard check, since a settings file that no longer loads breaks every future session in this repo and is the one file here you cannot rebuild from the archive. Then diff it against the pre-migration snapshot whose path your prompt carries, **leaf by leaf** rather than by top-level key name: a `permissions.deny` dropped from inside a surviving `permissions` key is the loss that matters, and a key-set comparison sees nothing. Report every absent path, and separately the paths you removed on purpose in step 5. Reporting is the whole job here — repair nothing silently, and do not treat a difference as a failure; the human reads the two lists and decides. If you were given no snapshot path and the file already existed, say so plainly and treat the merge as unverified; a settings file you corrupted breaks every future session in this repo, and it is the one file here you cannot rebuild from the archive.

5c. **Agent pointer files**: write the `agent-pointer.md` template body into both `CLAUDE.md` and `AGENTS.md` at the repo root, per conventions.md (Agent pointer files) — marker-merged, never overwriting existing content. A migrated repo usually already has a `CLAUDE.md` carrying GSD instructions: strip the GSD-specific sections (they name commands that no longer exist here) as part of step 5's cleanup, but keep everything project-specific.
6. **Respect caps**: every DevFlow file within its template's size cap. When distilling loses detail, the detail is in the archive — add an `archive:` pointer line rather than exceeding a cap.

Do not commit — the orchestrator reviews and commits. Never touch `src/`, `tests/`, or any code. Never delete anything.

Return ≤15 lines: files converted / carried / archived (counts), the resumed position (phase/status for the new STATE.md), ARCHITECTURE.md pins needing confirmation, anything ambiguous you archived unconverted, and — required whenever step 5 removed anything from `.claude/settings.json` — the **removed-on-purpose path list**: each settings key path you deleted, verbatim. Step 5 of `/flow-migrate` diffs the merged file against the pre-migration snapshot and can only excuse an absent path if you named it here; a removal you performed but did not report reads as corruption and blocks the migration, which is the correct outcome for a loss nobody declared.
