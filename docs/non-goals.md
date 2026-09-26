# Design decisions and non-goals

Rules and rejected features that do not belong to any one skill, recorded so a later proposal
can find the reason instead of re-arguing it.

## Standing rules

- **"Never merge without a PR, anywhere, because it removes checks and documentation."** —
  the maintainer, 2026-09-26. It applies to DevFlow's own repo and to every project DevFlow
  drives. The hard rules that enforce it in a run (feature branch only, opening a PR and merging
  one are human gates) are in [`autonomy.md`](../plugins/devflow/references/autonomy.md).

## Non-goals

Features of [GSD Path](https://github.com/open-gsd/gsd-path) (v1.3.1) that the 2026-09-26
comparison review rejected.

| # | Feature | Why DevFlow will not adopt it | Source |
|---|---------|-------------------------------|--------|
| I1 | `direct` integration mode: ship runs a local `--no-ff` merge into `main`, then pushes `main`, the milestone branch, and the tag with no PR. Older state without the field defaults to it. | It breaks the standing rule above: no PR means no CI run on a PR tip and no human merge GO. | [WORKFLOW.md](https://github.com/open-gsd/gsd-path/blob/v1.3.1/WORKFLOW.md), [ship skill, step 7](https://github.com/open-gsd/gsd-path/blob/v1.3.1/skills/gsd-path-ship/SKILL.md), [opengsd.net/path](https://opengsd.net/path) |
| I2 | Automatic push of the milestone tag after a merge is validated. | Pushing tags is a human gate in [`autonomy.md`](../plugins/devflow/references/autonomy.md). DevFlow's release workflow tags only when a new version lands on `main`, through a PR a human merges. | [WORKFLOW.md](https://github.com/open-gsd/gsd-path/blob/v1.3.1/WORKFLOW.md), [ship skill, step 7](https://github.com/open-gsd/gsd-path/blob/v1.3.1/skills/gsd-path-ship/SKILL.md) |
| I3 | Optional Jev evidence screening, which sends criteria and evidence text to a third-party hosted API. | It adds a vendor and a credential for an advisory result. DevFlow's independent verifier with abstention already covers it. | [jev-review.md](https://github.com/open-gsd/gsd-path/blob/v1.3.1/skills/gsd-path/references/jev-review.md), [PR #130](https://github.com/open-gsd/gsd-path/pull/130) |
| I4 | A background daemon with a menu-bar or tray dashboard and autostart. | DevFlow is files and prompts with no runtime process. `/flow-status --all` covers the board. | [daemon/README.md](https://github.com/open-gsd/gsd-path/blob/v1.3.1/daemon/README.md) |
