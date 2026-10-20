# Hooks

DevFlow's hard rules — never commit to the base branch, secret-scan every commit and push,
protected paths need a human, a new or changed dependency needs a human, never force-push or run
anything destructive in git — are written into every agent's own instructions. `/flow-hooks`
scaffolds a deterministic backstop for five of them: Claude Code
[PreToolUse hooks](https://code.claude.com/docs/en/hooks) that fire whether or not an agent
followed its instructions — unless a Claude Code mod stops them first (see
[Known limitations](#known-limitations)).

## What it installs

| Guard | Fires on | Blocks |
|---|---|---|
| `base-branch-guard.py` | `Bash` | `git commit`/`git push` while checked out on the project's base branch |
| `protected-paths-guard.py` | `Edit`/`Write` | an edit to a path matching `protected_paths`, unless `DEVFLOW_PROTECTED_PATH_OK` is set |
| `secret-scan-guard.py` | `Bash` | `git commit`/`git push` whose diff matches conventions.md's secret pattern class |
| `dependency-guard.py` | `Bash`/`Edit`/`Write`/`MultiEdit` | an edit that adds or changes a dependency in a manifest or lockfile, or a package-add command — asks the human, naming the packages |
| `destructive-git-guard.py` | `Bash` | on any branch: a force push (`--force`, `-f`, `--force-with-lease`, a `+refspec`), `git reset --hard`, `git clean -f`, `git branch -D` |

Run `/flow-hooks` (optionally `--only base,secret,paths,deps,destructive` for a subset) in any project — no
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

## Dependency guard

A new or changed dependency is a human gate ([`autonomy.md`](../plugins/devflow/references/autonomy.md)).
`dependency-guard.py` watches these manifests and lockfiles: `package.json`, `package-lock.json`,
`pnpm-lock.yaml`, `yarn.lock`, `requirements*.txt`, `pyproject.toml`, `poetry.lock`, `uv.lock`,
`Pipfile`, `Pipfile.lock`, `*.csproj`, `Directory.Packages.props`, `packages.lock.json`,
`Cargo.toml`, `Cargo.lock`, `go.mod`, `go.sum`.

For an edit to one of them, it parses the file before and after and compares dependency names and
versions. An edit that adds a dependency or changes a version is gated, and the prompt names each
package. An unrelated edit to the same file (a script, a comment) passes, and so does removing a
dependency. A file that does not parse after the edit is could-not-check, and is gated too. A
`Bash` command that adds packages (`npm`/`pnpm install <pkg>`, `yarn add`, `pip install <pkg>`,
`uv add`, `poetry add`, `pipenv install <pkg>`, `dotnet add package`, `cargo add`, `go get`) is
gated with the package names. An install from an existing manifest (`npm install`,
`pip install -r requirements.txt`) is not.

The gate is a `PreToolUse` `"ask"` decision, so Claude Code prompts the human. In
`bypassPermissions` mode a prompt is not guaranteed, so the guard blocks (exit 2) instead. Record
the answer in `.planning/DECISIONS.md` ([provenance](provenance.md#decision-log)).

`dependency_manifests` in `.planning/config.json` (a list of filename globs) replaces the watched
list. A configured glob the guard has no parser for is gated on any content change.

## Destructive-git guard

`autonomy.md` makes anything destructive in git a human gate, and DevFlow never force-pushes.
`destructive-git-guard.py` blocks (exit 2) these on every branch, not only the base branch:

- `git push --force`, `-f` (also in a group such as `-uf`), `--force-with-lease`, and a refspec
  with a leading `+` (`git push origin +main`)
- `git reset --hard`
- `git clean -f` / `--force` (also `-fd`, `-xdf`); a dry run with `-n` passes
- `git branch -D`, and `--delete --force` / `-d -f`

`--force-with-lease` is blocked on purpose. The lease only stops you overwriting commits you have
not fetched; the remote branch is still rewritten, and the rule has no lease exception. There is no
override variable: when a human decides a force push or a hard reset is right, they run it in their
own terminal. The guard reads no config and needs no git repo. It looks inside `bash -c`, `sh -c`
and `eval`, and skips leading `VAR=value` assignments, `sudo`/`env`-style wrappers and git's
global options. `git checkout .` and `git restore .` are not blocked. The block-list idea comes from
Matt Pocock's git-guardrails-claude-code skill (concept only, no code).

## Known limitations

These guards match on the literal `Bash` command string and a computed diff/file listing — they
are not a sandbox and cannot see through indirection:

- **Wrapper scripts and indirection.** A command like `bash release.sh` or a Makefile/npm target
  that internally runs `git commit`/`git push` never contains that literal substring in
  `tool_input.command`, so neither `base-branch-guard.py` nor `secret-scan-guard.py` sees it. This
  is the residual gap — everything else below is handled. The same gap applies to
  `destructive-git-guard.py`, and it also cannot see a git alias (`git config alias.fp 'push -f'`
  then `git fp`).
- **Manifests changed by a shell command.** `dependency-guard.py` reads `Edit`/`Write`/`MultiEdit`
  content and recognizes package-add commands. A manifest rewritten by `sed`, `echo >>` or a script
  is not seen.

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

**Claude Code mods run before these guards.** Since Claude Code 2.1.287, a
[mod](https://code.claude.com/docs/en/plugins/mods/overview) that a user installs runs in-process
before the guards. The guards are `PreToolUse` hooks in the project's `.claude/settings.json`, so
they run only after the last mod passes the tool call on. A mod that answers a tool call itself
stops the guards from running, and a mod on `tool.check` can approve a call that a guard blocked.
Only `PreToolUse` hooks in managed settings run before every mod, and only their block is final
([the order mods run in](https://code.claude.com/docs/en/plugins/mods/events#the-order-mods-run-in)).
To keep the guarantee, do not install mods you do not trust (`claude plugin validate` lists what a
mod hooks). On a machine with managed settings, put the guards in managed settings, or set the
built-in guard's
[`allowManagedModsOnly`](https://code.claude.com/docs/en/plugins/mods/admin#stop-user-installed-mods-from-loading)
option so that no mod a user installs runs.
