---
name: flow-plan
description: Plan one roadmap phase - discuss decisions, optional research, write plans, check them. Args - phase number, plus optional --auto (no questions), --gaps (replan from verification gaps), --research, --review (publish the plan graph as a review page). Use before executing a phase.
---

# flow-plan

Context rules: read `.planning/STATE.md` first (missing but `.planning/` exists → offer reconstruction from ROADMAP + newest SUMMARY frontmatter; no `.planning/` → point to `/flow-new`). Pass subagents paths, never contents. Keep output terse.

**Pre-flight**: REQUIREMENTS.md and ROADMAP.md exist; the phase number exists in ROADMAP. `--gaps` additionally requires `phases/NN-slug/VERIFICATION.md` with gaps. Block with a specific message otherwise.

1. **Discuss** (skip in `--auto` and `--gaps`): read the phase's ROADMAP row + its REQ lines. Identify genuinely open decisions (approach choices the requirements don't settle). Ask ≤3 via AskUserQuestion. Write `phases/NN-slug/CONTEXT.md` ONLY if real decisions were made: `## Locked` (D-NN decisions), `## Deferred` (ideas explicitly not now), `## Discretion` (planner's choice). No decisions → no file.

2. **Research** (if `--research`, or discussion surfaced unknowns worth verifying — offer): spawn `flow-researcher` with the specific questions; output `phases/NN-slug/RESEARCH.md`.

3. **Plan**: spawn `flow-planner` with paths only: `${CLAUDE_PLUGIN_ROOT}/references/plan-format.md`, `${CLAUDE_PLUGIN_ROOT}/references/conventions.md`, `${CLAUDE_PLUGIN_ROOT}/templates/plan.md`, `.planning/{STATE,ROADMAP,REQUIREMENTS,PROJECT}.md`, plus ARCHITECTURE.md / DESIGN.md / CONTEXT.md / RESEARCH.md / LEARNINGS.md / `codebase/MAP.md` when present, and the phase dir to write into. `--gaps`: state gap mode and pass the VERIFICATION.md path.

4. **Check** (revision gate): spawn `flow-plan-checker` with the plan-format reference path + phase dir (+ ARCHITECTURE.md / DESIGN.md / LEARNINGS.md paths when present). `PASS` → continue. Issues → respawn planner in revision mode with the numbered issues; re-check. Max 3 iterations; if capped, or the issue count stops shrinking between rounds, escalate: show the user the unresolved issues and ask proceed / fix manually / second opinion (`/flow-oracle` seeded with the plan + issues) / abort. In `--auto`: don't ask — stop with a GATE status line carrying the unresolved issues.

5. **Review page** (only with `--review`, or when the user asks to see the plan): publish the phase's plan graph as an Artifact so the human reviews *before* execution, where a wrong assumption is one replan instead of a phase of rework. Load the `artifact-design` skill first, write the page to your scratchpad dir, then publish with a stable `file_path` (republishing the same path updates the same URL — reuse it on `--gaps` rounds rather than minting a second page).

   From plan **frontmatter only** — never paste task bodies, never inline source: the wave graph as a mermaid diagram (nodes = plans, edges = `depends_on`, plans grouped by wave so the parallel layers are visible); per plan its objective, `requirements`, `files_modified`, and `must_haves.truths`; the `## Locked` / `## Deferred` decisions from CONTEXT.md; any `user_setup` items; and the plan-checker's unresolved issues if step 4 escalated. Close with what the reviewer is being asked to check — wrong wave assignment, a missing edge, a truth that doesn't prove the goal, a decision they'd make differently — and the two commands: `/flow-execute N` to proceed, `/flow-plan N` to replan.

   Secret-scan the rendered page per conventions.md before publishing — a hit blocks the publish, `GATE`. Artifacts start private; sharing is the user's call, so don't offer to distribute it. Record the URL in STATE.md's Session section. This is a *review aid*, not an artifact of record: the plan files stay the source of truth, and nothing here changes what executors read.

6. **Close**: update STATE.md (Position: status ready, Next: `/flow-execute N`), set the ROADMAP row to planned. Commit (if commit_docs): `chore(flow): plan phase NN`; prepend a `.planning/JOURNAL.md` line (format `${CLAUDE_PLUGIN_ROOT}/templates/journal.md`; create if missing). Print plan list (id — objective, wave).

End with the status line per `${CLAUDE_PLUGIN_ROOT}/references/autonomy.md` — success: `FLOW: CONTINUE | phase N planned, M plans | next: /flow-execute N`; escalation: `GATE`.
