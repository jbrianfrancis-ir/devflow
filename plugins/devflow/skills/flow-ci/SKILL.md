---
name: flow-ci
description: Drive an open pull request to green - watch checks, fix failures, triage and answer bot review comments, resolve threads. Args - optional PR number, --auto. Use after /flow-pr, or any time a PR is red or has unread review comments.
---

# flow-ci

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

Context rules: read `.planning/STATE.md` and `.planning/config.json` (`git` block) first, plus `{devflow_root}/references/conventions.md` (git workflow, secret scan). Keep output terse — this skill runs repeatedly under `/loop`.

Babysitting CI is not a human decision, so this skill does it. What stays human: merging, replying to **human** reviewers, force-pushing, anything destructive. Never auto-merge, ever — reaching green is the deliverable.

**Pre-flight**: `gh` authenticated (`gh auth status`); a PR exists for the current branch (`gh pr view --json number,url,state,isDraft,mergeStateStatus`) or the number was passed — none → point to `/flow-pr`. This read is live every pass, never from STATE (`autonomy.md` → External state is a cache, never evidence). PR closed/merged → report and route to `/flow-uat`. On the feature branch, working tree clean.

**One invocation = one bounded pass.** Poll while checks are `pending` (recheck every ~60s, readiness-driven — never a fixed sleep as a substitute for a real signal), up to ~10 minutes; if still pending when the budget is spent, stop with `CONTINUE` so `/loop` or `/goal` picks it up rather than burning a session on a queue.

1. **Read state**: `gh pr checks <n> --json name,state,bucket,link` and the review threads (`gh api repos/{owner}/{repo}/pulls/<n>/comments` plus `gh pr view <n> --json reviews,comments`). Classify every check: pass / fail / pending / skipped, and required vs optional (optional failures are reported, never block the loop).

2. **Fix failing checks**, one check at a time, most-blocking first. Pull the actual failure (`gh run view <run-id> --log-failed`, or the check's annotations) — never guess from the check name. Then classify the cause before touching code:
   - **Caused by this branch** → fix it. A logic bug fixed here gets a regression test in the same commit (conventions.md rules apply exactly as in execution: `src/`/`tests/`, dead-code deletion, ARCHITECTURE.md pins). Commit `fix(ci): <check> — <cause>`.
   - **Pre-existing on the base branch** (verify: does the same check fail on base?) → do not fix it here. Record it in the PR thread and in SUMMARY `deferred`; it is not this PR's job.
   - **Flaky / infra** (timeout, runner death, network) → re-run once (`gh run rerun --failed`). A second failure is not flake — treat it as real.
   - **Needs a decision or a secret you don't have** (new CI credential, an intentional API break, a policy check) → stop, `GATE` with what's needed.
   Max 3 fix attempts per check; then `GATE` naming the check, the cause, and what you tried. Never disable, skip, or `continue-on-error` a check to get green — that is weakening a truth (`plan-format.md`), and it needs a human.

3. **Triage review comments** — bots and humans are handled differently:
   - **Bot / automated reviewers** (CodeRabbit, Copilot, Sonar, Dependabot, linters): for each unresolved thread decide **fix**, **refute**, or **defer**. Fix → change the code, commit `fix(review): <what>`, reply naming the commit, resolve the thread. Refute → reply with the specific reason it does not apply here (an ARCHITECTURE.md pin, an intentional pattern, a false positive) and resolve; a bot finding you disagree with is answered, not silently closed. Defer → reply with why, log it in `.planning/TODOS.md`, leave the thread open.
   - **Human reviewers**: never auto-reply, never resolve their threads, never mark their requested changes done. Summarize what they asked for; obvious mechanical asks may be *implemented* and pushed, but the reply and the resolve are theirs. Stop with `GATE`.
   A finding that is blocking and architectural (Rule 4 in `flow-executor.md` terms) is a `GATE`, not a fix — the same escalation bar as execution.

4. **Push**: secret-scan the outgoing diff per conventions.md before every push — a hit means no push, `GATE`, never echo the value. Then `git push origin <branch>` (plain push only; force-push is a human gate). Pushing restarts checks — that ends the pass: report `CONTINUE`.

5. **Close the pass**: update STATE.md (Position: PR #N status; Blockers: anything gated). Prepend a `.planning/JOURNAL.md` line (format `{devflow_root}/templates/journal.md`) only when the pass changed something — pushed a fix, answered threads, reached green. A pass that only observed pending checks writes nothing (the journal is a history of changes, not of polls). Print: check summary (passed/failed/pending), what you fixed, threads answered, what remains.

**Loop etiquette** (`{devflow_root}/references/autonomy.md`): `/loop /flow-ci` is the intended driver.
- checks pending, or fixes pushed and checks restarted → `FLOW: CONTINUE | PR #N: X/Y checks green, awaiting rerun | next: /flow-ci`
- all required checks green, no unresolved bot threads, no human review outstanding → `FLOW: GATE | PR #N green — awaiting human review/merge | next: after merge, /flow-uat`
- human reviewer comments, an unfixable check, a secret-scan hit, or a decision needed → `FLOW: GATE | <what's needed> | next: <command>`
- PR merged already → `FLOW: CONTINUE | PR #N merged | next: /flow-uat`
- `gh` unauthenticated or the PR vanished → `FLOW: BLOCKED`.
