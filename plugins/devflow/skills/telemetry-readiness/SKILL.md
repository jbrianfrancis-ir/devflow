---
name: telemetry-readiness
description: Check that every deployed service in an Aspire/ACA project emits traces, metrics and logs to a workspace-based Application Insights, and that the Azure sinks exist and are wired to it. Read-only — reports, never fixes. Use at scaffold (advisory), when a service is added, before a PR, and before and after a deploy. Works in DevFlow, GSD and plain repos. Args - --scope code|platform|all, --env <name>, --services <list>.
---

# telemetry-readiness

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

Context rules: read `.planning/STATE.md` first when it exists (absent is fine — this skill needs no `.planning/`); paths not contents.

Read and obey `{devflow_root}/references/telemetry-readiness.md` in full — the checks, the exact commands, the verdict logic, and the output section all live there.

**Read-only, and honest about it.** This skill edits no repo file except the one output file its Delivery section names, makes no Azure write, never runs `az login`, never installs a tool, and never prints a secret value. It reports; fixes are ordinary `/flow-quick` or `/flow-plan` work after a human decides. A check that could not run is `UNVERIFIED` — never `PASS`, and never `FAIL` by absence.

**Pre-flight**
1. **Harness**: DevFlow (`.planning/config.json` has `deploy`) | GSD (`workflow` + a `gsd/phase-*` branch template) | plain. It picks the delivery path, nothing else.
2. **Deploy N/A**: DevFlow `deploy.tool` is explicitly `null` → report `N/A — no deployable surface`, point at the `D-NN` that recorded it, and stop with `FLOW: CONTINUE`. Only an explicit `null` qualifies; a missing or unreadable config means the project deploys (`{devflow_root}/references/autonomy.md`).
3. **Scope**: `--scope` when given. Default `code` from `/flow-pr` and `/flow-verify`; `all` from `/flow-harden`, `/flow-uat`, `/flow-release`. `--env` names the environment a platform verdict belongs to — one verdict per environment, so a uat PASS says nothing about prod.

**Run**
1. **Discover** the AppHost and its publish-mode compute resources per the reference's Target discovery. `--services` narrows the set (a new service from a `/flow-verify` AppHost diff); excluded resources are listed as `N/A (reason)`, never dropped. Resolve resource-group, environment and app names from the repo — never guess one.
2. **Code scope**: C1–C9. Grep to locate, then read the matched file; a commented-out call is an absent call.
3. **Platform scope**: P0–P5, read-only `az` with names-only projections. P0 failing makes every P-check UNVERIFIED and stops the scope there. P4 and P5 can only pass after that environment's first deploy, so on a first-ever deploy they are UNVERIFIED by construction and are re-run post-deploy.
4. **Verdict**: per check `PASS`/`FAIL`/`UNVERIFIED`/`N/A`, tagged `BLOCK` or `WARN`. Overall `PASS` only when every BLOCK check passes in the scopes this moment requires.
5. **Deliver** the `## Telemetry readiness` section per the reference's Delivery section, and append the evidence JSONL. This skill never writes `STATE.md`, `JOURNAL.md`, or `DECISIONS.md` — the calling skill owns those, including the record of any human override of a blocking failure.

End with the status line per `{devflow_root}/references/autonomy.md` (never `DONE` — a readiness check does not finish a project):
- `FLOW: CONTINUE | telemetry-readiness PASS (<scopes>) | next: {the calling skill's next step}`
- `FLOW: GATE | telemetry-readiness FAIL — N blocking (<ids + services>) | next: fix plan, or a human override recorded in DECISIONS.md`
- `FLOW: GATE | telemetry-readiness UNVERIFIED — <what passed>, <what did not run and why> | next: rerun with platform access, or a human approves deploying with UNVERIFIED telemetry`
- `FLOW: CONTINUE | telemetry-readiness N/A — no deployable surface | next: {the calling skill's next step}`
