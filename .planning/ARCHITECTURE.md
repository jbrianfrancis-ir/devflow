<!-- .planning/ARCHITECTURE.md — cap 3KB. HARD constraints, owned by the human. -->
# Architecture constraints

## Stack
| What | Exactly | Version |
|------|---------|---------|
| Content | Markdown (GitHub-flavored) | — |
| Scripting | Python 3, **stdlib only** | 3.9+ (CI: ubuntu-latest default) |
| Packaging | Claude Code plugin + Codex plugin manifests | per `plugins/devflow/.claude-plugin/plugin.json` |
| CI | GitHub Actions | `actions/checkout@v4` |

This repo is the **DevFlow plugin source**, not an application. There is no
package manifest, no build step, no runtime dependency, and no deployable
artifact. Nothing may introduce one.

## Principles
- **Layout override**: content lives under `plugins/devflow/{agents,references,skills,templates,scripts}/`, repo tooling under `scripts/`, tests under `tests/`, prose under `docs/`. DevFlow's default `src/` layout does **not** apply here; never create `src/`.
- **Docs are pointers, never copies.** A fact belongs in exactly one file. If a doc restates what `references/` or a skill already defines, link to it instead — a duplicate goes stale and a stale copy is worse than none. (This is the repo's own rule from `references/conventions.md`, applied to itself.)
- **No dependencies.** Python stays stdlib-only; CI actions stay pinned to the versions above. A proposed dependency — including a docs generator, a static site builder, or a link-checker that needs `pip install` — is a `checkpoint:decision`, never an improvisation.
- **Every internal link resolves.** A relative link or anchor that 404s is a defect, not a nit. Splitting a document is only complete when every inbound reference to it has been repointed.
- **The plugin manifests are the version source of truth.** `plugins/devflow/.claude-plugin/plugin.json` `version` drives releases and the Codex manifest must match it. Documentation work never touches either.

## Smoke
- **Command**: `python3 scripts/validate-plugin.py && python3 -m unittest discover -s tests -v`
- **Pass looks like**: exit 0 from both; validator prints no error lines; unittest reports `OK` with 0 failures and 0 errors.

<!-- The phase that lands scripts/check-links.py extends this command to
     `... && python3 scripts/check-links.py` in the same change that adds the
     script, and not before — a smoke command naming a file that does not exist
     yet fails every earlier phase for the wrong reason. -->

## Link checking
Internal-link integrity is enforced by `scripts/check-links.py` — **stdlib
only**, no network. It resolves relative links and `#anchor` fragments across
tracked markdown against the filesystem and the target file's headings, and
exits non-zero on a miss. External `https://` URLs are deliberately out of
scope: checking them makes CI depend on third-party uptime.

## Frameworks & libraries
| Library | Version | Use for |
|---------|---------|---------|
| Python `unittest` (stdlib) | 3.x | the test suite in `tests/` |
| Python `json`, `re`, `glob`, `os`, `sys` (stdlib) | 3.x | `scripts/validate-plugin.py` |

No third-party packages. No `requirements.txt`, no `pyproject.toml`.

## Architecture & patterns
- One skill per directory: `plugins/devflow/skills/<name>/SKILL.md` with YAML frontmatter (`name`, `description`).
- One agent per file: `plugins/devflow/agents/flow-<role>.md` with frontmatter declaring `model`.
- Shared prose contracts in `plugins/devflow/references/*.md`; artifact shapes in `plugins/devflow/templates/*.md`.
- Public prose (`README.md`, `docs/*.md`) is written for humans browsing GitHub; it must render correctly on github.com with no build step.
- Relative links only between repo files — never absolute `https://github.com/...` URLs to this repo's own content.

## Infrastructure (Azure / Aspire resources)
**None.** This project has no deployable surface. `/flow-harden`, `/flow-uat`,
and `/flow-release` are not applicable; integration ends at `/flow-pr` +
`/flow-ci` and merge to `main`. `.planning/config.json` records
`deploy.tool: null` accordingly.

## Environment (names only — never values)
| Var / parameter | Source | Used by |
|-----------------|--------|---------|
| `GH_TOKEN` | GitHub Actions `github.token` (CI only) | `.github/workflows/release.yml` |

No local environment variables are required to work on this repo.

**Fail fast — no fallback values.** Applies to the Python scripts: a missing
required input errors with the key named, never a silent default.

## Forbidden
- Any third-party Python package, or any `pip install` step in CI.
- A docs build system (MkDocs, Docusaurus, Sphinx, Jekyll) — `docs/` stays plain markdown read directly on GitHub.
- `src/` at the repo root.
- Restating requirements, versions, or roadmap content inside `CLAUDE.md` / `AGENTS.md` — they are pointers only.
- Editing `plugin.json` / `marketplace.json` version fields as part of documentation work.
