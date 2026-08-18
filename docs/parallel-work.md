# Parallel work

The bottleneck in agent-assisted work isn't decomposition — it's losing track of what each session is doing, and reading its output cold at the end.

## Fleet board
`/flow-status --all` runs `plugins/devflow/scripts/flow-fleet.py`, which walks your roots for `.planning/STATE.md` and prints one row per project: phase, status, last `FLOW:` state (parsing contract: [status-contract.md](status-contract.md)), age, dirty/stale/on-base flags, and the exact next command. It reads files, never screens, so it works under every multiplexer and survives their updates. Attention-first ordering, a "needs a human" footer with copy-pasteable `cd … && /flow-…` lines, `--json` for programmatic drivers, and exit status `1` when anything needs you. Configure roots once in `~/.devflow/fleet.json`: `{"roots": ["~/dev"], "stale_days": 3}`.

## Workstreams
`/flow-workstream new <slug>` cuts a git worktree on its own `flow/<slug>` branch so two phases run side by side without fighting over one checkout. It refuses streams that share a hidden edge (migration chain, lockfile, generated output, shared dev database), assigns a port offset so both apps can run, and names the untracked local files the new tree lacks. `.planning/` reconciliation at merge — which artifacts are branch-local, which merge as unions, which are single-writer — is specified in [`conventions.md`](../plugins/devflow/references/conventions.md) → Parallel workstreams.
