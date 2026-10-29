---
name: flow-audit
description: Read-only cross-artifact consistency check across REQUIREMENTS, ROADMAP, plans, SUMMARYs, VERIFICATION and STATE - coverage both directions, drift, unmeasurable criteria, open clarifications, principle conflicts. Use before executing a phase, before /flow-harden, or when the planning docs feel out of sync. --export assembles an agent-activity evidence pack (who had access, what changed, who approved) for a vendor or compliance review. --docs checks README/docs claims (paths, scripts, package scripts, make targets, env names) against the tree - use before a docs-only PR. --drift checks what the plan, STATE, decisions and CLAUDE.md say against the code and git history - use when a cold session is about to trust the docs.
---

# flow-audit

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

Context rules: read `.planning/STATE.md` first. Everything here is small and capped — read REQUIREMENTS.md, ROADMAP.md, ARCHITECTURE.md and STATE.md whole, and phase artifacts (`*-PLAN.md`, `*-SUMMARY.md`, `VERIFICATION.md`) **frontmatter only**. Never read source; this audits the documents against each other, not the code (`/flow-verify` proves code, `/flow-harden` audits production-readiness). `--docs` and `--drift` are the modes that read the tree, and only to check what the docs claim about it.

**STRICTLY READ-ONLY.** Change nothing — not a status, not a typo, not a marker. DevFlow spreads project knowledge across artifacts on purpose, and an auditor that edits while it reads destroys the evidence of what disagreed with what. Findings end in a report and a recommended route; the human decides.

**Pre-flight**: `.planning/` with REQUIREMENTS.md and ROADMAP.md. Missing → point to `/flow-new`. Scope defaults to the whole project; `N` limits it to phase N's artifacts plus the project-level files they reference. (`--export` needs only `.planning/` and a git checkout — it reports on what exists rather than checking it. `--docs` needs only a git checkout. `--drift` needs `.planning/` and a git checkout.)

## Passes
Run all of them; report nothing you cannot point at with a file and a line or row.

1. **Coverage, both directions.** Every REQ-ID in exactly one ROADMAP phase; every phase's REQ-IDs exist in REQUIREMENTS.md; every plan's `requirements` entry names a real REQ/SC; every REQ in a planned phase appears in some plan. The reverse direction is the one nothing else checks — **a plan tracing to no requirement is work nobody asked for**, and it is as much a finding as a requirement nothing implements.
2. **Success criteria reachability.** Every `SC-NN` that needs building to reach (a latency budget, a scale target) is named on a phase. An SC no phase carries and no acceptance case covers will not happen; say so.
3. **Status drift.** STATE Position vs ROADMAP row statuses vs what is actually on disk — SUMMARYs present, VERIFICATION status. Disk wins: a phase whose ROADMAP row says verified with no VERIFICATION.md, or `status: gaps` while STATE says verified, is drift. Report which artifact disagrees with disk, never "one of these is wrong".
4. **Open clarifications and abstentions.** Every unresolved `[NEEDS CLARIFICATION: …]` marker, which phase's requirements it sits on, and whether that phase is already planned or executed. A marker still open on an *executed* phase is a decision that got made by default — the highest-value finding this skill produces. List `unverified` backstop truths from VERIFICATION frontmatter alongside them.
5. **Ambiguity.** Requirements and success criteria whose acceptance rests on an unmeasurable adjective — fast, scalable, secure, robust, intuitive, seamless, modern — with no number, threshold, or observable check. Also unresolved placeholders (`TODO`, `TBD`, `???`, `{…}` left from a template).
6. **Principle conflicts.** Anything in a plan or a requirement that contradicts ARCHITECTURE.md's `## Principles`, its pins, or its Forbidden list. Always the highest severity below — the project already made these decisions.
7. **Inconsistency.** The same fact stated differently in two places: a requirement worded one way in REQUIREMENTS.md and another in a plan's `must_haves`, a phase goal that drifted between ROADMAP and its plans, one concept under two names, two requirements that contradict each other.

## Severity
- **CRITICAL** — violates a principle, pin, or Forbidden item; a requirement with zero coverage; a marker still open on executed work. Resolve before executing further.
- **HIGH** — conflicting or duplicated requirements, an unmeasurable acceptance criterion, an SC nothing will deliver, status drift that would mislead a cold session.
- **MEDIUM** — terminology drift, an underspecified edge case, a plan tracing to nothing.
- **LOW** — wording, minor redundancy. Report at most a handful; never pad.

Cap the report at ~25 findings; if more, report the worst by severity and say how many were dropped rather than implying the list is complete.

## Report
One table — `ID | severity | pass | where (file:line/row) | finding | fix` — worst first, then two or three lines of what to do next, routed to the right command: markers and conflicting requirements → `/flow-plan N` (or answer them in REQUIREMENTS.md); missing coverage → `/flow-phase` or a plan; status drift → `/flow-status` (it reconstructs Position from disk); code-level doubt → `/flow-verify N`. **Offer** to apply the mechanical fixes and wait for an explicit yes — never apply them in this run, and never fold a fix into the report as though it were done.

