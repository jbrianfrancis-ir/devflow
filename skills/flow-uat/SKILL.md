---
name: flow-uat
description: Deploy to the UAT environment on Azure (provisioning on first deploy) and generate the human acceptance test plan whose sign-off gates production. Use after /flow-harden.
---

# flow-uat

Context rules: read `.planning/STATE.md` first. Auth and secrets are the human's job; commands are yours — never store credentials in the repo.

**Pre-flight**: STATE shows hardened (or `deploy/PIPELINE.md` exists); working tree clean; `aspire` and `azd` CLIs available; `azd auth login --check-status` OK (otherwise have the user run `azd auth login` and wait). Block with specifics otherwise.

1. **Read** `${CLAUDE_PLUGIN_ROOT}/references/aspire.md` (Environments, Environment-config, Failure→fix sections).

2. **UAT test plan**: generate `.planning/deploy/UAT-PLAN.md` from `${CLAUDE_PLUGIN_ROOT}/templates/uat-plan.md`: one acceptance case per REQ-ID in REQUIREMENTS.md (steps a human can follow, observable expected result) + the smoke section. Set round = previous+1, sha = `git rev-parse HEAD`.

3. **Deploy** per the reference: `azd env list` → PIPELINE says uat unprovisioned or env absent → `azd init` (if needed), `azd env new uat`, `azd env select uat`, `azd up` (azd prompts the user for parameters/secrets — let it). Already provisioned → `azd env select uat`, then `azd provision` only if the AppHost/infra model changed since the last uat deploy (check git diff on AppHost project), then `azd deploy`.

4. **Post-deploy**: capture endpoint URLs from azd output into UAT-PLAN frontmatter and PIPELINE.md; curl the health endpoints (smoke). Update the PIPELINE uat row (SHA, date, result). Deploy or smoke failure → apply the reference's failure table; fixes go through `/flow-quick`; then redeploy.

5. **Acceptance**: hand the user the UAT plan with live URLs; offer to walk through it case by case. Record pass/fail per case in UAT-PLAN.md.
   - **All pass** → write `.planning/deploy/SIGNOFF.md`: approver (ask who), date, `sha`, round, result summary, `approved-for-production: true`. Say: `Next: /flow-release`.
   - **Any fail** → set UAT-PLAN result: failed, NO sign-off. Route each failure: requirement gap → `/flow-plan N --gaps`; defect → `/flow-quick` or `/flow-debug`. After fixes: re-run `/flow-uat` (new round, new sign-off — sign-off is per-SHA).

After a successful deploy, offer the monitoring recipe: `/loop 15m curl the UAT health endpoints and report any change`. The acceptance walkthrough and sign-off are always human-gated — never record results or write SIGNOFF.md autonomously.

Commit docs: `chore(flow): uat round N`; prepend a `.planning/JOURNAL.md` line — round, result (format `${CLAUDE_PLUGIN_ROOT}/templates/journal.md`; create if missing).

End with the status line per `${CLAUDE_PLUGIN_ROOT}/references/autonomy.md` — deployed, awaiting acceptance: `FLOW: GATE | uat round N deployed, acceptance pending | next: walk UAT-PLAN.md`; signed off: `CONTINUE | next: /flow-release`; failures: `CONTINUE` toward the fix route.
