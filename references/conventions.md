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

## Secret scan (fail-closed)
Run before **every commit** on the staged diff (`git diff --cached -U0`) and before **every push** on the outgoing diff (`git diff <base>...HEAD -U0`). One canonical check — write this pattern to a temp file (avoids shell-quoting errors) and `grep -inEf <pattern-file>` the diff's added lines:
```
-----BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|eyJhbGciOi[A-Za-z0-9_-]{20,}|(password|passwd|secret|token|api[_-]?key|connection[_-]?string)["' ]*[=:] *["'][^"']{8,}["']|(password|passwd|secret|token|api[_-]?key|connection[_-]?string)["' ]*[=:] *[A-Za-z0-9+/=_-]{16,} *$
```
(Assignment branches require a quoted literal or a long bare token — `os.environ["API_KEY"]`-style accessors and `${VAR}` references don't hit.)
Additionally, any **added** line in `.env*` (except `.env.example`/`.env.template`), `*.pem`, `*.pfx`, `*.key`, or `id_rsa*` is a hit regardless of content. On a hit: report file + line + pattern class only — **never echo the matched value** — and do not commit or push. Executor → `CHECKPOINT` (human-action); orchestrating skill → `FLOW: GATE | secret-scan hit in <file> | next: remove/rotate the credential, then rerun`. Only a human clears a hit (including false positives) — fail closed even in `--auto` mode and under `/goal`//`/loop`.

## Credential modes & push canary
- **Default rail**: the session's platform-provided git credentials (Claude Code's GitHub rail in cloud sessions; local `gh auth`). Sufficient for the whole DevFlow workflow; the set of repos granted to the session is the security boundary.
- **Push canary**: the first `git push -u origin <branch>` (at `/flow-new`) is the only real credential test. If it fails with an auth error → `FLOW: GATE` with fix instructions (grant the repo to the session, or `gh auth login`) — never a retry loop. Network errors (not auth) may retry with backoff.
- **Token mode** (pushing beyond the session's grant, e.g. a context repo): the token arrives as an environment variable only — never echoed, never written to any file, never committed, never placed in git config that gets committed.

## Session journal (`.planning/JOURNAL.md`)
One line per completed state-changing skill run, **newest first** — format in `templates/journal.md`. Cap 2KB (~25 lines): when over, rewrite dropping the oldest lines. Create the file on first write; its absence is always fine (pre-existing projects keep working). Read by `/flow-status` (top line = last activity) and indexable by BlitzOS-style context repos as session entries (see `docs/blitzos.md`).

## Plugin self-bootstrap (cloud-ready projects)
Every DevFlow project carries its own plugin declaration so any session — Claude Code on the web, a fresh container, a teammate's machine — gets DevFlow at session start. `/flow-new` and `/flow-migrate` write `.claude/settings.json` at the repo root with exactly:
```json
{
  "extraKnownMarketplaces": {
    "devflow": { "source": { "source": "github", "repo": "jbrianfrancis-ir/devflow" } }
  },
  "enabledPlugins": { "devflow@devflow": true }
}
```
If `.claude/settings.json` already exists, **merge** these two keys into it — never overwrite other settings, and never remove marketplaces/plugins the project already declares. Context repos (BlitzOS-style) that aggregate DevFlow projects declare the same marketplace block in their own `.claude/settings.json` — contract in `docs/blitzos.md`.
