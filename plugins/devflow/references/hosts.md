# DevFlow host and provider contract

DevFlow runs in Claude Code and local Codex clients. The `.planning/` files and
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
- Claude Artifact publishing is an enhancement. Without an Artifact tool, write
  the review page beneath `.planning/reviews/` and return its path.
- `/goal`, `/loop`, and `/clear` are optional Claude conveniences. In Codex,
  repeatedly invoke `$flow-next` for durable one-step advancement.

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
      [--provider native|claude|codex] --role <role> --repo <path> \
      --prompt-file <path> [--timeout 1800]
  ```

  `--host` is the CLI you are calling from and is always required. Omit
  `--provider` to let the bridge apply the precedence above itself — it reads
  `agents.provider` from the repo's `.planning/config.json`. The bridge refuses
  to run when the resolution lands on the host, so a native role can never
  start a second CLI. Independent wrappers may run concurrently; the
  orchestrator waits for and counts every result.

Read-only roles: mapper, researcher, plan-checker, plan-reviewer, reviewer, verifier. Write
roles: planner, executor, migrator, consultant.

Always tell a spawned write role its **resolved provider and model** — it needs
both to write the commit attribution trailers in `conventions.md`, and it cannot
observe them for itself. Pass the concrete provider (`claude`/`codex`), never
`native`.

## Model tiers

Each `flow-*` agent declares its own `model:`. Judgment roles — planner,
plan-checker, plan-reviewer, verifier, reviewer, consultant, migrator — run on the top tier;
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

When an override exists for a role you are spawning, pass it as the subagent's
model — it takes precedence over the agent file. Never silently upgrade a role
to a more expensive tier because a task looks hard; that is a planning problem,
and quietly spending more is exactly what the declaration exists to prevent.

Cross-provider is different: model names are provider-specific, so the peer's
model is never read from config. Pass `--model` to the bridge only when you
know the name is valid for that provider; omitted, the peer CLI picks its own
default.

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
