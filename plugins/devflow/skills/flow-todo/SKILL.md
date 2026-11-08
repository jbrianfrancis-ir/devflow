---
name: flow-todo
description: Capture an idea or task for later without derailing current work; no args lists open items. Args - the idea text, or --incident <pasted alert, ServiceMonitor output, or App Insights/incident link>.
---

# flow-todo

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

With args: append `- [ ] YYYY-MM-DD: {idea}` to `.planning/TODOS.md` (create if missing; cap ~30 lines — when over, ask the user which done/stale lines to drop). Confirm in one line and return to whatever was happening. `--incident` (a production alert to handle later) → exactly as `/flow-debug --incident`, but `--route todo`: pasted text and any link each saved to a scratch file with the file-write tool, never through a shell, links never fetched, then `python3 {devflow_root}/scripts/flow-incident.py --repo . --route todo --text-file <file>` and/or `--link-file <file>` (plus `--at`/`--version`/`--id` exactly as `/flow-debug` says), then delete the scratch files; it appends the line itself; a repeat while that line is open adds none. No args: print open items with indices; offer to check off done ones or promote one to `/flow-quick` / a roadmap phase.
End with the status line per `{devflow_root}/references/autonomy.md`: `FLOW: CONTINUE | todo captured/listed | next: {per STATE}`.
