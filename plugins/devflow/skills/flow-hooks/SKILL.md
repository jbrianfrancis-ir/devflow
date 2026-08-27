---
name: flow-hooks
description: Scaffold deterministic PreToolUse hooks (base-branch guard, protected-paths guard, secret-scan guard) into .claude/settings.json, hardening three of DevFlow's instruction-only hard rules so they hold even if an agent ignores them. Args - optional --only base,secret,paths to install a subset; default installs all three. No .planning/ required.
---

# flow-hooks

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

Context rules: read `.planning/STATE.md` first if present — no `.planning/` is required to run this
skill at all. When `.planning/config.json` exists, note it: `git.base` and `protected_paths` are the
fields the installed guards read themselves at runtime, not something this skill interprets.

This installs a **backstop**, not a replacement. The underlying rules — never commit to the base
branch, secret-scan every commit/push, protected paths need a human — stay written in
`{devflow_root}/references/conventions.md` and in every agent's own instructions. These hooks exist for
the case where an agent doesn't follow them.

## Guards

| Guard | Fires on | Blocks |
|---|---|---|
| `base-branch-guard.py` | `Bash` | `git commit`/`git push` while checked out on the project's base branch |
| `protected-paths-guard.py` | `Edit\|Write` | an edit to a path matching `protected_paths`, unless `DEVFLOW_PROTECTED_PATH_OK` is set |
| `secret-scan-guard.py` | `Bash` | `git commit`/`git push` whose diff matches conventions.md's secret pattern class |

Full script contracts — exact message text, exit codes, the config fields each one reads — live in
the scripts themselves at `{devflow_root}/templates/hooks/*.py`; read them there rather than
restating them here.

## Selection

Default: install all three. `--only <list>` (comma-separated, any order) installs a subset:
`base`→`base-branch-guard`, `secret`→`secret-scan-guard`, `paths`→`protected-paths-guard`. An
unrecognized token is a bad-args stop, not a silent skip.

## Install, per selected guard

1. Copy `{devflow_root}/templates/hooks/<name>.py` to `.claude/hooks/<name>.py` in the target repo
   (create `.claude/hooks/` if it doesn't exist yet); `chmod +x` the copy.
2. Merge into `.claude/settings.json` — read the existing file, or start from `{}` if absent; never
   touch unrelated keys (same discipline as the Plugin self-bootstrap merge in `conventions.md`):
   - ensure `hooks.PreToolUse` exists and is a list;
   - append one block per guard, matcher per the table above:
     ```json
     {"matcher": "<Bash|Edit|Write>", "hooks": [{"type": "command", "command": "python3 \"${CLAUDE_PROJECT_DIR}/.claude/hooks/<name>.py\""}]}
     ```
   - **idempotent**: before appending, scan every existing `hooks.PreToolUse[].hooks[].command` for
     this guard's `.claude/hooks/<name>.py` path. If it already appears anywhere in the list, skip
     that guard and report it as already installed — never append a duplicate entry.

## Report

Print, per guard, whether it was installed or was already present. Remind the user that
`.claude/hooks/` and `.claude/settings.json` are the **target repo's own files** — this skill only
writes them, it never commits on the user's behalf; commit them once satisfied.

End with the status line per `{devflow_root}/references/autonomy.md`:
`FLOW: CONTINUE | N hooks installed, M already present | next: {per STATE}`.
