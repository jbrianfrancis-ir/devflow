---
name: flow-todo
description: Capture an idea or task for later without derailing current work; no args lists open items. Args - the idea text.
---

# flow-todo

With args: append `- [ ] YYYY-MM-DD: {idea}` to `.planning/TODOS.md` (create if missing; cap ~30 lines — when over, ask the user which done/stale lines to drop). Confirm in one line and return to whatever was happening.

No args: print open items with indices; offer to check off done ones or promote one to `/flow-quick` / a roadmap phase.

End with the status line per `${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`: `FLOW: CONTINUE | todo captured/listed | next: {per STATE}`.
