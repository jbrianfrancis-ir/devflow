# DevFlow conventions

Base principles applied to every project unless `.planning/ARCHITECTURE.md` overrides them.

## Code layout
Application and library code lives under `src/` off the repo root; **tests live under `tests/`** off the repo root. Keep config, docs, `.planning/`, CI, and tooling at the root. Planner: task `<files>` paths go under `src/` for code and `tests/` for tests. Executor: create code in `src/` and tests in `tests/`; never scatter either at the repo root. (An ecosystem with a firm different idiom may override this in ARCHITECTURE.md; absent that, use `src/` and `tests/`.)

## Dependency versions
Follow `.planning/ARCHITECTURE.md` pins exactly — no `latest`, no silent upgrades — with one carve-out: **Aspire updates within the current major apply automatically** (e.g. 13.6.2 → 13.6.3, 13.6 → 13.7). A **major** Aspire bump (e.g. 13 → 14) requires user approval — raise a `checkpoint:decision`. When you auto-apply an Aspire within-major update, bump the version in ARCHITECTURE.md to match and log it as a deviation. Mechanics in `aspire.md`.

## Git workflow — branch → origin → PR upstream
- **Base branch**: `dev` if it exists (locally or on a remote), else `main`. Resolved once at `/flow-new` and recorded in `.planning/config.json` under `git`.
- **Never commit to the base branch.** All code changes land on a feature branch cut from the base: `flow/<slug>` (project, phase, or task slug).
- **Push to `origin`** (your working remote / fork) as work completes — origin always mirrors the feature branch.
- **Integrate by pull request against `upstream`** (the canonical repo), targeting its base branch. If there is no separate `upstream` remote, open the PR within `origin`, base = the base branch, head = the feature branch.
- **Deploy runs from merged base code**, not feature branches: `/flow-harden` may commit to the feature branch, but `/flow-uat` and `/flow-release` operate after the PR is merged to base.
- Opening a PR to `upstream` is outward-facing — always a human gate (see `autonomy.md`).

## config.json `git` block
```json
"git": { "base": "dev", "origin": "origin", "upstream": "upstream", "branch": "flow/<slug>" }
```
`upstream` is `null` when there is no separate canonical remote.
