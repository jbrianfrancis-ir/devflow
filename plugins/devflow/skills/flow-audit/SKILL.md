---
name: flow-audit
description: Read-only cross-artifact consistency check across REQUIREMENTS, ROADMAP, plans, SUMMARYs, VERIFICATION and STATE - coverage both directions, drift, unmeasurable criteria, open clarifications, principle conflicts. Use before executing a phase, before /flow-harden, or when the planning docs feel out of sync. --export assembles an agent-activity evidence pack (who had access, what changed, who approved) for a vendor or compliance review.
---

# flow-audit

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

Context rules: read `.planning/STATE.md` first. Everything here is small and capped — read REQUIREMENTS.md, ROADMAP.md, ARCHITECTURE.md and STATE.md whole, and phase artifacts (`*-PLAN.md`, `*-SUMMARY.md`, `VERIFICATION.md`) **frontmatter only**. Never read source; this audits the documents against each other, not the code (`/flow-verify` proves code, `/flow-harden` audits production-readiness).

**STRICTLY READ-ONLY.** Change nothing — not a status, not a typo, not a marker. DevFlow spreads project knowledge across artifacts on purpose, and an auditor that edits while it reads destroys the evidence of what disagreed with what. Findings end in a report and a recommended route; the human decides.

**Pre-flight**: `.planning/` with REQUIREMENTS.md and ROADMAP.md. Missing → point to `/flow-new`. Scope defaults to the whole project; `N` limits it to phase N's artifacts plus the project-level files they reference. (`--export` needs only `.planning/` and a git checkout — it reports on what exists rather than checking it.)

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

## --export (evidence pack)

`--export [--since <date|tag|sha>]` is a **separate mode**: it does not run the passes above. It assembles the record of agent activity — which agents had access, what they changed, and who approved it — from git history and `.planning/`. Default range is the whole history; `--since` narrows it (e.g. a vendor review period).

Writing `.planning/exports/AUDIT-<YYYY-MM-DD>.md` does not break the read-only rule: that rule protects the artifacts being audited from an auditor that edits while it reads. A new derived file changes no evidence. Never modify anything it reads.

Fill `{devflow_root}/templates/audit-export.md` — it carries the section structure and the standard it holds each figure to. Sources, in order:
- **Changes** — `git log --format='%H|%ad|%an|%s|%(trailers:key=DevFlow-Agent,valueonly)|%(trailers:key=DevFlow-Plan,valueonly)' --date=short <range>`. Group by phase/plan; report attributed vs total and name the unattributed remainder rather than quietly excluding it.
- **Access** — providers and models **observed in the trailers**, not read from `config.json`: config is current state and says nothing about what ran in March. Report the declared values too, and flag any difference.
- **Approvals** — `.planning/DECISIONS.md` in range, verbatim, plus `deploy/SIGNOFF.md`.
- **Verification** — `VERIFICATION.md` frontmatter per phase: status, smoke, human checks, `unverified`.
- **Controls** — from `conventions.md` and `autonomy.md`: what is *enforced*, not outcomes you haven't measured.

Two rules the template states and you must hold to: derive every figure from a command you ran or a file you read (unreproducible numbers are worse than absent ones — write "not recorded"), and put the limitations section first, including any period where the trailers or the decision log did not yet exist. A partial record presented as a complete one is the failure mode here.

**Before finalizing**: run the conventions.md secret scan over the assembled pack, exactly as for an outbound consult bundle — this artifact leaves the machine. A hit is fail-closed: don't write the file, report file/line/pattern class (never the value), `FLOW: GATE`. Then tell the user the pack carries approver names and emails from the decision log, and that **DevFlow never sends it** — distribution is entirely their call.

Commit when `commit_docs` (`chore(flow): audit export <date>`, attribution trailers per conventions.md) so the exact pack that was handed over stays reproducible at a known SHA. This is the one `/flow-audit` mode that writes, so it is also the one that journals: prepend a JOURNAL line.

Status line: `FLOW: GATE | audit export written to <path> — review before sharing | next: {the command STATE points to}`. A pack going to a third party is a human decision, never an autonomous step.

End with the status line per `{devflow_root}/references/autonomy.md` — clean: `FLOW: CONTINUE | audit clean | next: {the command STATE points to}`; findings that need a decision: `FLOW: GATE | audit: N critical, M high | next: {route}`; only MEDIUM/LOW: `CONTINUE` naming them as known debt.
