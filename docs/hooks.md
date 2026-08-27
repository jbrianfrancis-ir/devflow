# Hooks

DevFlow's hard rules — never commit to the base branch, secret-scan every commit and push,
protected paths need a human — are written into every agent's own instructions. `/flow-hooks`
scaffolds a deterministic backstop for three of them: Claude Code
[PreToolUse hooks](https://code.claude.com/docs/en/hooks) that fire whether or not an agent
followed its instructions.

## What it installs

| Guard | Fires on | Blocks |
|---|---|---|
| `base-branch-guard.py` | `Bash` | `git commit`/`git push` while checked out on the project's base branch |
| `protected-paths-guard.py` | `Edit`/`Write` | an edit to a path matching `protected_paths`, unless `DEVFLOW_PROTECTED_PATH_OK` is set |
| `secret-scan-guard.py` | `Bash` | `git commit`/`git push` whose diff matches conventions.md's secret pattern class |

Run `/flow-hooks` (optionally `--only base,secret,paths` for a subset) in any project — no
`.planning/` required. It copies the scripts into `.claude/hooks/` and merges idempotent
`PreToolUse` entries into `.claude/settings.json`, leaving unrelated settings untouched. Those
are the target repo's own files; the skill writes them but never commits on your behalf.

## Why a backstop

A guard here is best-effort, not the sole control: each script fails open (exit 0) with a loud
stderr warning whenever it cannot determine the answer — no git repo, unreadable config — because
blocking on infrastructure noise would cost more than the gap it closes. The rules themselves,
including the exact secret-scan pattern and the fail-closed discipline around it (only a human
clears a hit, including false positives), are specified in
[`conventions.md`](../plugins/devflow/references/conventions.md).

## Configuration it reads

`base-branch-guard.py` and `secret-scan-guard.py` read `git.base` from `.planning/config.json`
(falling back to `main`/`master` if absent); `protected-paths-guard.py` reads `protected_paths`, a
glob list, from the same file. Full script contracts live in
`plugins/devflow/templates/hooks/*.py`.

## Known limitations

These guards match on the literal `Bash` command string and a computed diff/file listing — they
are not a sandbox and cannot see through indirection:

- **Wrapper scripts and indirection.** A command like `bash release.sh` or a Makefile/npm target
  that internally runs `git commit`/`git push` never contains that literal substring in
  `tool_input.command`, so neither `base-branch-guard.py` nor `secret-scan-guard.py` sees it. This
  is the residual gap — everything else below is handled.

`secret-scan-guard.py` also covers, not just an already-staged diff: `git commit -a`/`-am`/`--all`
(scanned via a working-tree-vs-HEAD diff, not `--cached` alone); a binary or zero-byte credential
file (`.pfx`/`.pem`/etc.) added or modified, which emits no `+++`/`+` lines to scan; and a
brand-new untracked file staged and committed in one chained command (`git add newfile.pem &&
git commit`), which has no diff history to catch it by. That last case is handled deliberately
conservatively: rather than compute exactly which untracked file(s) a `git add` invocation would
stage — defeated by a glob, a shell variable, or the add and commit landing on separate lines of
the same command — the guard scans **every** currently untracked file whenever `git add` appears
anywhere in the command at all. A pure deletion of a credential-shaped file is not blocked —
removing a leaked secret is remediation, not a new hit.

Treat the wrapper-script gap as the reason the underlying agent-instruction rules in
`conventions.md` stay primary — the hook is a backstop for the case an agent ignores them, not a
substitute for following them.
