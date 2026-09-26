---
name: flow-security-audit
description: Optional pre-production security audit gate (Cloudflare harness patterns). Opt-in only — not part of default /flow-* runs. Use when explicitly asked to security-audit / pen-test / full vuln review before UAT/prod. Modes: guidance (default for questions) vs full audit (explicit). Supports --provider native|claude|codex.
disable-model-invocation: true
---

# flow-security-audit

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

**Agent provider**: accept `--provider native|claude|codex`. Resolve and dispatch every role in this run exactly as `{devflow_root}/references/hosts.md` specifies. A missing or failed peer is fail-closed; report `FLOW: BLOCKED` with remediation and never fall back silently.

Context rules: read `.planning/STATE.md` first (absent is fine — this skill needs no `.planning/`); paths not contents.

**Opt-in only.** This skill does not run on every /flow-* invocation. `/flow-next` never routes to it, and `/flow-harden`, `/flow-uat`, and `/flow-release` do not require it. The gate is off by default: run it before `/flow-uat` or `/flow-release` when a human asks for a pre-production audit. It is a thin DevFlow wrapper over the method in Cloudflare's [security-audit skill](https://github.com/cloudflare/security-audit-skill) (MIT); for depth, point at that repo's companion files by URL — never install it for the user.

## Operating modes
- **Guidance** (default): security questions, a focused review of one path, triage of a specific finding. Use only the relevant principles below, answer in the transcript, write no files, run no phases.
- **Full audit**: only when the user explicitly asks to audit / pen-test the codebase, asks for a full or end-to-end security review, or asks for report artifacts. Run every phase below.

Ambiguous request → ask one focused question before creating any file.

## Core principles (both modes)
1. **Boundary + result.** Every candidate names the lower-trust principal, the input or action, the intended control, the boundary crossed, the affected principal/resource, and a concrete result. No boundary and result → not a finding.
2. **Hunter ≠ verifier.** Whoever found a candidate never confirms it; a fresh context tries to refute it.
3. **Severity only on `confirmed`** — critical / high / medium / low / informational, never above the demonstrated impact. High vs medium: does it *fully defeat* an explicit control for an action with real consequences, or only weaken it?
4. **`needs_validation` for missing deployment facts.** Proxy, identity-provider, cloud, header, or topology behavior not in the repo is neither assumed present nor absent — name the exact missing fact and a safe owner-run check. No severity.
5. **No live probing.** Source-only. Never contact deployed endpoints, shared services, or real identities; never execute target code here. A fact that needs execution becomes `needs_validation` — upstream's sandbox rules cover safe local execution if a human wants it.
6. **A checklist deviation is not a vulnerability**, and a **defense-in-depth gap is not a vulnerability** without a reachable boundary violation. Report those as hardening notes at most (`/flow-harden` owns hardening).
7. **Smallest effective fix** at the last trusted decision point, plus a regression test. The audit describes fixes; it never edits target source.

## AI / LLM companion
When the target has LLM surfaces (prompt assembly, RAG, agent memory, tool calling, MCP), add units for: indirect prompt injection via ingested content; cross-tenant context or cache bleed; tool-argument injection into sinks; confused-deputy agency (tool runs with a broader identity than the requester); approval not bound to the exact action; model output rendered or executed unescaped. Prompt injection alone is not a finding — require a code-level boundary failure. A guardrail prompt is not a control. Depth: upstream https://github.com/cloudflare/security-audit-skill/blob/main/AI-AND-LLM.md.

## Full audit
**Output directory** — decide before reconnaissance:
- `.planning/security-audit/run-N/` only if `git check-ignore -q .planning/security-audit/` succeeds (the whole directory is ignored);
- otherwise `~/security-audit-skill/<repo>/run-N/` (next unused N), outside the target.
Never write artifacts to a tracked path. Record the reviewed SHA and whether the worktree is dirty.

The orchestrator is the only writer of `run-metadata.json` (repo, SHA, profile `quick|standard|deep`, scope), `coverage-ledger.json`, `findings.json`, `REPORT.md`, `NEEDS-VALIDATION.md`.

**Phases**, in order:
1. **Recon** — map entry points, trust boundaries, principals, data stores, and LLM surfaces. Seed the coverage ledger: one unit per surface × boundary × attack class, each `planned`. Read any prior run's ledger and findings; a prior run never implies "the rest is fine".
2. **Coverage-led hunt** — one `flow-reviewer` per unit, lens `security`, scoped to the unit's paths (whole files: `git diff $(git hash-object -t tree /dev/null) HEAD -- <paths>`), with principles 1, 4–6 in the prompt. Each returns structured candidates (fingerprint, trace file:line, boundary, result). Mark each unit `covered`, `candidate`, `blocked`, or `deferred` — never silently skipped. One coverage-critic pass then names any surface the ledger missed.
3. **Candidate validation** — dedupe by fingerprint; each candidate goes to a **fresh** `flow-reviewer` (lens `security`) told only the claim, instructed to refute it from source and return `confirmed`, `needs_validation`, or `rejected` with evidence.
4. **Structured findings** — write `findings.json`. Record fields mirror upstream `report-schema.json`: every record carries `verdict`, `fingerprint`, `title`, `description`, `trace`, `evidence`; `confirmed` adds `root_cause`, `conditions`, `remediation`, `severity`; `needs_validation` adds `blockers`, `validation_plan`; `rejected` adds `reason`. If a local checkout of the upstream skill exists, run its `validate-findings.cjs` and `validate-coverage-ledger.cjs`; otherwise say the validators were not run.
5. **Independent verify** — a fresh read-only role re-checks every `confirmed` record's file:line claims against source before any report is written; disagreement demotes the record.
6. **Report** — `REPORT.md` (scope, profile, coverage statement stating what was *not* covered, confirmed findings by severity), `NEEDS-VALIDATION.md` (each missing fact with its safe check). No live-probe instructions. Run the `{devflow_root}/references/conventions.md` secret scan over the artifacts; a hit is fail-closed (`FLOW: GATE`, report file/line/pattern class, never the value).

Terminal states are exactly two: all artifacts written, or `run_status: incomplete` with its reason recorded and disclosed. Never stop mid-phase.

This skill changes no `.planning/` state, commits nothing, and does not fix findings — fixes go through `/flow-quick` or `/flow-plan` on a feature branch.

End with the status line per `{devflow_root}/references/autonomy.md` (never `DONE` — an audit does not finish a project):
- guidance: `FLOW: CONTINUE | security guidance given | next: {the command STATE points to}`
- any `confirmed` critical/high, or any `needs_validation`: `FLOW: GATE | security audit: N confirmed (H critical/high), V needs_validation — see <run dir> | next: /flow-quick <fix> or answer NEEDS-VALIDATION.md`
- only medium/low/informational or clean: `FLOW: CONTINUE | security audit: <summary>, coverage <profile/scope> | next: {the command STATE points to}`
- incomplete run or peer failure: `FLOW: BLOCKED | security audit incomplete: <reason> | next: <remediation>`
