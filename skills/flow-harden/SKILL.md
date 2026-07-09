---
name: flow-harden
description: Production-hardening pass - audit the codebase against the Aspire production checklist, fix findings via a hardening plan. Use after all roadmap phases are verified, before /flow-uat.
---

# flow-harden

Context rules: read `.planning/STATE.md` first; paths not contents.

**Pre-flight**: all ROADMAP phases verified (otherwise list what's pending and stop — hardening unfinished work wastes a pass).

1. **Read** `${CLAUDE_PLUGIN_ROOT}/references/aspire.md` (Detection, No-AppHost, Build-gate, Hardening-checklist sections).

2. **AppHost gate**: detect the Aspire AppHost and CLIs per the reference. No AppHost → the first hardening task is creating one that models every existing service and external resource (per the reference), gated by `aspire run` working locally. Missing CLIs → give the user the install pointers and stop.

3. **Audit** (read-only, this session): walk the hardening checklist against the codebase. If `.planning/ARCHITECTURE.md` exists, also diff it against reality (manifest versions, libraries in use, forbidden items) — drift is a finding. Run `aspire publish` as the build gate. Record each finding as: what, where, why it blocks production.

4. **Fix**: no findings → skip to 5. Otherwise write the findings as a standard plan (spawn `flow-planner` with the findings, gap-mode style: smallest change per finding; phase dir `.planning/phases/H1-hardening/`), then spawn `flow-executor` per plan and `flow-verifier` after — same contracts as /flow-execute (templates and references from `${CLAUDE_PLUGIN_ROOT}` as usual). Re-run `aspire publish` to confirm green.

5. **Close**: create `.planning/deploy/PIPELINE.md` if missing:
   ```markdown
   # Deploy pipeline
   | Env | azd env | Provisioned | Last deploy (SHA, date) | Result | URLs |
   |-----|---------|-------------|--------------------------|--------|------|
   | uat | — | no | — | — | — |
   | prod | — | no | — | — | — |
   ```
   Update STATE.md (Status: hardened, Next: `/flow-pr` — integrate before deploying). Commit `chore(flow): hardening pass` on the feature branch and `git push origin <branch>`. Repeat runs are cheap — re-audit and report "already hardened" when clean.

Hardening fixes are code, so they land on the feature branch like any other work and reach base via `/flow-pr`; deploy (`/flow-uat`, `/flow-release`) runs from merged base code.

End with the status line per `${CLAUDE_PLUGIN_ROOT}/references/autonomy.md` — clean: `FLOW: GATE | hardened; open a PR before deploy | next: /flow-pr`; findings being fixed: `CONTINUE`; missing CLIs/AppHost decision: `GATE`.
