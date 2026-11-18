bump: minor
`destructive-git-guard.py` (installed by `/flow-hooks`) now also blocks `gh pr create` whose body (`--body`/`-b`, `--body-file`/`-F <path>`, or `-F -` heredoc) has no `Merge Danger: LOW|MEDIUM|HIGH — one-way|two-way door; blast radius: …` line; `--fill` or no body is blocked too. GitHub stays advisory; the block is the agent's own hook.
