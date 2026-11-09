# Providers and model tiers

## Orchestrator-agnostic
DevFlow runs as skills inside the interactive host rather than replacing it.

## Provider selection

Native workers are used unless a delegating skill receives
`--provider claude|codex`. A project can save the same choice as
`"agents": {"provider": "native|claude|codex"}` in `.planning/config.json`;
the command flag wins. Cross-provider use requires both CLIs installed and
authenticated, authorizes the bounded repository context to be sent to that
provider, and preserves all Flow checkpoints, branch rules, and secret scans.

## Model tiers

Each role declares its own model, so cost is a property of the plugin rather than something you have to remember to ask for. Roles split into two tiers: judgment roles run on the top tier, bounded roles a tier down — including the high-volume **executor**, deliberately in the cheap group because a DevFlow plan is a complete, unambiguous executor prompt by design, which is what makes that safe. The per-role assignment is the reference's to state, not this page's. Override per role with `"agents": {"models": {"executor": "opus"}}` in `.planning/config.json`.

No role has a default effort. A project can set one per role with `"agents": {"effort": {"<role>": "<level>"}}` in `.planning/config.json`; which levels each provider accepts, and why native spawns do not apply it, are under [Effort](#effort) below.

Provider dispatch mechanics, the full per-role model table, and cross-provider sandbox rules are specified in [`hosts.md`](../plugins/devflow/references/hosts.md).

One role, `flow-prober`, is a write role even though its job looks read-only: `/flow-plan` spawns it to test one stated toolchain assumption headed for an `ARCHITECTURE.md` pin, building and running a throwaway project outside the repo. The write access is for that scratch build, not the repo — its contract forbids touching the repo at all. Contract in [`flow-prober.md`](../plugins/devflow/agents/flow-prober.md).

## Bridge confinement

The [`hosts.md`](../plugins/devflow/references/hosts.md) contract keeps only the rule; the reasons are here.

**Third-party clones: the claude peer ignores the repo's settings.** When `--repo`'s `origin` and `upstream` remotes both point outside the GitHub owners we wrote (`flow-agent.py`'s `TRUSTED_REMOTE_OWNERS`), or there is no such remote, the bridge adds `--setting-sources user`. The clone's `.claude/settings.json` and `settings.local.json` then never load headless, so hooks a repo plants do not fire. On Claude Code 2.1.312 that flag also drops the project `CLAUDE.md` and `.claude/skills`; user settings, user hooks and user plugins still load. Trust comes from the remotes, never from a file in the repo. The codex peer is unchanged.

`prober` is a write role whose writes belong **outside** the repo: it needs `workspace-write` to build a throwaway project at all, so the bridge roots it at a scratch directory (`flow-agent.py`'s `SCRATCH_ROLES`) rather than at the checkout — but the two peers enforce that differently. The codex peer sandboxes it there for real (`--sandbox`/`--cd`): the repo is not writable to it at all. The claude CLI has no directory-scoping flag that would confine it the same way without also removing the Bash access a prober needs to build anything, so there the scratch root is only the process's working directory, held by the prompt contract rather than the sandbox. Calling it read-only would be a label asserting something its sandbox does not — the access class and what a role may touch are two different questions, and only the first is what `--sandbox` sets.

## Effort

DevFlow ships no effort for any role: no agent file declares one, and without a
project setting the host's own default applies. A project that wants per-role
effort sets `agents.effort.<role>` in `.planning/config.json`, with the same
role names as `agents.models`. Absent or `"inherit"` passes no effort at all.
Example only, not a recommendation:

```json
"agents": { "effort": { "reviewer": "high", "executor": "inherit" } }
```

- Cross-provider: the bridge resolves `--effort`, then `agents.effort.<role>`,
  then none, and checks the value before starting any peer. The claude peer
  gets `claude --effort <level>` for the levels in `flow-agent.py`'s
  `EFFORT_LEVELS`; any other value fails the dispatch. That check is the only
  guard: the claude CLI itself warns on an unknown level and runs at its
  default. The codex peer refuses every effort ("effort for codex: unverified,
  not supported yet") because Codex types reasoning effort as whatever the
  model advertises, so there is no fixed set to check against. Leave the key
  unset or `inherit` for roles dispatched to codex.
- Native: **not applied**. Claude Code agent definitions accept an `effort`
  field, but DevFlow's agent files are shipped content that cannot carry a
  project's value, and the Agent tool takes no per-call effort. Native roles
  run at the session's effort (`claude --effort <level>` at launch). Codex
  native per-role effort is unverified and likewise not applied.
