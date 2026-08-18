# Providers and model tiers

## Provider selection

Native workers are used unless a delegating skill receives
`--provider claude|codex`. A project can save the same choice as
`"agents": {"provider": "native|claude|codex"}` in `.planning/config.json`;
the command flag wins. Cross-provider use requires both CLIs installed and
authenticated, authorizes the bounded repository context to be sent to that
provider, and preserves all Flow checkpoints, branch rules, and secret scans.

## Model tiers

Each role declares its own model, so cost is a property of the plugin rather than something you have to remember to ask for. Roles split into two tiers: judgment roles run on the top tier, bounded roles a tier down — including the high-volume **executor**, deliberately in the cheap group because a DevFlow plan is a complete, unambiguous executor prompt by design, which is what makes that safe. The per-role assignment is the reference's to state, not this page's. The executor is deliberately cheap: a DevFlow plan is a complete, unambiguous executor prompt by design, which is what makes that safe. Override per role with `"agents": {"models": {"executor": "opus"}}` in `.planning/config.json`.

Provider dispatch mechanics, the full per-role model table, and cross-provider sandbox rules are specified in [`hosts.md`](../plugins/devflow/references/hosts.md).
