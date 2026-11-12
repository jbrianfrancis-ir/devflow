# DevFlow host and provider contract

DevFlow runs in Claude Code, local Codex clients and GitHub Copilot. The `.planning/` files and
the bundled skills, role contracts, references, and templates are the portable
source of truth.

## Resolve `devflow_root`

At the beginning of every skill, resolve `devflow_root` to the installed plugin
directory containing that skill's `skills/` directory. For a skill at
`<root>/skills/<name>/SKILL.md`, canonicalize `../..`. Never assume a home path
or host-specific plugin-root variable. Replace `{devflow_root}` in every path
before calling a tool.

## Host capabilities

- Use the host's structured question tool when available; otherwise ask the
  same concise question in chat. Never answer a human gate for the user.
- Invoke skills with the host mechanism. Claude exposes `/flow-*`; Codex exposes
  `$flow-*`. Durable state may retain `/flow-*` for compatibility, but render
  the appropriate prefix when telling the user what to run.
- Explicit-only skills (`autonomy.md` → Explicit-only skills) carry
  `disable-model-invocation: true`. Claude honors it for plugin skills: the
  Skill tool refuses them and the user's slash command still runs them. Codex
  equivalent (`agents/openai.yaml` with `policy.allow_implicit_invocation:
  false`): unverified for plugin-installed skills, not added.
- Claude Artifact publishing is an enhancement. Without an Artifact tool, write
  the review page beneath `.planning/reviews/` and return its path.
- `/goal`, `/loop`, and `/clear` are optional Claude conveniences. In Codex,
  repeatedly invoke `$flow-next` for durable one-step advancement.

## GitHub Copilot

Copilot (github.com cloud agent, VS Code agent mode, CLI) loads the plugin or the pack
`scripts/flow-copilot.py` vendors into `.github/`. In the vendored pack `devflow_root` is
`.github` and role contract files end in `.agent.md`.
- Run skills by name: `/flow-*` in the CLI and VS Code; on github.com, name it in the task.
- Roles: VS Code and the CLI run the `flow-<role>` custom agent as a subagent. The cloud agent
  has no subagents: read the role contract fully and follow it inline, holding a read-only
  role to no edits, and say in the result that it was not a fresh context.
- No question tool: ask in chat. The cloud agent cannot ask, so a human gate ends the run with
  the question in the PR; never answer it. Only `native` exists (no `--host copilot` bridge),
  so refuse a peer provider. `model:` tiers and `agents.models` do not apply.
- The pack ships no hooks; never add a Stop or agentStop hook. Re-render it after a DevFlow update.

## Provider selection and dispatch

Delegating skills accept `--provider native|claude|codex`. Resolve command flag,
then `.planning/config.json` `agents.provider`, then `native`. Native means the
current host and must not start a second CLI.

- Claude native: spawn the named `flow-*` plugin agent.
- Codex native: spawn built-in `worker` for write roles or `explorer` for
  read-only roles. Pass the matching `{devflow_root}/agents/flow-*.md` path and
  require the child to read it fully before acting.
- Non-native: use a bounded native wrapper subagent to invoke the bridge:

  ```
  python3 {devflow_root}/scripts/flow-agent.py --host <claude|codex> \
      [--provider native|claude|codex] --role <role> [--effort <level>] \
      --repo <path> --prompt-file <path> [--timeout 1800]
  ```

  `--host` is the CLI you are calling from and is always required. Omit
  `--provider` to let the bridge apply the precedence above itself — it reads
  `agents.provider` from the repo's `.planning/config.json`. The bridge refuses
  to run when the resolution lands on the host, so a native role can never
  start a second CLI. Independent wrappers may run concurrently; the
  orchestrator waits for and counts every result.

An executor spawned by `/flow-execute` runs in a task worktree, so its `--repo`
is that worktree, never the main checkout. The codex peer's `--cd`/`--sandbox`
then confines its writes to the worktree; the claude peer has no such flag, so
there the landing helper's leak check is what enforces it.

Read-only roles: adjudicator, mapper, researcher, plan-checker, plan-reviewer, reviewer, triager, verifier. Write
roles: planner, executor, migrator, consultant, prober.

