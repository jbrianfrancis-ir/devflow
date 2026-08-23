---
name: flow-uat
description: Deploy to the UAT environment on Azure (provisioning on first deploy) and generate the human acceptance test plan whose sign-off gates production. Use after /flow-harden.
---

# flow-uat

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

Context rules: read `.planning/STATE.md` first. Auth and secrets are the human's job; commands are yours — never store credentials in the repo.

**Pre-flight**: **Deploy N/A**: `.planning/config.json` → `deploy.tool` is `null` means this project has nothing to deploy (autonomy.md), so this skill does not apply — say so, point at the `D-NN` that recorded it, and stop with `FLOW: GATE | no deployable surface — /flow-uat does not apply | next: /flow-pr` (or `/flow-next` once merged). Only an explicit `null` qualifies; missing or unreadable config means the project deploys. Otherwise: STATE shows hardened (or `deploy/PIPELINE.md` exists); working tree clean; `aspire` and `azd` CLIs available; `azd auth login --check-status` OK (otherwise have the user run `azd auth login` and wait). Block with specifics otherwise.

1. **Read** `{devflow_root}/references/aspire.md` (Environments, Environment-config, Failure→fix sections).

2. **UAT test plan**: generate `.planning/deploy/UAT-PLAN.md` from `{devflow_root}/templates/uat-plan.md`: one acceptance case per REQ-ID in REQUIREMENTS.md (steps a human can follow, observable expected result) + one per `SC-NN` success criterion + the smoke section. An SC case states its **threshold and how it was measured** — the number is the pass condition, so "felt fast" is not a result. SCs `/flow-harden` already measured carry that evidence forward for confirmation rather than re-testing; SCs it marked *deferred to UAT* are judged here for the first time. Also list any `unverified` backstop truths from the phases' VERIFICATION.md files: behavior nobody has pinned down is exactly what a human should exercise against a real deployment. Web UI → fill the Route sweep table with the app's key routes (grep the router/pages, ≤15 rows). Set round = previous+1, sha = `git rev-parse HEAD`.

3. **Deploy** per the reference: `azd env list` → PIPELINE says uat unprovisioned or env absent → `azd init` (if needed), `azd env new uat`, `azd env select uat`, `azd up` (azd prompts the user for parameters/secrets — let it). Already provisioned → `azd env select uat`, then `azd provision` only if the AppHost/infra model changed since the last uat deploy (check git diff on AppHost project), then `azd deploy`.

4. **Post-deploy**: capture endpoint URLs from azd output into UAT-PLAN frontmatter and PIPELINE.md; curl the health endpoints (smoke). **Readiness, not sleeps**: poll the health endpoint until healthy or a deadline (~3 min) — never fixed sleeps; report the failure the moment it's definitive. Web UI → run the **route sweep**: load each Route-sweep row against the live UAT URL (headless browser when available — capture console errors and failed network requests; else curl status + body sanity) and fill the table — a console error or failed request fails the row even if the page renders. Update the PIPELINE uat row (SHA, date, result). Deploy or smoke failure → apply the reference's failure table; fixes go through `/flow-quick`; then redeploy.

5. **Acceptance**: hand the user the UAT plan with live URLs; offer to walk through it case by case. Record pass/fail per case in UAT-PLAN.md.
   - **All pass** → write `.planning/deploy/SIGNOFF.md`: approver (ask who), date, `sha`, round, result summary, `approved-for-production: true`. Say: `Next: /flow-release`.
   - **Any fail** → set UAT-PLAN result: failed, NO sign-off. Route each failure: requirement gap → `/flow-plan N --gaps`; defect → `/flow-quick` or `/flow-debug`. After fixes: re-run `/flow-uat` (new round, new sign-off — sign-off is per-SHA).

After a successful deploy, offer the monitoring recipe: `/loop 15m curl the UAT health endpoints and report any change`. The acceptance walkthrough and sign-off are always human-gated — never record results or write SIGNOFF.md autonomously.

Commit docs: `chore(flow): uat round N`; prepend a `.planning/JOURNAL.md` line — round, result (format `{devflow_root}/templates/journal.md`; create if missing).

End with the status line per `{devflow_root}/references/autonomy.md` — deployed, awaiting acceptance: `FLOW: GATE | uat round N deployed, acceptance pending | next: walk UAT-PLAN.md`; signed off: `CONTINUE | next: /flow-release`; failures: `CONTINUE` toward the fix route.
