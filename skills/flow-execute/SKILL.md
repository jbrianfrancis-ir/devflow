---
name: flow-execute
description: Execute all plans of a phase in dependency waves via parallel executor subagents, then verify. Args - phase number, optional --auto (skip confirmations). Use after /flow-plan.
---

# flow-execute

Context rules: read `.planning/STATE.md` first; pass subagents paths, never contents; read plan/SUMMARY **frontmatter only** in this session; keep output terse — the executors do the work.

**Pre-flight**: phase dir has `NN-MM-PLAN.md` files; working tree clean (`git status --short` — otherwise ask to commit/stash, or proceed on explicit confirmation). Surface any `user_setup` items from plan frontmatter and confirm they're done before starting.

1. **Wave plan**: read each plan's frontmatter. Skip plans whose SUMMARY already exists (resume support). Group the rest by `wave`.

2. **Execute wave by wave** (waves in order; plans within a wave in parallel — spawn all `flow-executor` agents for the wave in one message). Each executor prompt: the plan path, `.planning/STATE.md` path (+ `.planning/ARCHITECTURE.md` and, for UI plans, `.planning/DESIGN.md` when present), template path `${CLAUDE_PLUGIN_ROOT}/templates/summary.md`, checkpoints reference `${CLAUDE_PLUGIN_ROOT}/references/checkpoints.md`, and "read the plan and execute it". Keep only each result block (≤15 lines) in context.

3. **Checkpoints**: an executor returning `CHECKPOINT` pauses its plan, not the wave. Present the `need` to the user (AskUserQuestion for decisions), then respawn that executor in continuation mode: plan path + completed tasks/SHAs + the user's answer. Checkpoints are human gates even in `--auto` — never answer one yourself; finish the wave's other plans, then stop with a GATE status line carrying the checkpoint content. Failed executor (no SUMMARY, no checkpoint): retry once; then ask skip/abort (interactive) or stop with BLOCKED (`--auto`).

4. **Verify** after the last wave: spawn `flow-verifier` with the phase dir, `${CLAUDE_PLUGIN_ROOT}/references/verification.md`, and `${CLAUDE_PLUGIN_ROOT}/templates/verification.md`.
   - `gaps` → print them; update STATE (Blockers: gaps, Next: `/flow-plan N --gaps`). Stop.
   - `human_needed` → present the batched human checks now (walk through, record pass/fail in VERIFICATION.md); any fail → treat as gaps. In `--auto`: don't walk through — stop with a GATE status line listing the checks.
   - `pass` → set ROADMAP row verified; append the verifier's learnings bullets to `.planning/LEARNINGS.md` (cap 20 bullets — consolidate oldest when over); update STATE (Position, Next: `/flow-plan N+1` or `/flow-harden` when all phases verified).

5. **Close**: commit docs (if commit_docs): `chore(flow): phase NN executed + verified`. Print: plans done, commits, deviations flagged, verification status.

End with the status line per `${CLAUDE_PLUGIN_ROOT}/references/autonomy.md` — pass: `FLOW: CONTINUE | phase N verified | next: {/flow-plan N+1 or /flow-harden}`; gaps: `CONTINUE` toward `--gaps`; checkpoint/human checks pending: `GATE`; unrecoverable: `BLOCKED`.
