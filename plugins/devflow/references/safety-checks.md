# Safety checks

Guard patterns for code an agent writes or runs, and the checks `/flow-audit --safety` makes for them. Adapted from cover-your-ais' codebase safety audit (`docs/acknowledgements.md`). The helper `scripts/flow-safety-audit.py` finds S1, S2, S4 and S5 by heuristics. S3 needs judgment. Every pattern below shows names and hosts only, never a credential value.

Out of scope: DevFlow does not look for committed keys, tokens or `.env` files, and it adds no secret or `.env` deny rules. `/flow-audit --safety` never reports them. Destructive git commands belong to `destructive-git-guard.py` (`/flow-hooks`, `docs/hooks.md`), not to these checks.

## S1 Test-DB guard
Tests run against a local or container DB: `localhost`, `127.0.0.1`, `::1`, `host.docker.internal`, a docker-compose service name, testcontainers, or in-memory/SQLite. Test setup that can drop, truncate, reset or migrate stops before it touches anything when the host is not local. Planner: a task that writes DB test setup names this guard in its `<action>`. Executor: write it into the shared fixture, once per test project.

```python
LOCAL = {"localhost", "127.0.0.1", "::1", "host.docker.internal", "db"}  # "db": the compose service
host = urlparse(os.environ["TEST_DATABASE_URL"]).hostname
if host not in LOCAL:
    raise SystemExit(f"WARNING: test DB host is {host}, not local; refusing to reset it")
```

The same shape works in C# (`new NpgsqlConnectionStringBuilder(cs).Host`) or TypeScript (`new URL(url).hostname`). Print the host, never the connection string.

## S2 Recursive-delete guards
A recursive delete on a variable target (`rm -rf`, `rmtree`, `rimraf`, `Remove-Item -Recurse`) has three guards:
1. `${VAR:?}` on every variable in the path. If the variable is empty, the script stops instead of deleting the parent.
2. `set -euo pipefail` (at least `-u`) at the top of the shell script.
3. Resolve the target with `realpath` and refuse anything outside the repo root.

```bash
set -euo pipefail
root=$(git rev-parse --show-toplevel)
target=$(realpath -- "${BUILD_DIR:?}")
[[ "$target" == "$root"/* ]] || { echo "refusing to delete $target: outside $root" >&2; exit 1; }
echo "WARNING: deleting $target ($(find "$target" | wc -l) files)"
rm -rf -- "$target"
```

## S3 Prose-only rules
A "never", "do not", "ask before" or "code freeze" rule in `AGENTS.md`, `CLAUDE.md`, `.cursorrules` or `copilot-instructions.md` (under `.github/`) holds only while the model obeys it. Back each one with a control that works without the model: a hook, a `permissions.deny` rule in `.claude/settings.json`, branch protection or a required review, a CI check, or a read-only DB role. Name the safe command next to the rule, for example "run tests with `make test-local`". Skip rules about secrets, keys, credentials and `.env` files entirely. DevFlow does not recommend deny rules for them.

## S4 CI agents on untrusted input
An AI agent step (`anthropics/*`, `claude-code-action`, `openai/codex*`, copilot, aider, cursor, `claude -p`, `codex exec`) on `pull_request_target`, `issue_comment`, `pull_request_review_comment`, `issues`, `discussion*` or `workflow_run` reads text that anyone can write. Such a job gets:
- `permissions:` set to the least it needs (`contents: read`), never `write-all`. With no permissions block, the default token may have write access.
- No `secrets.*` beyond the one the agent step needs, and no write token next to it.
- `pull_request` instead of `pull_request_target` for agents.
- No cache shared with a release job.

Name a secret by its expression (`secrets.X`) and never by its value.

## S5 Hazard warnings
A script that deploys, resets, drops, migrates down, destroys or truncates prints one `WARNING:` line before it acts. The line names the target and what gets destroyed:

```
WARNING: DATABASE_URL host is prod-db.example; this DROPS all tables
```

The source study found that a warning like this in command output reduced agent harm more than repeating the rule in instructions did. Agents read the output of what they run.
