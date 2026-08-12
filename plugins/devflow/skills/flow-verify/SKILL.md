---
name: flow-verify
description: Re-verify an executed phase against its must_haves and walk the user through batched human checks. Args - phase number. Use standalone after changes, or when /flow-execute ended with human checks pending. Supports --provider native|claude|codex.
---

# flow-verify

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

**Agent provider**: accept `--provider native|claude|codex`. Resolve and dispatch every role in this run exactly as `references/hosts.md` specifies. The selected provider applies to all delegated roles unless this skill explicitly calls an external consultation engine. A missing or failed peer is fail-closed; report `FLOW: BLOCKED` with remediation and never fall back silently.

Context rules: read `.planning/STATE.md` first; paths not contents; frontmatter-only reads.

**Pre-flight**: phase dir exists with at least one SUMMARY. Otherwise point to `/flow-execute N`.

1. Spawn `flow-verifier` with: the phase dir, `{devflow_root}/references/verification.md`, `{devflow_root}/templates/verification.md`. It rewrites `VERIFICATION.md`.

2. Present results: status, truths table summary, gaps.

3. **Human checks**: walk the user through the batched list one item at a time (what to do, what they should see); record pass/fail in VERIFICATION.md. Failures become gaps.

4. Route: gaps → STATE Blockers + `Next: /flow-plan N --gaps`; all pass → ROADMAP row verified, STATE updated (Next: next unplanned phase, or `/flow-harden` when all verified). Commit docs if commit_docs: `chore(flow): phase NN verified`; prepend a `.planning/JOURNAL.md` line (format `{devflow_root}/templates/journal.md`; create if missing).

End with the status line per `{devflow_root}/references/autonomy.md` — pass: `FLOW: CONTINUE | phase N verified | next: {next command}`; gaps: `CONTINUE` toward `--gaps`; human checks pending: `GATE`.
