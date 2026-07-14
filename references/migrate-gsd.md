# GSD → DevFlow migration map

Read by /flow-migrate and the flow-migrator agent. Source: a GSD (open-gsd/gsd-core) project's `.planning/` (+ `.gsd/`). GSD versions vary — convert what you recognize, archive everything else. **Nothing is deleted**: originals move to `.planning/archive/gsd/` (same relative paths), and git history is untouched.

## File map
| GSD | DevFlow | How |
|-----|---------|-----|
| `PROJECT.md` | `PROJECT.md` (≤2KB) | Distill: what/core value/out of scope; Key Decisions table from GSD decisions (keep IDs, cap 10 rows — older rows to archive) |
| `REQUIREMENTS.md` | `REQUIREMENTS.md` (≤3KB) | One line per requirement + acceptance hint. Preserve GSD requirement IDs verbatim (ROADMAP/plans cite them) |
| `ROADMAP.md` (+ milestones) | `ROADMAP.md` (≤2KB) | Flatten milestones into one phase table, keeping phase numbers/slugs. Completed → `verified`; current → its true status. Per completed milestone add one summary line to PROJECT.md |
| `STATE.md` | `STATE.md` (≤1.5KB) | From template: Position/Decisions(≤5)/Blockers/Session from GSD's Current Position + Accumulated Context. Drop frontmatter metrics, velocity tables, progress bars |
| `config.json` | `config.json` | Fresh DevFlow shape: `mode` (from GSD autonomy settings, default interactive), `commit_docs` (carry over), `deploy:{tool:"aspire+azd"}`, `git` block resolved from the repo (base/origin/upstream/branch). Archive the GSD original |
| STATE "Learnings"/Accumulated Context; extract-learnings output | `LEARNINGS.md` (≤20 bullets) | Mine lasting rules only; drop narration |
| STATE pending todos; inbox/backlog files | `TODOS.md` | One checkbox line each |
| `codebase/` or map-codebase output | `codebase/MAP.md` (≤6KB) | Distill if present; else offer `/flow-map` after migration |
| `research/*.md` | phase `RESEARCH.md` or `codebase/DOCS.md` digest | Keep if it informs remaining phases; else archive |
| `phases/<done>/` (SUMMARY exists + verified) | archive as-is | Immutable history. Optionally add a frontmatter-only SUMMARY stub if the dir is referenced by remaining work |
| `phases/<current>/` PLAN.md files | convert in place | GSD plan frontmatter (wave/depends_on/files_modified/must_haves/requirements) is DevFlow-compatible. Strip: `type: tdd` (→ note in action), `<execution_context>` @-includes, `<threat_model>` (fold real mitigations into task actions), model hints. Tasks/`<verify>`/`<done>` carry over |
| `UAT.md`, `deferred-items.md` | `deploy/UAT-PLAN.md` seed / TODOS.md | Deferred items → TODOS; old UAT content informs the next `/flow-uat` round |
| `.gsd/`, capability state, mempalace/graphify/intel artifacts | archive | No DevFlow equivalent by design |
| Anything unrecognized | archive | List in the migration report |

## New files GSD lacks (created during migration)
- **`.claude/settings.json`** — the plugin self-bootstrap block (see conventions.md), so every future session — cloud included — installs DevFlow at start. Merged, never overwritten.
- **`ARCHITECTURE.md`** — the human's constraints file. Draft from manifests + GSD PROJECT/config, but the human confirms/edits before it becomes binding (versions especially).
- **`DESIGN.md`** — only via `/flow-design` if the project has a UI and a Claude Design system.
- **`deploy/PIPELINE.md`** — not created at migration; `/flow-harden` initializes it.

## Invariants
- Requirement IDs and phase numbers/slugs never change meaning during migration.
- The migration itself is one commit on a feature branch (`flow/migrate-from-gsd`), per conventions.md — review before merging.
- After migration, `/gsd-*` commands must not run in this project again (both systems own `.planning/`). Remove or disable project-level GSD artifacts (project `.claude/` gsd settings, `.gsd/`, GSD sections in CLAUDE.md) as part of the migration commit; uninstalling the GSD plugin globally is the human's choice.
