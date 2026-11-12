# Installation

The install commands for both hosts are in the repo [`README.md`](../README.md). This page covers what happens after.

## Codex

Start a new Codex thread after installation and invoke skills with `$flow-new`,
`$flow-plan`, `$flow-execute`, and the other `$flow-*` names. Codex cloud is not
part of the initial support contract.

## GitHub Copilot

Copilot CLI and VS Code agent mode; the Copilot cloud agent on github.com is not supported at
this time. Install: [README](../README.md#github-copilot-cli-and-vs-code). First run, gates, roles
and gaps: [getting-started-copilot.md](getting-started-copilot.md). Host behaviour:
[`hosts.md`](../plugins/devflow/references/hosts.md) → GitHub Copilot.

VS Code without agent plugins: `python3 <devflow>/scripts/flow-copilot.py render --repo .`
(`<devflow>` is a checkout's `plugins/devflow` or an installed copy) vendors the skills, `flow-*`
custom agents, references, templates and scripts into `.github/`, with no hooks, plus a workflow
that runs `flow-copilot.py check` on PRs touching `.github/`. Re-render after each DevFlow update.

## Test the working tree for one session

The installed plugin is the published build, not your checkout. To run skills from a DevFlow
working tree without changing any installed plugin or marketplace, load it for one session.

- **Claude Code**: from the fixture directory, run
  `claude --plugin-dir <path-to-checkout>/plugins/devflow`. Skills are namespaced by the plugin
  name, so run `/devflow:flow-status`, not `/flow-status`. A headless check works too:
  `claude --plugin-dir <path-to-checkout>/plugins/devflow -p "/devflow:flow-status" --effort low`.
  In an empty directory it reports that there is no `.planning/` and ends with a `FLOW: BLOCKED`
  line whose `next:` is `/flow-new`.
- **Codex**: unverified. No session-only load path has been checked against Codex docs or a live
  run, so none is documented here.

DevFlow's own PRs record the result as the host smoke receipt in
[`pull_request_template.md`](../.github/pull_request_template.md).

## Bootstrapping

Claude projects remain **self-bootstrapping**: `/flow-new` and `/flow-migrate` merge a `.claude/settings.json` declaration so fresh Claude sessions install DevFlow. Codex v1 installs from the DevFlow marketplace at user scope and does not mutate user configuration from a project skill. Both also write `CLAUDE.md` and `AGENTS.md` pointer files at the repo root — marker-merged, never overwriting your content — so a session that never runs a `flow-*` skill still finds `.planning/`. They point at the artifacts rather than restating them; a copy of your constraints in an auto-loaded file goes stale and does more damage than no file at all. The declaration's exact JSON and the pointer-file merge rules are specified in [`conventions.md`](../plugins/devflow/references/conventions.md).

## Context repos

BlitzOS-style context repos: DevFlow projects slot into [BlitzOS](https://github.com/blitzdotdev/blitzos)-style context repos — thin private repos that let cloud agents boot already knowing your repos and their state. Detection, company-brain rendering, `FLOW:` status parsing, session-record mapping, and the bootstrap contract are specified in [`blitzos.md`](blitzos.md).
