---
name: flow-workstream
description: Manage parallel workstreams as git worktrees - new, list, drop. Args - new <slug> [--phase N], list, drop <slug>. Use to run more than one phase or feature at once without two agents fighting over one checkout.
---

# flow-workstream

Context rules: read `.planning/STATE.md`, `.planning/config.json` (`git` block), and `${CLAUDE_PLUGIN_ROOT}/references/conventions.md` (**Parallel workstreams** — the reconciliation table and hidden edges are the rules this skill enforces) first. Keep output terse.

One workstream = one git worktree = one `flow/<slug>` branch = one PR. Run this from the main checkout. No args → `list`.

## list (default)
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/flow-fleet.py <repo-root> --depth 1` — the scanner enumerates this repo's worktrees and reads each one's position, FLOW state, staleness, and dirty count. Print it verbatim, then name the one to touch first. (`/flow-status --all` is the same board across every repo.)

## new `<slug>` [--phase N]
**Pre-flight**: git repo with at least one commit; `git worktree list` doesn't already have `flow/<slug>`; the base branch from `config.json` is current (`git fetch` first when there's a remote). If `--phase N`, that phase exists in ROADMAP and isn't already owned by another workstream — check the other worktrees' STATE Position lines. A phase already in flight elsewhere is a hard stop, not a warning.

**Independence check before creating anything** — the same test `/flow-execute` applies to same-wave plans, applied to streams. Ask whether this workstream and every in-flight one share: files, the migration chain, the lockfile, generated committed output, or shared dev infrastructure. Any shared mutable resource is a hidden edge → say so and recommend serializing instead. Creating the worktree anyway is the user's call, made explicitly.

1. **Create**: `git worktree add <dir> -b flow/<slug> <base>`, where `<dir>` defaults to a sibling `../<repo>-<slug>` (override via `config.json` `worktrees.dir`). Never nest a worktree inside the repo.
2. **Record**: in the new worktree's `.planning/config.json`, set `git.branch` to `flow/<slug>` and add `"workstream": {"slug": "<slug>", "port_offset": <index × 100>, "phase": <N|null>}`. The index is the count of existing DevFlow worktrees. Both files are branch-local per conventions.md — that divergence is expected, not a conflict to fix.
3. **Merge hygiene** (once per repo, on the base branch — skip if present): add to `.gitattributes`
   ```
   .planning/JOURNAL.md merge=union
   .planning/LEARNINGS.md merge=union
   ```
   `union` is a built-in git driver; no config needed. Everything else in `.planning/` reconciles per the conventions.md table.
4. **Local setup**: list by NAME the untracked files the new worktree lacks that the app needs (`.env*`, certs, local settings — from ARCHITECTURE.md's Environment manifest and `.gitignore`). Offer to copy them across verbatim — never read, print, or diff their contents; declining leaves them as `user_setup` items. Then name the port offset and what must use it (Aspire dashboard, service ports, dev database name) so the two streams can run side by side.
5. **Report**: the worktree path, branch, port offset, and the exact next command — `cd <dir> && /flow-plan N` (or `/flow-status`). Prepend a `.planning/JOURNAL.md` line in the **main** checkout.

## drop `<slug>`
Destructive and outward-adjacent — always a human gate, even in `--auto`.

**Pre-flight, all reported before asking**: uncommitted changes in the worktree (`git status --porcelain`), commits not pushed to origin (`git log origin/flow/<slug>..flow/<slug>`), and whether the branch is merged into the base (`git branch --merged <base>`). Unmerged or unpushed work is named explicitly — this is the one place DevFlow can destroy work that was never written down.

Also run the **scope-conformance** check before dropping a merged stream: `git diff --name-only <base>...flow/<slug>` against the union of `files_modified` across the phase's plans. Paths outside it are advisory, but they are the last cheap chance to notice that a stream reached beyond its brief into shared state — report them, then proceed. Base unavailable → report the check as not run, never as clean.

Confirmed → `git worktree remove <dir>` then `git branch -d flow/<slug>` (plain `-d`; `-D` on an unmerged branch requires a second explicit confirmation). Then `git worktree prune`. Log a `.planning/JOURNAL.md` line in the main checkout.

## Status line
Per `${CLAUDE_PLUGIN_ROOT}/references/autonomy.md` — created: `FLOW: CONTINUE | workstream <slug> at <dir> | next: cd <dir> && /flow-plan N`; listed: `FLOW: CONTINUE | N workstreams, M need a human | next: cd <dir> && <command>`; hidden edge found or drop awaiting confirmation: `GATE`.
