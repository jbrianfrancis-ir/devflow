---
name: flow-pr
description: Push the current feature branch to origin and open a pull request against upstream (or the base branch) from verified work. Use when a phase or body of work is ready to integrate.
---

# flow-pr

Context rules: read `.planning/STATE.md` and `.planning/config.json` (`git` block) first; also read `${CLAUDE_PLUGIN_ROOT}/references/conventions.md` (git workflow). Opening a PR is outward-facing — see the human gate below.

**Pre-flight**: on the feature branch (`git.branch`), not the base branch; working tree clean; the work is verified (a phase VERIFICATION passed, hardening done, or the user confirms). Not on a feature branch → offer to create `flow/<slug>` off `git.base` and move the commits to it. No `origin` remote → block.

1. **Secret scan**: run the conventions.md secret scan over `git diff <base>...HEAD` — a hit means do not push: `FLOW: GATE | secret-scan hit | next: remove/rotate, rerun /flow-pr`.
2. **Push**: `git push -u origin <branch>`.
3. **Build the PR** body from the verified work: phase SUMMARY + VERIFICATION frontmatter (what shipped, REQ-IDs covered, deviations, human checks) since the last PR/base. Concise title. Base = the base branch of `upstream` if set, else of `origin`; head = `<branch>` (`<origin-owner>:<branch>` for a cross-fork PR).
4. **Human gate**: show title, base ← head, and the body; get explicit confirmation before creating — even in `--auto`. (Outward-facing to the canonical repo.)
5. **Open**: `gh pr create --repo <upstream-or-origin> --base <base> --head <head> --title ... --body ...`, or the GitHub MCP (`create_pull_request`). If a PR from this branch already exists, the push updated it — just report its URL. No `upstream` → PR within `origin` (base = base branch).
6. **Record**: write the PR URL into STATE.md (Session/Position); note it in `.planning/deploy/PIPELINE.md` if present; prepend a `.planning/JOURNAL.md` line with the PR URL (format `${CLAUDE_PLUGIN_ROOT}/templates/journal.md`; create if missing).

End with the status line per `${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`: `FLOW: GATE | PR #N opened, awaiting review/merge | next: after merge, /flow-uat (or /flow-harden if not yet hardened)`.
