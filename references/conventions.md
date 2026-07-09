# DevFlow conventions

Base principles applied to every project unless `.planning/ARCHITECTURE.md` overrides them.

## Code layout
All application, library, and test code lives under `src/` off the repo root. Keep config, docs, `.planning/`, CI, and tooling at the root — `src/` is for code. Planner: every task `<files>` path is under `src/`. Executor: create code there; never scatter source at the repo root. (An ecosystem with a firm different idiom may override this in ARCHITECTURE.md; absent that, use `src/`.)

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
