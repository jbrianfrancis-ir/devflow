---
name: flow-plan
description: Plan one roadmap phase - discuss decisions, optional research, write plans, check them. Args - phase number, plus optional --auto (no questions), --gaps (replan from verification gaps), --research, --review (publish the plan graph as a review page). Use before executing a phase. Supports --provider native|claude|codex.
---

# flow-plan

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

**Agent provider**: accept `--provider native|claude|codex`. Resolve and dispatch every role in this run exactly as `references/hosts.md` specifies. The selected provider applies to all delegated roles unless this skill explicitly calls an external consultation engine. A missing or failed peer is fail-closed; report `FLOW: BLOCKED` with remediation and never fall back silently.

Context rules: read `.planning/STATE.md` first (missing but `.planning/` exists → offer reconstruction from ROADMAP + newest SUMMARY frontmatter; no `.planning/` → point to `/flow-new`). Pass subagents paths, never contents. Keep output terse.

**Pre-flight**: REQUIREMENTS.md and ROADMAP.md exist; the phase number exists in ROADMAP. `--gaps` additionally requires `phases/NN-slug/VERIFICATION.md` with gaps. Block with a specific message otherwise.

1. **Discuss** (skip in `--auto` and `--gaps`): read the phase's ROADMAP row + its REQ lines. Identify genuinely open decisions (approach choices the requirements don't settle). **Any `[NEEDS CLARIFICATION: …]` marker on this phase's requirements goes first** — those questions were already identified as changing what gets built, and this is the last cheap moment to answer them. Ask ≤3 with the host question mechanism, markers before anything you newly noticed. An answered marker is resolved in REQUIREMENTS.md — replace the marker with the decision and log it as D-NN — so it never has to be asked twice. In `--auto` no marker is answered; they stay open and become backstop truths at step 3. Write `phases/NN-slug/CONTEXT.md` ONLY if real decisions were made: `## Locked` (D-NN decisions), `## Deferred` (ideas explicitly not now), `## Discretion` (planner's choice). No decisions → no file.

2. **Research** (if `--research`, or discussion surfaced unknowns worth verifying — offer): spawn `flow-researcher` with the specific questions; output `phases/NN-slug/RESEARCH.md`.

3. **Plan**: spawn `flow-planner` with paths only: `{devflow_root}/references/plan-format.md`, `{devflow_root}/references/conventions.md`, `{devflow_root}/templates/plan.md`, `.planning/{STATE,ROADMAP,REQUIREMENTS,PROJECT}.md`, plus ARCHITECTURE.md / DESIGN.md / CONTEXT.md / RESEARCH.md / LEARNINGS.md / `codebase/MAP.md` when present, and the phase dir to write into. `--gaps`: state gap mode and pass the VERIFICATION.md path.

4. **Check** (revision gate): spawn `flow-plan-checker` with the plan-format reference path + phase dir + `.planning/REQUIREMENTS.md` (it checks coverage both directions and that open markers carry backstop truths) (+ ARCHITECTURE.md / DESIGN.md / LEARNINGS.md paths when present). `PASS` → continue. Issues → respawn planner in revision mode with the numbered issues; re-check. Max 3 iterations; if capped, or the issue count stops shrinking between rounds, escalate: show the user the unresolved issues and ask proceed / fix manually / second opinion (`/flow-oracle` seeded with the plan + issues) / abort. In `--auto`: don't ask — stop with a GATE status line carrying the unresolved issues.

5. **Review page** (only with `--review`, or when the user asks to see the plan): render the phase's plan graph so the human reviews *before* execution, where a wrong assumption is one replan instead of a phase of rework. When the host provides Artifact publishing, load its artifact-design skill, write to the scratchpad, and publish with a stable `file_path`. Otherwise write or replace `.planning/reviews/phase-NN-plan.md` and return that path. Reuse the destination on `--gaps` rounds.

   From plan **frontmatter only** — never paste task bodies, never inline source: the wave graph as a mermaid diagram (nodes = plans, edges = `depends_on`, plans grouped by wave so the parallel layers are visible); per plan its objective, `requirements`, `files_modified`, and `must_haves.truths`; the `## Locked` / `## Deferred` decisions from CONTEXT.md; any `user_setup` items; and the plan-checker's unresolved issues if step 4 escalated. Close with what the reviewer is being asked to check — wrong wave assignment, a missing edge, a truth that doesn't prove the goal, a decision they'd make differently — and the two commands: `/flow-execute N` to proceed, `/flow-plan N` to replan.

   Secret-scan the rendered page per conventions.md before publishing or reporting it — a hit blocks the operation, `GATE`. Hosted Artifacts start private; sharing is the user's call. Record the URL or local path in STATE.md's Session section. This is a *review aid*, not an artifact of record: plan files stay authoritative.

6. **Close**: update STATE.md (Position: status ready, Next: `/flow-execute N`), set the ROADMAP row to planned. Commit (if commit_docs): `chore(flow): plan phase NN`; prepend a `.planning/JOURNAL.md` line (format `{devflow_root}/templates/journal.md`; create if missing). Print plan list (id — objective, wave).

End with the status line per `{devflow_root}/references/autonomy.md` — success: `FLOW: CONTINUE | phase N planned, M plans | next: /flow-execute N`; escalation: `GATE`.
