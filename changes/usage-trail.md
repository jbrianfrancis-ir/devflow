bump: minor
`flow-usage.py trail --repo . --session <jsonl|id>` (opt-in: `"usage_report": true` and `"usage_trail": true`) prints a read-only trail of one Claude Code session from its saved transcript: a three-line summary, numbered reads/commands/edits/MCP calls with model changes, each helper's exact task text and its own steps, and files read inside shell commands as second evidence.