Clean is a real result: say "no findings" plainly rather than manufacturing LOWs to look thorough.

Write nothing to `.planning/` — not even a JOURNAL line (this run changed nothing, and the journal records changes). The report lives in the transcript.

## --docs (doc-vs-code claims)

`--docs [paths…]` is a **separate mode**: it does not run the passes above, and it needs no `.planning/`. It checks what the project's Markdown claims about the tree — the claims a reader acts on and a stale doc gets wrong. Default scope: `README.md`, `docs/**/*.md`, `AGENTS.md`, `CLAUDE.md` and `.planning/ARCHITECTURE.md`, each if present; paths narrow it. **Strictly read-only**, like the default mode: it changes nothing, including the docs it finds wrong.

1. **Mechanical claims** — run `python3 {devflow_root}/scripts/flow-docs-audit.py [paths…]` from the repo root. It emits JSON: every claim with `file`/`line`, a rule, and a status of `verified`, `contradicted`, or `could-not-check`. Rules: **D1** repo-relative paths in backticks or links exist; **D2** scripts invoked in shell fences exist; **D3** `npm run`/`pnpm`/`yarn` scripts are keys in the nearest `package.json`; **D4** `make` targets are in the Makefile; **D5** env var names in an environment/config table are referenced in some non-doc file (names only; `.env*` is never opened). Exit 2 means it could not run — report that, never a clean audit.
2. **Behaviour claims** — statements the script cannot parse ("`--auto` skips confirmations", "retries three times"). Check each one you report by pointing at the file:line that makes it true or false. A claim you cannot point at is `could-not-check`, never "fine" — and never go read a whole codebase to settle one.

Take `could-not-check` from the script as it stands: a missing `package.json` or an unreadable file is not evidence the claim holds.

**Severity**: a contradicted command or path in a README quick-start / install / setup / usage section is **HIGH** (the script marks these `severity: HIGH`); every other contradiction is **MEDIUM**; `could-not-check` is listed, not graded. Report in the same table shape as above with `pass` = the rule (`D1`–`D5`, or `behaviour`), worst first, then the script's `summary` counts verbatim so the reader sees how much was checked. **Offer** to fix the docs and wait for an explicit yes. Write nothing to `.planning/`.

Status line: clean → `FLOW: CONTINUE | docs audit clean: N claims verified | next: {the command STATE points to}`; any HIGH → `FLOW: GATE | docs audit: N high, M medium | next: fix the docs or the code they describe`; only MEDIUM → `CONTINUE` naming them as known debt.

## --drift (docs vs code)

`--drift [N] [--since <date|tag|sha>]` is a **separate mode**: it does not run the passes above. The default passes check the documents against each other and `--docs` checks paths and commands; `--drift` checks what the plan, STATE, decisions and agent instructions say was built against what the code and git history show. It answers the question a cold session cannot: *can I trust these docs?* `N` limits it to phase N; `--since` limits the git range. **Strictly read-only**, like the default mode: it changes nothing, including a STATE line it finds stale.

Read STATE.md, ROADMAP.md, ARCHITECTURE.md, DECISIONS.md and the project section of `CLAUDE.md`/`AGENTS.md` (outside the DevFlow block) whole; phase artifacts **frontmatter only**. Read source only to settle one specific claim — open the file:line that makes it true or false, never a whole codebase.

1. **X1 Plan → tree.** For each executed plan (a SUMMARY exists): every `must_haves.artifacts` and `files_new` path exists at `HEAD` (`git cat-file -e HEAD:<path>`), and every SUMMARY `commits` SHA resolves and is on this branch (`git merge-base --is-ancestor <sha> HEAD`). A missing artifact or an off-branch commit is work the docs claim and the code does not have.
2. **X2 Stale verification.** For each verified phase, find the commit that last wrote its VERIFICATION.md (`git log -1 --format=%H -- <path>`), then the commits since it that touch the phase's `files_modified` (`git log --no-merges --format='%h|%s|%(trailers:key=DevFlow-Plan,valueonly)' <sha>..HEAD -- <files>`). A change from outside that phase means the code was edited after it was proven, and the verification no longer covers what ships.
3. **X3 Unplanned work.** Non-merge commits in range that touch paths outside `.planning/` and carry no `DevFlow-Plan` trailer, with no matching `.planning/quick/` entry. Report the count and the top paths, not every commit: this is work no plan or requirement traces to.
4. **X4 STATE vs git.** Every branch, SHA and PR that STATE Position or Session names: the branch exists (`git rev-parse --verify`), the SHA resolves, and the PR is in the state STATE claims (`gh pr view <n> --json state` when gh is authenticated; otherwise `could-not-check`). A STATE that says "PR open" for a merged PR misleads the next session.
5. **X5 Decisions and instructions vs code.** Each concrete, checkable statement — an ARCHITECTURE.md manifest major or Forbidden item, a DECISIONS.md or STATE `## Decisions` entry that names a mechanism, a project rule in CLAUDE.md/AGENTS.md such as "all DB access goes through `src/data/`" — point at the file:line that makes it true or false. A statement you cannot settle that way is `could-not-check`, never "fine". Full manifest-against-ARCHITECTURE audits stay in `/flow-harden`; check only what a statement names.

