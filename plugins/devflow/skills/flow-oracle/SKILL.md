---
name: flow-oracle
description: Ask an external frontier model for a second opinion via a curated context bundle. Args - question, plus optional --panel (multi-model cross-check), --followup NNN, or no args to resume the newest open consult. Use when stuck or before a high-stakes decision. Supports --provider native|claude|codex.
---

# flow-oracle

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

**Agent provider**: accept `--provider native|claude|codex`. Resolve and dispatch every role in this run exactly as `references/hosts.md` specifies. The selected provider applies to all delegated roles unless this skill explicitly calls an external consultation engine. A missing or failed peer is fail-closed; report `FLOW: BLOCKED` with remediation and never fall back silently.

Context rules: read `.planning/STATE.md` first if present (no `.planning/` → still works: create `.planning/consults/`, skip journaling, warn once). Read `{devflow_root}/references/oracle.md` — it defines engines, the bundle format, the outbound secret scan, and the send gate. Keep output terse.

1. **Resume** (no args): newest `status: draft|sent` file in `.planning/consults/` — `sent` with a session id → collect (`oracle session <id>`, or ask the user to save the reply as `RESPONSE.md` beside the bundle) and go to step 5; `draft` with a ready bundle (manual engine) → remind the user to paste `BUNDLE.md` and save the reply, then GATE. Nothing open → ask for the question. `--followup NNN` → new consult with `parent: NNN`, seeded with NNN's verdict + the delta only, reusing NNN's engine session when recorded.

2. **Seed**: create `.planning/consults/NNN-slug.md` from `{devflow_root}/templates/consult.md`. Propose the file manifest — only files that change the answer: an open debug file (symptom + hypotheses + evidence), a plan + its checker issues, the code under suspicion. Never "the whole repo"; never the contract's excluded types.

3. **Engine**: detect per the reference (oracle CLI → oracle MCP → manual render-and-copy). Default model per engine; `--panel` → 2–3 models. Record engine/models in the consult file.

4. **Send gate + consult**: show engine, model(s), and manifest (path, bytes); sending code externally is outward-facing (autonomy.md) — explicit user OK required, and under `--auto`//`/goal`//`/loop` never auto-send (GATE). On OK, spawn `flow-consultant` with paths only: the consult file, `{devflow_root}/references/oracle.md`, `{devflow_root}/references/conventions.md`, ARCHITECTURE.md when present, the approved file list, question, engine + models. Handle returns: `SCAN-HIT` → GATE per conventions (never echo the value); `PENDING` → GATE (collect later by rerunning `/flow-oracle`); `BUNDLE-READY` → tell the user where the bundle is, what to paste it into, and to save the reply as `RESPONSE.md` beside it, then GATE.

5. **Apply** (`ANSWERED`): present the ≤10-line verdict. Any `[CONFLICTS: pin]` line → `checkpoint:decision`, never silent adoption. Route by origin: debug consult → merge surviving suggestions as new hypotheses into the debug file; plan consult → feed into `/flow-plan` revision; else the user decides. Set `status: applied` (+ Outcome with the commit/plan/debug ref) or `discarded` (+ why). Prepend a `.planning/JOURNAL.md` line (format `{devflow_root}/templates/journal.md`; create if missing).

End with the status line per `{devflow_root}/references/autonomy.md` — applied/discarded: `FLOW: CONTINUE | consult NNN {applied|discarded} | next: {per STATE}`; awaiting send OK, a manual paste, or a detached run: `GATE`; scan hit: `GATE`.
