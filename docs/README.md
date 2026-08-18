# Docs

Reference pages for DevFlow that go beyond what the [repo README](../README.md) covers. Every page below is linked from here.

## Getting started

- [installation.md](installation.md) — what happens after the README's install commands: Codex invocation, self-bootstrapping, and context-repo integration.
- [providers.md](providers.md) — which provider runs a role, and which model tier it gets.
- [execution-model.md](execution-model.md) — how a phase actually executes: the plan dependency graph, the smoke gate, state files, and map staleness.

## Working the loop

- [requirements-clarity.md](requirements-clarity.md) — how DevFlow marks an unsettled requirement instead of guessing, and audits it later.
- [review.md](review.md) — how plans and diffs get reviewed, including the adversarial cross-provider pass and its ledger.
- [parallel-work.md](parallel-work.md) — seeing every project's status at once, and running phases side by side in worktrees.
- [autonomy.md](autonomy.md) — the FLOW status line, loop rails, and the gates that never auto-proceed.
- [provenance.md](provenance.md) — who made a change and who approved it: commit trailers and the decision log.

## Background

- [acknowledgements.md](acknowledgements.md) — which external projects DevFlow's concepts are derived from.

## Integration contracts

- [status-contract.md](status-contract.md) — the stable file and status-line interface an outside driver reads to observe and drive a session.
- [blitzos.md](blitzos.md) — the design contract for a BlitzOS fork that manages DevFlow projects across repos.
