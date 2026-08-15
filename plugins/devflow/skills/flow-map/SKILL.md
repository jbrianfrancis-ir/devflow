---
name: flow-map
description: Build or refresh codebase memory (MAP.md), distill docs (--docs path), or consolidate learnings (--refresh). Use on existing codebases before planning, or when the map is stale. Supports --provider native|claude|codex.
---

# flow-map

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

**Agent provider**: accept `--provider native|claude|codex`. Resolve and dispatch every role in this run exactly as `{devflow_root}/references/hosts.md` specifies. The selected provider applies to all delegated roles unless this skill explicitly calls an external consultation engine. A missing or failed peer is fail-closed; report `FLOW: BLOCKED` with remediation and never fall back silently.

Context rules: read `.planning/STATE.md` first if present; the mapper works in its own context — don't re-explore here.

**Default** (also with `--refresh` of the map): spawn `flow-mapper` with: template path `{devflow_root}/templates/codebase-map.md`, output `.planning/codebase/MAP.md` (cap 6KB, overwrite whole file; includes Env vars and Related repos sections — names only, omitted when empty). The mapper sets both `mapped` and `mapped_sha` (full `HEAD` SHA) — `mapped_sha` is what makes later staleness computable rather than guessed, so a map written without it will simply be fully re-mapped next time. Print its ≤10-line digest. Note the map date in STATE.md's Last line.

A full run here is always safe. The scoped drift refresh at the end of a phase (`/flow-execute` step 4b) is the cheap incremental path; this is the one that rebuilds from scratch when the map has drifted too far to patch, or when you want it re-derived from nothing.

**--docs `<path>`**: spawn `flow-mapper` in docs mode with the doc path(s); output `.planning/codebase/DOCS.md` (cap 3KB digest with pointers — never wholesale copies).

**--refresh** (learnings): read `.planning/LEARNINGS.md` + the `human_checks`/`deviations`/learnings from recent phase VERIFICATION and SUMMARY frontmatter; consolidate to ≤20 bullets (merge duplicates, drop obsolete, keep only rules future work must follow). Overwrite LEARNINGS.md.

Commit if commit_docs: `chore(flow): update codebase memory`.

End with the status line per `{devflow_root}/references/autonomy.md`: `FLOW: CONTINUE | map refreshed {date} | next: {per STATE}`.
