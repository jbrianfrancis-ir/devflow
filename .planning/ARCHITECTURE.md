<!-- .planning/ARCHITECTURE.md — cap 3KB; this file is ~7.5KB, over deliberately (D-11).
     HARD constraints, owned by the human. The `## Link checking` section carries most of the
     excess: it is the contract for this repo's only real guard, and three review rounds showed
     that every clause it was missing was a place the guard could go wrong while reporting green.
     A constraint document that omits the rules is not shorter, it is untrue. -->
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
`scripts/check-links.py` — **stdlib only, no network, no allowlist file**. It is the standing CI gate
(`lint.yml` → `Check internal links`) and the third step of `## Smoke`.

**Scope.** Tracked `.md`, enumerated with `git ls-files -z` (NUL-split: plain `ls-files` C-quotes odd
filenames, which silently drops them from the scan), except `plugins/devflow/templates/**` and
`.planning/**` — both describe a *consuming* project, not this repo.

**Reference kinds.** `[text](target)` links and `#anchor` fragments; backticked repo-relative paths
(a token containing `/` and ending `.md`/`.py`/`.json`/`.yml`); `{devflow_root}/…` rewritten to
`plugins/devflow/…`.

**Resolution differs by kind, deliberately.** A markdown link resolves against the **referring file's
own directory only** — github.com's rule; any other base green-lights links that 404 for a reader.
Backticked and `{devflow_root}` tokens are base-ambiguous prose and keep the multi-base walk (repo
root, the referring file's directory, and `plugins/devflow/` for files under it). A `{devflow_root}/…`
token is root-anchored whichever syntax carries it. Directories are valid targets, not missing ones.

**Containment — two independent guards, neither subsuming the other.** A reference whose normalized
path walks above the root is rejected *before* any filesystem access, so a verdict can never depend on
what the checkout directory happens to be named; and a resolved candidate whose `realpath` escapes the
root is rejected, closing symlink escapes. A reference GitHub cannot follow is truthfully unresolved.

**Skip rules R1–R5**, by rule and never by allowlist: R1 whitespace (a command, not a path); R2
glob/family punctuation `[*<>{},|]`; R3 an `NN`/`NNN`/`MM`/`YYYY` placeholder segment; R4 a
`.planning/` or `~/` prefix; R5 a first segment naming nothing under any resolution base. **R5 does not
apply to markdown links** — a link's base is unambiguous, so an unmatched first segment means broken,
not "not a reference"; R1–R4 still apply to both. A link target carrying any URI scheme, or a `//host`
or `www.` prefix, is external and never reaches the resolver.

**Masking.** Fenced code blocks are skipped. Genuine YAML frontmatter is skipped — and a leading `---`
counts as frontmatter *only* when a closing `---` appears later, because otherwise it is an ordinary
CommonMark thematic break and the document must still be checked in full. The fence scanner does not
look at frontmatter lines, since a YAML literal block may legitimately contain a fence opener. An
**unterminated code fence is a failure**, not a silent mask: a file masked to EOF is a file that quietly
stopped being checked.

**Coverage is reported, not assumed.** Output is `N failures, M references checked`, and a test asserts
a floor of 140 against this repo (currently 162). `0 failures` from a checker that examined nothing is
precisely the failure this guard exists to prevent, so a collapse turns CI red instead of printing a
smaller number.

**Anchors** follow github-slugger: lowercase, strip punctuation, then replace each space
**individually** — a per-character replacement, not a whitespace-run collapse, or every heading with
punctuation between spaces yields a slug one hyphen short of its real anchor. **Deliberately abstained
and unproven (D-12):** duplicate headings (`-1` suffixes), headings holding inline code or links, and
setext headings — this repo contains none of those cases, so nothing grades them.

External `http(s)://` URLs are out of scope: checking them makes CI depend on third-party uptime.

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
