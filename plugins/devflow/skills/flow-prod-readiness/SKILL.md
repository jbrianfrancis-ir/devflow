---
name: flow-prod-readiness
description: Read-only production-readiness review of one deployed app's platform posture - edge geo-filter, WAF with OWASP rules plus a false-positive check, identity on every request, private database, secrets out of code, audit logging, tested restore, minimum capacity and graceful shutdown, monitoring others can read. Each item gets pass, gap or unknown and an owner. Run once per app before go-live and again after a major infrastructure change; never per PR. Explicit-only. Args - --app <name>, --url <base url>, --env <name>, --out <path>.
disable-model-invocation: true
---

# flow-prod-readiness

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

Context rules: read `.planning/STATE.md` first when it exists (absent is fine — this skill needs no `.planning/`); paths not contents.

Read and obey `{devflow_root}/references/prod-readiness.md` in full — the nine items, what counts as evidence, the owner rule, and the report format all live there.

**When, and when not.** Once per app before its first go-live, and again after a major infrastructure change (the reference lists what counts). It is **not a per-PR step**: `/flow-next` never routes here, and `/flow-pr`, `/flow-harden`, `/flow-uat` and `/flow-release` do not call it. Only a human typing the command runs it.

**Read-only, and honest about it.** This skill edits no repo file except the one report its Delivery section names. It makes no Azure, Entra or network write, never runs `az login` or `az account get-access-token`, never mints, borrows or widens a credential, never installs a tool, and never prints a secret value — secret findings are counts and file paths only. Live traffic is limited to a handful of ordinary unauthenticated `GET`/`HEAD` requests: no scanners, no load, no attack payloads. An item that could not be checked is `unknown` — never `pass`, and never `gap` by absence.

**Owners.** Every item names an owner. A fix in the app's own code or config is `app team` and goes through ordinary `/flow-quick` or `/flow-plan` work after a human decides. Every Azure, Entra or network change — edge, WAF, firewall, private endpoints, auth settings, backup policy, replicas, alert routing, role assignments — is `platform owner (human)`: the person who administers that subscription or tenant. DevFlow never makes those changes and never plans them as executor tasks.

**Pre-flight**
1. **Harness**: DevFlow (`.planning/config.json` has `deploy`) | GSD | plain. It picks the delivery path, nothing else.
2. **Deploy N/A**: DevFlow `deploy.tool` explicitly `null` → report `N/A — no deployable surface` and stop with `FLOW: CONTINUE`.
3. **Target**: `--app`, `--url` and `--env` when given; otherwise resolve them from `.planning/deploy/PIPELINE.md`, `azure.yaml`, the AppHost, or repo docs. Never guess a name or URL — unresolved means every platform and live check is `unknown`.

**Run**
1. **Repo evidence** for each item per the reference (AppHost, infra files, middleware, health and shutdown handling, logging).
2. **Platform evidence**, only when an `az` session is already signed in: read-only `show`/`list` with names-only `--query` projections. Not signed in, or access denied → those checks are `unknown`; keep going.
3. **Live evidence**: the plain requests the reference allows, against `--url`.
4. **Grade** each item `pass` / `gap` / `unknown` with its evidence, owner and next step. The false-positive half of item 2 is always delivered as a test plan, never executed against production by this skill.
5. **Deliver** the report per the reference's Delivery section. This skill never writes `STATE.md`, `JOURNAL.md` or `DECISIONS.md`.

End with the status line per `{devflow_root}/references/autonomy.md` (never `DONE` — a readiness review does not finish a project):
- `FLOW: CONTINUE | prod-readiness: 9 pass | next: {the project's next step}`
- `FLOW: GATE | prod-readiness: N gap, M unknown (<item ids>) | next: owners act on the report; rerun after fixes or platform access`
- `FLOW: CONTINUE | prod-readiness N/A — no deployable surface | next: {the project's next step}`
