---
name: flow-pr
description: Push the current feature branch to origin and open a pull request against upstream (or the base branch) from verified work. Use when a phase or body of work is ready to integrate.
---

# flow-pr

Context rules: read `.planning/STATE.md` and `.planning/config.json` (`git` block) first; also read `${CLAUDE_PLUGIN_ROOT}/references/conventions.md` (git workflow). Opening a PR is outward-facing — see the human gate below.

**Pre-flight**: on the feature branch (`git.branch`), not the base branch; working tree clean; the work is verified (a phase VERIFICATION passed, hardening done, or the user confirms). Not on a feature branch → offer to create `flow/<slug>` off `git.base` and move the commits to it. No `origin` remote → block.

1. **Secret scan**: run the conventions.md secret scan over `git diff <base>...HEAD` — a hit means do not push: `FLOW: GATE | secret-scan hit | next: remove/rotate, rerun /flow-pr`.
2. **Independent review** (autoreview): the session that wrote the code does not review it — a reviewer sharing the author's context is grading its own homework, exactly as in `/flow-execute` step 4. Pick the lenses the diff actually warrants (`git diff --stat <base>...HEAD`): **correctness** and **conventions** always; **security** on auth/input/network/config changes; **architecture** when ARCHITECTURE.md exists; **tests** when behavior changed or a bug was fixed; **reuse** on new modules; **design** only when DESIGN.md exists and UI changed. Spawn one `flow-reviewer` per lens **in parallel — all in one message** — each with: its lens name, the diff range `<base>...HEAD`, `${CLAUDE_PLUGIN_ROOT}/references/conventions.md`, and ARCHITECTURE.md / DESIGN.md / the phase SUMMARY + VERIFICATION paths when present. Keep only the returned finding blocks.

   **Merge and triage**: dedupe across lenses — same file+line and same claim is one finding, keeping the highest severity (two lenses reaching the same conclusion independently is signal; report it once, note the agreement). Then resolve each, most severe first:
   - `blocking` → fix it, or **refute** it in writing (the specific reason it doesn't apply: an ARCHITECTURE.md pin, an intentional pattern, a false positive). A refuted blocking finding is a **human gate** — never refute one yourself and ship. Blocking findings that are architectural (Rule 4 shaped) are a checkpoint, not a fix.
   - `should-fix` → fix, or refute with a reason and carry it into the PR body's open-items trailer. Your call, recorded either way.
   - `nit` → fix if trivial, otherwise drop silently. Nits never block a PR and never enter the PR body.
   Fixes commit as `fix(review): <what>` (trivial ones may batch into `chore(flow): pre-PR review fixes`); a fixed bug gets a regression test in the same commit (conventions.md). Re-run only the lenses whose findings you changed code for. Max 3 rounds, or stop early when a round returns no new blocking findings. Anything still open — unfixed, unrefuted, or a refuted blocker — goes to the human gate in step 5, never silently shipped.
3. **Push**: `git push -u origin <branch>`.
4. **Build the PR** body as a narrative recap, not a checklist: 2–5 short paragraphs — the problem/goal, the approach and any root cause, what actually changed, and the proof (verification evidence, test results) — sourced from phase SUMMARY + VERIFICATION frontmatter since the last PR/base, keeping REQ-IDs covered, deviations, and open human checks as a short trailer. Concise title. Base = the base branch of `upstream` if set, else of `origin`; head = `<branch>` (`<origin-owner>:<branch>` for a cross-fork PR).

   Then append a **`## Review guide`** section — the reviewer's attention budget is the scarcest thing in this pipeline, and a diff handed over cold burns it. Aim it, in this order, ≤15 lines total:
   - **Read first** — 2–4 files ranked by risk, one clause each on what to check. Rank by blast radius, not diff size: security/auth boundaries, data or migration changes, public API and contract changes, then anything a `flow-reviewer` raised a finding on. Say plainly which parts are mechanical and safe to skim.
   - **Proof strength** — from VERIFICATION.md's truths table, split the `must_haves` into proven **by command or test** (name it) versus proven **by code trace** only. A trace is weaker evidence than a run; a reviewer deserves to know which truths rest on it.
   - **Thin spots** — where verification was weakest: HUMAN verdicts, truths with no automated coverage, `deferred` items from SUMMARY, and any `[REPEAT]` gap. Understate nothing here; this section is the reason the guide is trustworthy.
   - **Deviations and open items** — `[Rule N]` deviations from SUMMARY frontmatter, unresolved `should-fix` findings and their refutations, and any refuted `blocking` finding (flagged as needing the reviewer's agreement).
   Never let this section claim more confidence than VERIFICATION.md supports — if it disagrees with the truths table, the truths table wins.
5. **Human gate**: show title, base ← head, the body, and every review finding still open — unfixed `should-fix` items with their refutations, and any refuted `blocking` finding called out first by name. Get explicit confirmation before creating — even in `--auto`. (Outward-facing to the canonical repo.)
6. **Open**: `gh pr create --repo <upstream-or-origin> --base <base> --head <head> --title ... --body ...`, or the GitHub MCP (`create_pull_request`). If a PR from this branch already exists, the push updated it — just report its URL. No `upstream` → PR within `origin` (base = base branch).
7. **Record**: write the PR URL into STATE.md (Session/Position); note it in `.planning/deploy/PIPELINE.md` if present; prepend a `.planning/JOURNAL.md` line with the PR URL (format `${CLAUDE_PLUGIN_ROOT}/templates/journal.md`; create if missing).

End with the status line per `${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`: `FLOW: CONTINUE | PR #N opened, checks running | next: /flow-ci` — driving the PR to green is autonomous work (`/flow-ci` watches checks and answers bot review threads). `GATE` only when the human gate in step 5 wasn't cleared, a secret-scan hit blocked the push, or a review finding still needs a decision.
