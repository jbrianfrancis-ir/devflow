---
name: flow-second-opinion
description: Read-only second-opinion review of one pull request by Grok Build and Codex CLI (trial through 2026-10-30) - scope-guarded to allowlisted non-fork, non-InformativeResearch repos, throwaway checkout, each tool in its read-only sandbox, local report plus a trial-log row; posts ONE combined PR comment only with --post. Args - PR URL, optional --tools codex,grok, --post. Explicit-only.
disable-model-invocation: true
---

# flow-second-opinion

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

Context rules: no `.planning/` is needed. Keep output terse. Background and trial rules: `docs/second-opinion.md` in the DevFlow repo.

**Explicit-only, advisory, read-only.** A human invokes this by name. The two tools are second-opinion **reviewers**, never mutators: they do not commit, push, edit a PR, approve, or request changes, and neither do you on their behalf. Their findings are input for the human and for `/flow-pr`'s own review, not verdicts.

**The helper is the only authority.** Every effect goes through `python3 {devflow_root}/scripts/flow-second-opinion.py`. Never run `grok` or `codex` yourself, never add `--always-approve`, `--yolo`, `--dangerously-bypass-approvals-and-sandbox` or a write sandbox, and never post with `gh` directly.

## One invocation

1. **Argument.** A pull request URL (or `owner/repo#n`). None → ask which PR; never guess.
2. **Scope.** `python3 {devflow_root}/scripts/flow-second-opinion.py scope <pr>`. Exit 1 → report every reason verbatim and stop (`BLOCKED`). Do not work around a refusal: the allowlist file and the fork rules are the human's, and an InformativeResearch repository or fork is never in scope.
3. **Review locally.** `python3 {devflow_root}/scripts/flow-second-opinion.py review <pr> [--tools codex,grok]`. It runs for minutes (each tool is capped by `--timeout`, default 900s); run it in the background if the host would time out. It prints one JSON summary: per tool `status` (`ok`, `skipped` with the login step to run, `timeout`, `error`, `read-only violation`), runtime, findings count, usage/cost, and `tree_clean`.
4. **Present** the report file it names: the per-tool table, then the findings worst first. A skipped tool's `note` is the exact login command for the human to run; never run a login yourself.
5. **Post only on an explicit yes.** Posting a comment on a PR is outward-facing (`{devflow_root}/references/autonomy.md` → Human gates). Ask; on yes, re-run step 3 with `--post`, which posts ONE combined comment headed "second-opinion review (trial)". Anything else posts nothing. A run with a `read-only violation` never posts, and you do not retry it — report it as the headline.

## Status line
Per `autonomy.md`: reviewed → `FLOW: CONTINUE | second opinion on <repo>#<n>: <codex N, grok M findings> (report <path>) | next: triage the findings`; posted → same, plus `posted`; refused or violation → `FLOW: BLOCKED | second opinion <refused|read-only violation>: <reason> | next: /flow-status`.
