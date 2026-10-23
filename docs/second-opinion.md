# Second-opinion review trial

## What this is
A one-week trial, through **2026-10-30**, of two outside coding agents as **second-opinion
pull request reviewers**: Grok Build (the xAI `grok` CLI) and OpenAI Codex CLI. Each one reads a
pull request and lists the bugs, security problems and regressions it finds. The question the
trial answers is simple: does either tool find real problems that the Claude review missed, and
at what cost in false positives, time and money? On 2026-10-30 the trial log becomes a scorecard
and each tool is kept or dropped.

The tools are reviewers only. They never commit, push, edit a pull request, approve, or request
changes. The output is a local report and, only when a human asks, one comment on the PR.

The skill is [`flow-second-opinion`](../plugins/devflow/skills/flow-second-opinion/SKILL.md). The
helper it drives is `{devflow_root}/scripts/flow-second-opinion.py`; its docstring is the
contract for the scope guard and the read-only layers, so this page does not repeat them.

## Scope
Only repositories the human owns and lists by name, and never InformativeResearch code:

- The repo must be in the allowlist file, `$XDG_CONFIG_HOME/devflow/second-opinion-allowlist`
  (default `~/.config/devflow/second-opinion-allowlist`): one `owner/repo` per line, `#`
  comments. A missing or empty file refuses every PR.
- Forks are refused. A fork of a non-InformativeResearch project can be added with `fork-ok`
  after its name, but a fork whose parent or source is InformativeResearch is always refused, as
  is any InformativeResearch-owned repo or `SpecialProjects.*` / `AutomationHub.*` name.
- A PR whose head lives in another repository is refused.
- A check that cannot run (no `gh` access, no metadata) refuses. It is never read as allowed.

`scope <pr>` runs the guard alone and prints why a PR is refused.

## Running it
From any directory, with `gh` signed in:

- `python3 {devflow_root}/scripts/flow-second-opinion.py review <pr-url>` — both tools, local
  report only.
- add `--tools codex` or `--tools grok` to run one tool; `--timeout 900` caps each tool in
  seconds; `--head <sha>` reviews a specific head, such as the reviewed head of a merged PR.
- add `--post` to post ONE combined comment headed "second-opinion review (trial)". Posting is a
  human gate ([autonomy.md](../plugins/devflow/references/autonomy.md)).
- `scorecard` sums the trial log per tool.

A tool that is not signed in is skipped and the report names the login step:
`grok login --device-auth` or `codex login`. The wrapper never handles a key or a credential
file.

## Where output goes
Nothing is written to any repository.

- The throwaway checkout lives under the system temp dir and is removed after the run
  (`--keep-checkout` keeps it). It is refused under `~/dev` and on a Windows drive.
- The report: `$XDG_STATE_HOME/devflow/second-opinion/<repo>-<pr>-<timestamp>.md`
  (default `~/.local/state/devflow/second-opinion/`).
- The trial log: `trial-log.jsonl` in the same folder, one row per tool per run, with the PR,
  head and base, tool version, status, findings count by severity, runtime, token usage, cost
  when the tool reports it, the plan used, and whether the tree stayed unchanged.

## Triage for the scorecard
Each log row has three blank fields for a human to fill in after reading the findings:
`real_issue_claude_missed` (a count), `false_positive` (a count) and `notes`. `scorecard`
reports these per tool, with the number of rows still untriaged.

## Read-only proof
Each run records HEAD, every ref, and `git status --porcelain --untracked-files=all --ignored`
before and after each tool. The report's "Tree after run" column shows the result. A change
marks the run a read-only violation: the run exits 1 and never posts.

One limit to know: Grok's `read-only` sandbox profile still allows writes to temp paths, and the
checkout is under the temp dir. Grok's own permission mode (`dontAsk`, with only read and
read-only git commands allowed), the removed write bits on the checkout, and the
before-and-after check cover that gap.
