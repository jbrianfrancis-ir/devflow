---
name: flow-map
description: Build or refresh codebase memory (MAP.md), distill docs (--docs path), or consolidate learnings (--refresh). Use on existing codebases before planning, or when the map is stale.
---

# flow-map

Context rules: read `.planning/STATE.md` first if present; the mapper works in its own context — don't re-explore here.

**Default** (also with `--refresh` of the map): spawn `flow-mapper` with: template path `${CLAUDE_PLUGIN_ROOT}/templates/codebase-map.md`, output `.planning/codebase/MAP.md` (cap 6KB, overwrite whole file). Print its ≤10-line digest. Note the map date in STATE.md's Last line.

**--docs `<path>`**: spawn `flow-mapper` in docs mode with the doc path(s); output `.planning/codebase/DOCS.md` (cap 3KB digest with pointers — never wholesale copies).

**--refresh** (learnings): read `.planning/LEARNINGS.md` + the `human_checks`/`deviations`/learnings from recent phase VERIFICATION and SUMMARY frontmatter; consolidate to ≤20 bullets (merge duplicates, drop obsolete, keep only rules future work must follow). Overwrite LEARNINGS.md.

Commit if commit_docs: `chore(flow): update codebase memory`.

End with the status line per `${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`: `FLOW: CONTINUE | map refreshed {date} | next: {per STATE}`.
