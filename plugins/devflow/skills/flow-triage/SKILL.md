---
name: flow-triage
description: Pre-screen open, externally-authored pull requests against ARCHITECTURE.md/REQUIREMENTS.md/conventions.md and produce a merge-readiness summary — flags only the promising ones for human review. Args - optional PR number(s) to screen specific PRs, --all (include every open PR and every verdict tier, not just flagged ones), --export (persist the report under .planning/triage/). Supports --provider native|claude|codex. Prototype: drafts responses, never posts, closes, or merges anything.
---

# flow-triage

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

**Agent provider**: accept `--provider native|claude|codex`. Resolve and dispatch `flow-triager` exactly as `{devflow_root}/references/hosts.md` specifies. A missing or failed peer under an explicit non-native provider is fail-closed; report `FLOW: BLOCKED` with remediation and never fall back silently.

**STRICTLY ADVISORY.** This skill reads pull requests it did not write and produces a report; it never posts a comment, requests changes, closes, or merges anything on GitHub. Every drafted response is transcript/report output for a human to read, edit, and paste themselves — the same shape as `/flow-pr`'s PR body, which is drafted and then gated before `gh pr create` ever runs. Posting a triage verdict or response to a third-party PR is a named human gate (`{devflow_root}/references/autonomy.md`), never an autonomous step, and this skill has no flag that crosses it.

**Prototype**: this screens and drafts. It does not post, auto-close, or integrate with any webhook — if that's what you need next, it isn't here yet.

**Pre-flight**: `gh` authenticated (`gh auth status`) — missing or unauthenticated is `FLOW: BLOCKED`, never a silent skip (`conventions.md` → Fail-closed guards). An `origin` remote configured (`upstream` optional, screened too when set).

1. **Resolve the PR set.**
   - Explicit PR numbers as args (`/flow-triage 123 456`, or `owner/repo#123` when more than one
     remote is configured): screen exactly those, regardless of author or draft state — an explicit
     ask is never filtered or capped. A bare number resolves against `origin`; qualify it with
     `owner/repo#` to mean `upstream`, or any number that could exist in both.
   - No args: for each of `origin` and `upstream` (when configured), `gh pr list --repo {owner}/{repo}
     --state open --limit 1000 --json number,title,author,isDraft,updatedAt` — the explicit
     `--limit 1000` matters: `gh pr list`'s default cap is 30, and sorting a truncated fetch by
     `updatedAt` cannot produce the true most-recently-updated set once a repo has more open PRs
     than that. Then `gh api repos/{owner}/{repo}/pulls/{n}` per candidate for its
     `author_association` (`gh pr list`/`gh pr view --json` don't expose it — confirmed against
     `gh` 2.46.0). Drop drafts. Default filter keeps only external contributions:
     `author_association` not in `OWNER`/`MEMBER`/`COLLABORATOR`. Tag every surviving candidate with
     its `owner/repo` and carry that tag through every later step — `origin` and `upstream` PR
     numbers are independent sequences that can collide, so a bare number is not a safe identifier
     once both are in play; every `gh` call after this point names `--repo` explicitly. Cap the
     merged, repo-tagged set to the 20 most recently updated across both repos — `--all` removes
     the author filter (screens every open PR in both) and, in step 3, prints full detail for every
     verdict tier rather than flagged rows only.
   - Nothing matches → report "nothing to triage" and stop at `FLOW: CONTINUE` (below); no PRs is a clean, real result, not a reason to widen the query on its own.

2. **Screen.** Spawn one fresh-context `flow-triager` per PR (`{devflow_root}/agents/flow-triager.md`), in parallel, batched (e.g. 5 concurrent) to bound cost when the sweep is large. Each gets: its `owner/repo` and PR number, `{devflow_root}/references/conventions.md`, and the paths to `.planning/ARCHITECTURE.md`, `.planning/REQUIREMENTS.md`, `.planning/DECISIONS.md`, `.planning/PROJECT.md`, `CONTRIBUTING.md`, and `.planning/codebase/MAP.md` — whichever of those exist in this repo. Keep only the returned `TRIAGE` blocks. A PR whose diff can't be fetched, or that the triager reports `could-not-screen`, stays in the output — never drop it silently (`conventions.md` → Fail-closed guards).

3. **Assemble the report.**
   - A table, every screened PR, one row each: `Repo | PR # | Title | Author | Verdict | one-line reason`. Never omit a row — a PR that couldn't be screened gets a row saying so.
   - Below the table: the full `TRIAGE` block (summary, concerns, draft_response) for every `merge-candidate` and `needs-human-judgment` row — those are what a human should read closely. `needs-changes` and `reject` rows get their full block too only under `--all`; by default they stay a one-line table row, since triage's whole point is keeping them out of a maintainer's queue while still keeping the record honest that they were seen.
   - Never manufacture a `needs-human-judgment` verdict to look thorough, and never pad `concerns` — a sweep with nothing flagged is a real, reportable result.

4. **Report, or `--export`.** Default: print the report in the transcript; write nothing, commit nothing, journal nothing — this run changed no state the project owns, same reasoning as `/flow-audit`'s default pass. With `--export`: first confirm the local checkout is on a feature branch (`git branch --show-current` is not `main`/`dev`) with a clean tree (`git status --porcelain` empty) — a base-branch checkout or a dirty tree is `FLOW: BLOCKED` before any write, never a silent skip (`references/autonomy.md`'s hard rule: never commit to the base branch). Then fill `{devflow_root}/templates/triage-report.md`, run the conventions.md secret scan over the assembled file before writing it (an outbound-shaped artifact, same rule as `/flow-audit --export`'s evidence pack — a hit blocks the write and reports file/line/pattern class only), then write `.planning/triage/<YYYY-MM-DDTHHMMSSZ>.md` — a full timestamp, not just the date, since a second `--export` on the same day must never silently overwrite the first report. Commit when `commit_docs` (`chore(flow): triage report <timestamp>`, attribution trailer per `conventions.md`) and prepend a `.planning/JOURNAL.md` line — the one mode that writes is the one that journals, exactly as `/flow-audit --export` does.

End with the status line per `{devflow_root}/references/autonomy.md`: nothing to triage, or only `needs-changes`/`reject` verdicts and no `could-not-screen` → `FLOW: CONTINUE | triage: {n} needs-changes, {m} reject, nothing needs your review | next: rerun after new PRs arrive`; anything `merge-candidate`, `needs-human-judgment`, or `could-not-screen` → `FLOW: GATE | triage: {n} merge-candidate, {m} needs-human-judgment, {k} could-not-screen | next: review the flagged PRs above` — a `could-not-screen` PR is unproven either way, fail-closed exactly like a secret-scan hit that couldn't run (`conventions.md` → Fail-closed guards), never folded into the clean-sweep `CONTINUE` case; `gh` unavailable/unauthenticated → `BLOCKED`.
