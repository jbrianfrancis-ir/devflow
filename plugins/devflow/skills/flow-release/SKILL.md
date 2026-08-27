---
name: flow-release
description: Deploy to production on Azure, gated on UAT sign-off matching the current commit. Use after /flow-uat sign-off.
---

# flow-release

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

Context rules: read `.planning/STATE.md` first. Production is not the place to improvise — any gate failure stops the release.

**Abort gates** (all must pass):
- `.planning/config.json` → `deploy.tool` is not `null`. **Deploy N/A**: `.planning/config.json` → `deploy.tool` is `null` means this project has nothing to deploy (autonomy.md), so this skill does not apply — say so, point at the `D-NN` that recorded it, and stop with `FLOW: GATE | no deployable surface — /flow-release does not apply | next: /flow-pr` (or `/flow-next` once merged). Only an explicit `null` qualifies; missing or unreadable config means the project deploys.
- `.planning/deploy/SIGNOFF.md` exists with `approved-for-production: true`.
- SIGNOFF `sha` == `git rev-parse HEAD`. Drifted → stop: "HEAD has moved since sign-off — run /flow-uat again." No exceptions; sign-off is per-SHA.
- Working tree clean; `azd auth login --check-status` OK.

1. **Read** `{devflow_root}/references/aspire.md` (Environments, Failure→fix).

2. **Confirm** with the user: releasing SHA {sha}, signed off by {approver} on {date}, to prod. Explicit yes required — this is a permanent human gate: even under `/goal`, `/loop`, or auto mode, stop with a GATE status line and wait.

3. **Deploy**: `azd env list` first — provisioning state is Azure's fact, and the PIPELINE prod row is a cache of it (`autonomy.md` → External state is a cache, never evidence); `/flow-uat` step 3 already reads it live. `azd env list` or PIPELINE says prod unprovisioned → `azd env new prod`, `azd env select prod`, `azd up` (user answers parameter prompts — prod values, not uat). Else `azd env select prod`; `azd provision` only if the infra model changed since the last release; `azd deploy`.

4. **Smoke**: curl prod health endpoints; capture URLs. Failure → present options: rollback (`git checkout <last release tag>` + `azd deploy` from it, or Azure portal revision rollback), retry after fix, or investigate (`/flow-debug`). Do not mark released until smoke is green.

5. **Record**: update PIPELINE prod row (SHA, date, result, URLs); `git tag release-YYYYMMDD-N && git push --tags` (ask before pushing); STATE.md Status: released, Next: next roadmap work or `/flow-status`. Commit docs: `chore(flow): release YYYYMMDD-N`; prepend a `.planning/JOURNAL.md` line — tag, result (format `{devflow_root}/templates/journal.md`; create if missing).

End with the status line per `{devflow_root}/references/autonomy.md` — released: `FLOW: DONE | released YYYYMMDD-N | next: /flow-status`; gate/abort: `GATE` or `BLOCKED` with the reason.
