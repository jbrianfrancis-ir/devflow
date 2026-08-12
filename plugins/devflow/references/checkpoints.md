# Checkpoints

Three types:
- **decision** — the user must choose between approaches. Present options + trade-offs. Blocks execution.
- **human-action** — the user must do something the agent can't: create an account, set a secret, click a console, verify a suspicious package, clear a secret-scan hit. Give exact steps. Blocks execution.
- **human-verify** — the user confirms built behavior works. NOT blocking mid-execution: batch to end of phase. Executors record these in SUMMARY frontmatter `human_checks`; the verifier consolidates them into one list in VERIFICATION.md. (Every mid-flight stop costs a full executor cold-start — only block for the first two types.)

## Executor checkpoint protocol
Stop at the checkpoint task and return exactly:

```
CHECKPOINT
plan: NN-MM | task: N | type: decision|human-action
done: [task numbers + commit SHAs completed so far]
need: {what the user must decide or do — specific}
resume: {what to tell the executor to continue}
```

The orchestrator presents this to the user, then respawns the executor with: the plan path, "tasks 1..K committed (confirm via git log), continue from task K+1", and the user's answer. On continuation the executor verifies the claimed commits exist before resuming — never re-does committed work.
