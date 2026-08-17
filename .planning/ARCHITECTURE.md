<!-- .planning/ARCHITECTURE.md — cap 3KB; this file is ~4.6KB, over deliberately (D-11).
     HARD constraints, owned by the human. -->
# Architecture constraints

## Stack
| What | Exactly | Version |
|------|---------|---------|
| Content | Markdown (GitHub-flavored) | — |
| Scripting | Python 3, **stdlib only** | 3.9+ |
| Packaging | Claude + Codex plugin manifests | per `plugins/devflow/.claude-plugin/plugin.json` |
| CI | GitHub Actions | `actions/checkout@v4` |

This repo is the **DevFlow plugin source**, not an application: no package manifest, no
build step, no runtime dependency, no deployable artifact. Nothing may introduce one.

## Principles
- **Layout override**: content under `plugins/devflow/{agents,references,skills,templates,scripts}/`, repo tooling under `scripts/`, tests under `tests/`, prose under `docs/`. DevFlow's default `src/` layout does **not** apply; never create `src/`.
- **Docs are pointers, never copies.** A fact belongs in exactly one file. If a doc restates what `references/` or a skill defines, link instead — a stale duplicate is worse than none.
- **No dependencies.** Python stays stdlib-only; CI actions stay pinned. A proposed dependency — including a docs generator or a link-checker needing `pip install` — is a `checkpoint:decision`.
- **Every internal reference resolves.** A path that 404s is a defect, not a nit. Splitting a document is complete only when every inbound reference is repointed — including prose mentions, which no checker catches.
- **Manifests are the version source of truth.** `plugins/devflow/.claude-plugin/plugin.json` `version` drives releases; the Codex manifest must match. Documentation work never touches either.

## Smoke
- **Command**: `python3 scripts/validate-plugin.py && python3 -m unittest discover -s tests -v && python3 scripts/check-links.py`
- **Pass looks like**: exit 0 from all three; validator prints no error lines; unittest reports `OK`, 0 failures, 0 errors; checker prints no failure lines.

## Link checking
`scripts/check-links.py` — **stdlib only, no network**. Validates `[text](target)` links and
`#anchor` fragments, backticked repo-relative paths, and `{devflow_root}/…` refs resolved to
`plugins/devflow/…`. Scope: tracked `.md` except `plugins/devflow/templates/**` and `.planning/**`.
Non-repo refs (bare filenames, consuming-project artifacts, external URLs) are skipped **by rule,
never an allowlist file**. External URLs are out of scope: checking them makes CI depend on
third-party uptime.

## Frameworks & libraries
| Library | Version | Use for |
|---------|---------|---------|
| Python `unittest` (stdlib) | 3.x | tests in `tests/` |
| Python `json`/`re`/`glob`/`os`/`sys` (stdlib) | 3.x | `scripts/*.py` |

No third-party packages. No `requirements.txt`, no `pyproject.toml`.

## Architecture & patterns
- One skill per dir: `plugins/devflow/skills/<name>/SKILL.md` with frontmatter (`name`, `description`).
- One agent per file: `plugins/devflow/agents/flow-<role>.md`, frontmatter declares `model`.
- Shared prose contracts in `references/*.md`; artifact shapes in `templates/*.md`.
- Public prose (`README.md`, `docs/*.md`) must render on github.com with no build step.
- Relative links only between repo files — never absolute URLs to this repo's own content.
- `validate-plugin.py` parses role sets out of `flow-agent.py` by regex — keep those literals regex-parseable.

## Infrastructure (Azure / Aspire resources)
**None.** No deployable surface. `/flow-harden`, `/flow-uat`, `/flow-release` are N/A;
integration ends at `/flow-pr` + `/flow-ci` and merge to `main`. `config.json` sets `deploy.tool: null`.

## Environment (names only — never values)
| Var / parameter | Source | Used by |
|-----------------|--------|---------|
| `GH_TOKEN` | Actions `github.token` (CI only) | `.github/workflows/release.yml` |
| `DEVFLOW_SMOKE` | unset in CI; gates one live-CLI test | `tests/test_flow_agent.py` |

No local environment variables are required to work on this repo.

**Fail fast — no fallback values.** A missing required input errors naming the key, never a silent default.

## Forbidden
- Any third-party Python package, or any `pip install` step in CI.
- A docs build system (MkDocs, Docusaurus, Sphinx, Jekyll).
- `src/` at the repo root.
- Restating requirements, versions, or roadmap content in `CLAUDE.md`/`AGENTS.md` — pointers only.
- Editing manifest version fields as part of documentation work.
