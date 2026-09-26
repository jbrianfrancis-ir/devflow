---
name: flow-undo
description: Undo unpublished commits on the current feature branch - preview what would be removed, ask the human, then apply only on explicit confirmation, keeping a backup ref. Args - the commit to return to (SHA or rev). Explicit-only; never touches published work, a merge, or the base branch.
disable-model-invocation: true
---

# flow-undo

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

Context rules: read `.planning/STATE.md` first if present — no `.planning/` is required. Keep output terse.

**Explicit-only.** A human invokes this by name; the model never auto-invokes it. Applying an undo is destructive git, so it is a human gate every time (`{devflow_root}/references/autonomy.md` → Human gates) — there is no `--auto`, and `/goal`//`/loop` never answer it.

**The helper is the only undo authority.** Every git effect goes through `python3 {devflow_root}/scripts/flow-undo.py`. Never run `git reset`, `git revert`, `git push`, `git branch -D`, or any other git write yourself, and never compute, shorten, or substitute a SHA — pass the helper's own values back verbatim.

## One invocation

1. **Target.** The argument names the commit to return to (`HEAD~1` means "undo the last commit"). No argument → ask which commit; never guess.
2. **Preview.** `python3 {devflow_root}/scripts/flow-undo.py preview --repo <repo-root> --to <target>`. It prints JSON: `branch`, `head`, `target`, `commits` (what would be removed, newest first), and either `apply` parameters or `blocked` reasons.
3. **Blocked** (exit 1, non-empty `blocked`) → report every reason verbatim and stop. Do not work around one: a `published` commit needs `git revert` on a new commit through normal Flow work, a `could-not-check` means publication is unknown and is never read as unpublished, a `merge-commit` or `base-branch` is out of scope for undo by design. Status `BLOCKED`.
4. **Present the effect** — branch, current HEAD, target, and each commit that would be removed (SHA + subject) — then ask the human through the host's structured question tool (`hosts.md` → Host capabilities) whether to apply. Ask and wait within this invocation. Do **not** write the `## Gate` block first: the helper refuses a dirty tree, so a STATE.md edit made before the apply would block the apply it is asking about. The DECISIONS entry below is this gate's record.
5. **Apply only on an explicit yes.** Anything else — no, silence, a modified request — applies nothing; a different target means a new preview. On yes: `python3 {devflow_root}/scripts/flow-undo.py apply --repo <apply.repo> --to <apply.to> --expected-head <apply.expected_head>`, the three values copied from the preview's `apply` object.
6. **Refused** (exit 1) → report the reason. If HEAD moved, go back to step 2 and ask again on the new preview; never retry with a SHA you derived.
7. **Applied** → report `removed`, the new HEAD, and `backup_ref`.

## Record
When `.planning/` exists, append a `.planning/DECISIONS.md` entry per `autonomy.md` and `{devflow_root}/templates/decisions.md` — gate `undo-apply`: what was asked (branch, target, commits to remove), the human's actual answer (including a refusal), the git identity (`git config user.name` / `user.email`), and the HEAD SHA at the time. Commit it on the branch after the apply, so the record lands on top of the undone state; secret-scan the staged diff first (`conventions.md`). Do not rewrite STATE — `/flow-status` reconciles it.

## Restore
The backup ref keeps the undone commits reachable. To get them back, clean tree, on the same branch: `git reset --hard <backup_ref>` — or, without moving the branch, `git branch <name> <backup_ref>`. Restoring is itself destructive git, so it is the human's command to run, not this skill's. Backup refs live under `refs/devflow/undo/` and are never pushed; delete one with `git update-ref -d <backup_ref>` once it is no longer needed.

## Status line
Per `autonomy.md`: applied → `FLOW: CONTINUE | undid N commits on <branch>, backup <backup_ref> | next: /flow-status`; declined → `FLOW: CONTINUE | undo declined, nothing changed | next: /flow-status`; blocked or refused → `FLOW: BLOCKED | undo blocked: <codes> | next: /flow-status`.
