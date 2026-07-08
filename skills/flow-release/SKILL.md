---
name: flow-release
description: Deploy to production on Azure, gated on UAT sign-off matching the current commit. Use after /flow-uat sign-off.
---

# flow-release

Context rules: read `.planning/STATE.md` first. Production is not the place to improvise — any gate failure stops the release.

**Abort gates** (all must pass):
- `.planning/deploy/SIGNOFF.md` exists with `approved-for-production: true`.
- SIGNOFF `sha` == `git rev-parse HEAD`. Drifted → stop: "HEAD has moved since sign-off — run /flow-uat again." No exceptions; sign-off is per-SHA.
- Working tree clean; `azd auth login --check-status` OK.

1. **Read** `${CLAUDE_PLUGIN_ROOT}/references/aspire.md` (Environments, Failure→fix).

2. **Confirm** with the user: releasing SHA {sha}, signed off by {approver} on {date}, to prod. Explicit yes required — this is a permanent human gate: even under `/goal`, `/loop`, or auto mode, stop with a GATE status line and wait.

3. **Deploy**: PIPELINE says prod unprovisioned → `azd env new prod`, `azd env select prod`, `azd up` (user answers parameter prompts — prod values, not uat). Else `azd env select prod`; `azd provision` only if the infra model changed since the last release; `azd deploy`.

4. **Smoke**: curl prod health endpoints; capture URLs. Failure → present options: rollback (`git checkout <last release tag>` + `azd deploy` from it, or Azure portal revision rollback), retry after fix, or investigate (`/flow-debug`). Do not mark released until smoke is green.

5. **Record**: update PIPELINE prod row (SHA, date, result, URLs); `git tag release-YYYYMMDD-N && git push --tags` (ask before pushing); STATE.md Status: released, Next: next roadmap work or `/flow-status`. Commit docs: `chore(flow): release YYYYMMDD-N`.

End with the status line per `${CLAUDE_PLUGIN_ROOT}/references/autonomy.md` — released: `FLOW: DONE | released YYYYMMDD-N | next: /flow-status`; gate/abort: `GATE` or `BLOCKED` with the reason.