A git command that fails, or a ref that does not resolve, is `could-not-check` with the reason — never evidence of a clean result.

**Severity**: a Forbidden item or principle the code violates is **CRITICAL**; a missing artifact, an off-branch SUMMARY commit, stale verification, and STATE contradicted by git are **HIGH**; unplanned work and a decision the code quietly departs from are **MEDIUM**; wording is **LOW**. `could-not-check` is listed, not graded. Same report table as above with `pass` = `X1`–`X5`, worst first, ~25 findings cap, then routes: stale verification → `/flow-verify N`; STATE drift → `/flow-status`; unplanned work → record it with `/flow-quick` or a plan; a decision the code contradicts → a decision for the human (update the decision or the code, never both silently). **Offer** the mechanical fixes and wait for an explicit yes. Write nothing to `.planning/`.

Status line: clean → `FLOW: CONTINUE | drift audit clean: N claims checked | next: {the command STATE points to}`; any CRITICAL or HIGH → `FLOW: GATE | drift audit: N critical, M high | next: {route}`; only MEDIUM/LOW → `CONTINUE` naming them as known debt.

## --export (evidence pack)

`--export [--since <date|tag|sha>]` is a **separate mode**: it does not run the passes above. It assembles the record of agent activity — which agents had access, what they changed, and who approved it — from git history and `.planning/`. Default range is the whole history; `--since` narrows it (e.g. a vendor review period).

Writing `.planning/exports/AUDIT-<YYYY-MM-DD>.md` does not break the read-only rule: that rule protects the artifacts being audited from an auditor that edits while it reads. A new derived file changes no evidence. Never modify anything it reads.

Fill `{devflow_root}/templates/audit-export.md` — it carries the section structure and the standard it holds each figure to. Sources, in order:
- **Changes** — `git log --format='%H|%ad|%an|%s|%(trailers:key=DevFlow-Agent,valueonly)|%(trailers:key=DevFlow-Plan,valueonly)' --date=short <range>`. Group by phase/plan; report attributed vs total and name the unattributed remainder rather than quietly excluding it.
- **Access** — providers and models **observed in the trailers**, not read from `config.json`: config is current state and says nothing about what ran in March. Report the declared values too, and flag any difference.
- **Approvals** — `.planning/DECISIONS.md` in range, verbatim, plus `deploy/SIGNOFF.md`.
- **Rework rate** — `python3 {devflow_root}/scripts/flow-rework.py --since <same range start> --json`, omitting `--since` when the export covers the whole history (it then measures the last 30 days, and the section says so). Copy the agent and baseline figures, top files, and every note verbatim. It is a signal, not a gate: no threshold, and no rate turns the status line into a GATE. Exit 2 means it could not run — write "not recorded" with the reason.
- **Verification** — `VERIFICATION.md` frontmatter per phase: status, smoke, human checks, `unverified`.
- **Controls** — from `conventions.md` and `autonomy.md`: what is *enforced*, not outcomes you haven't measured.

Two rules the template states and you must hold to: derive every figure from a command you ran or a file you read (unreproducible numbers are worse than absent ones — write "not recorded"), and put the limitations section first, including any period where the trailers or the decision log did not yet exist. A partial record presented as a complete one is the failure mode here.

**Before finalizing**: run the conventions.md secret scan over the assembled pack, exactly as for an outbound consult bundle — this artifact leaves the machine. A hit is fail-closed: don't write the file, report file/line/pattern class (never the value), `FLOW: GATE`. Then tell the user the pack carries approver names and emails from the decision log, and that **DevFlow never sends it** — distribution is entirely their call.

Commit when `commit_docs` (`chore(flow): audit export <date>`, attribution trailers per conventions.md) so the exact pack that was handed over stays reproducible at a known SHA. This is the one `/flow-audit` mode that writes, so it is also the one that journals: prepend a JOURNAL line.

Status line: `FLOW: GATE | audit export written to <path> — review before sharing | next: {the command STATE points to}`. A pack going to a third party is a human decision, never an autonomous step.

End with the status line per `{devflow_root}/references/autonomy.md` — clean: `FLOW: CONTINUE | audit clean | next: {the command STATE points to}`; findings that need a decision: `FLOW: GATE | audit: N critical, M high | next: {route}`; only MEDIUM/LOW: `CONTINUE` naming them as known debt.