The bridge applies two confinements itself; the orchestrator passes nothing for them. On a
third-party clone (no `origin`/`upstream` owner in `flow-agent.py`'s `TRUSTED_REMOTE_OWNERS`)
the claude peer runs with `--setting-sources user`, so the clone's own settings and hooks never
load. `prober` is rooted at a scratch directory outside the repo (`SCRATCH_ROLES`): the codex
peer sandboxes it there; under the claude peer only its prompt contract holds it there.

**Write roles emit to `.tmp` and atomically rename — for the artifacts a reader polls.** Every
write role above that produces a `.planning/` file writes `<name>.tmp` and renames it into
place, so a reader sees either the previous complete file or the new one, never a mixture.
`prober` is the exception: its files are throwaway scratch outside the repo that no reader
ever polls, so this rule does not bind it. This applies per file: a multi-file write is
still a sequence of atomic single-file appearances, not one atomic transaction across the whole
set — which is why the next rule is also needed and this one does not subsume it.

**Never diff or audit a phase directory while its write role is running.** Wait for completion.
*A quiet directory is not a finished one*: polling for stability cannot tell a finished write
from a pause between two files, and audits of a mid-write snapshot have filed defects already fixed.

Always tell a spawned role that **commits** — today only the executor — its
**resolved provider and model**: it needs both to write the commit attribution
trailers in `conventions.md`, and it cannot observe them for itself. Pass the
concrete provider (`claude`/`codex`), never `native`. The other write roles
(planner, migrator, consultant) produce files the orchestrator reviews and
commits, so sending them an attribution they will never use is payload for
nothing.

## Model tiers

Each `flow-*` agent declares its own `model:`. Judgment roles — planner,
plan-checker, plan-reviewer, verifier, reviewer, triager, adjudicator, consultant, migrator — run on the top tier;
bounded roles — mapper, researcher, executor — run a tier down. The executor is
deliberately in the cheap group: a plan is a complete, unambiguous executor
prompt by design (`plan-format.md`), and that is what makes it safe. It is also
the highest-volume role, so it dominates cost.

A project overrides any of them with `agents.models.<role>` in
`.planning/config.json`, using the same values the frontmatter accepts
(`opus`, `sonnet`, `haiku`, `inherit`):

```json
"agents": { "provider": "native", "models": { "executor": "opus" } }
```

When an override exists for a role you are spawning, pass it as the subagent's model — it takes precedence over the agent file. Never silently upgrade a role to a more expensive tier because a task looks hard; that is a planning problem, and quietly spending more is exactly what the declaration exists to prevent. The Haiku lane's one retry below is the only sanctioned upgrade.

**Haiku lane** (Claude native only, and only when `agents.models.executor` is unset; the bridge and Codex have no lane). Spawn `flow-executor` with the Agent tool's `model: "haiku"` when all of these hold, else on its agent file's `sonnet`: the plan is a `/flow-quick` mini-plan or the only plan in its wave; every `files_modified` path ends in `.md`, `.txt`, `.json`, `.yaml`, `.yml` or `.toml` and none contains (any case) `architecture`, `auth`, `secur`, `secret`, `migrat` or `.github/`; and no task has a `<falsify>` or a `checkpoint:*` type. Tell the executor the model you passed, for its trailer. **Escalation**: a haiku executor that returns a CHECKPOINT, no SUMMARY, or a SUMMARY recording a failed `<verify>` is respawned once with `model: "sonnet"` as a continuation with its completed tasks, SHAs and that output, and the run report says `executor haiku→sonnet: <plan> <reason>`. Only then does a checkpoint reach the human or a failure block. The sonnet result is final: never a second retry.

Cross-provider is different: model names are provider-specific, so the peer's
model is never read from config. Pass `--model` to the bridge only when you
know the name is valid for that provider; omitted, the peer CLI picks its own
default.

**Usage report** (opt-in, `"usage_report": true` in `.planning/config.json`): only `/flow-execute`, `/flow-quick` and `/flow-verify` record, per `{devflow_root}/references/usage-report.md`. Off, nothing is recorded.

## Effort

DevFlow ships no effort for any role. A project may set `agents.effort.<role>` in
`.planning/config.json` (role names as in `agents.models`; absent or `"inherit"` passes none).
Cross-provider: the bridge resolves `--effort`, then `agents.effort.<role>`, and checks the value
before starting a peer — the claude peer takes `flow-agent.py`'s `EFFORT_LEVELS`, the codex peer
refuses every effort. Native: not applied; native roles run at the session's effort.

The host remains responsible for graph ordering, disjoint-write checks, fan-in,
checkpoints, secret scans, commits and pushes, and independent verification.

## Cross-provider safety

Selecting a peer provider, directly or in project config, authorizes sending the
bounded prompt and repository-visible files to it. The bridge uses existing CLI
authentication and never handles credentials. It never emits permission-bypass
flags. Missing executables, authentication errors, malformed output, timeouts,
signals, permission denial, and non-zero exits fail closed; never fall back to a
different provider silently.

Continue after a checkpoint with a fresh call containing artifact paths,
completed task/commit IDs, and the user's answer. Files and git history are the
handoff, not hidden provider conversation history.
