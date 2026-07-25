---
name: flow-pr
description: Push the current feature branch to origin and open a pull request against upstream (or the base branch) from verified work. Use when a phase or body of work is ready to integrate.
---

# flow-pr

Context rules: read `.planning/STATE.md` and `.planning/config.json` (`git` block) first; also read `${CLAUDE_PLUGIN_ROOT}/references/conventions.md` (git workflow). Opening a PR is outward-facing — see the human gate below.

**Pre-flight**: on the feature branch (`git.branch`), not the base branch; working tree clean; the work is verified (a phase VERIFICATION passed, hardening done, or the user confirms). Not on a feature branch → offer to create `flow/<slug>` off `git.base` and move the commits to it. No `origin` remote → block.

1. **Secret scan**: run the conventions.md secret scan over `git diff <base>...HEAD` — a hit means do not push: `FLOW: GATE | secret-scan hit | next: remove/rotate, rerun /flow-pr`.
2. **Self-review** (autoreview — review the outgoing diff until no actionable findings remain): read `git diff <base>...HEAD` hunk by hunk (hunks, not whole files) hunting leftover debug output, dead paths the change superseded (conventions.md Dead code), TODO/commented-out code, doc drift, and convention violations. Trivial findings → fix and commit `chore(flow): pre-PR review fixes`, re-scan, re-review. Substantive findings → route through `/flow-quick` first. Max 3 rounds; anything still open gets listed at the human gate below, never silently shipped.
3. **Push**: `git push -u origin <branch>`.
4. **Build the PR** body as a narrative recap, not a checklist: 2–5 short paragraphs — the problem/goal, the approach and any root cause, what actually changed, and the proof (verification evidence, test results) — sourced from phase SUMMARY + VERIFICATION frontmatter since the last PR/base, keeping REQ-IDs covered, deviations, and open human checks as a short trailer. Concise title. Base = the base branch of `upstream` if set, else of `origin`; head = `<branch>` (`<origin-owner>:<branch>` for a cross-fork PR).
5. **Human gate**: show title, base ← head, the body, and any self-review findings still open; get explicit confirmation before creating — even in `--auto`. (Outward-facing to the canonical repo.)
6. **Open**: `gh pr create --repo <upstream-or-origin> --base <base> --head <head> --title ... --body ...`, or the GitHub MCP (`create_pull_request`). If a PR from this branch already exists, the push updated it — just report its URL. No `upstream` → PR within `origin` (base = base branch).
7. **Record**: write the PR URL into STATE.md (Session/Position); note it in `.planning/deploy/PIPELINE.md` if present; prepend a `.planning/JOURNAL.md` line with the PR URL (format `${CLAUDE_PLUGIN_ROOT}/templates/journal.md`; create if missing).

End with the status line per `${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`: `FLOW: GATE | PR #N opened, awaiting review/merge | next: after merge, /flow-uat (or /flow-harden if not yet hardened)`.
