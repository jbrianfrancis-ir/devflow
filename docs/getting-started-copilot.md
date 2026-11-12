# Getting Started using DevFlow in GitHub Copilot

For Copilot CLI and VS Code agent mode. The Copilot cloud agent on github.com is not supported at this time. *needs-confirmation* marks what has not been run live.

## Prerequisites and install
- A Copilot plan with CLI or VS Code agent mode, plus `git`, `gh` and Python 3 for the bundled scripts.
- Copilot CLI installed and signed in ([GitHub docs](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli)), or VS Code with `chat.plugins.enabled` (preview).
- Install with the steps in [README → GitHub Copilot](../README.md#github-copilot-cli-and-vs-code). Without agent plugins, vendor the pack instead ([installation.md](installation.md#github-copilot)).

## Verify it loaded
- CLI: `copilot plugin list` shows `devflow`; in a session, `/skills list` shows the `flow-*` skills.
- VS Code: **Chat: Open Customizations** → **Plugins** lists DevFlow as enabled, and `/flow-status` is in the chat `/` menu.

## First run
In the repo you want to work in, run `/flow-status` (with no `.planning/` it points to `/flow-new`), then `/flow-new`. Every skill ends with a `FLOW:` line naming the next command. A plugin skill may be listed with a `devflow:` prefix (*needs-confirmation*).

## Gates and questions
Copilot has no structured question tool, so DevFlow asks in chat and waits. Human gates (UAT sign-off, release, undo) never proceed without your answer. There is no `/goal` or `/loop`: run `/flow-next` once per step.

## Reviewer and other roles
Skills such as `/flow-plan`, `/flow-execute` and `/flow-pr` run the `flow-*` roles (planner, plan-checker, executor, reviewer, verifier) as Copilot custom agents in subagents. If a role's custom agent is not available, the skill runs it inline in the same session and says it was not a fresh context (*needs-confirmation* for which applies to a plugin install). Only the native provider exists: `--provider claude|codex` is refused.

## Known gaps vs Claude Code
- No `/goal`, `/loop` or `/clear`; no Artifact pages (review pages go to `.planning/reviews/`); no `--plugin-dir` one-session load.
- Roles run on the session model: no per-role `model:` tiers, `agents.models` or Haiku lane; the usage report records `unknown`.
- Explicit-only skills use `disable-model-invocation`, documented for VS Code skills; CLI *needs-confirmation*. Parallel executor waves in worktrees: *needs-confirmation*.

## Update or uninstall
- CLI: `copilot plugin update devflow`, `copilot plugin uninstall devflow`.
- VS Code: **Chat: Update Plugins**; to remove, **Plugins** → DevFlow → **Uninstall**.
- Vendored pack: re-run `render` after each update; to remove it, delete the files its manifest (`devflow-copilot.json`) lists.
