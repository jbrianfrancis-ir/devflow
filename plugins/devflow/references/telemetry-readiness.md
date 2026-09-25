# Telemetry readiness

The bar every deployed service has to clear: instrumentation **on in code** and a **real sink in Azure**. Two scopes — `code` (checks C1–C9, needs only the checkout) and `platform` (checks P0–P5, needs an authenticated `az`). `all` runs both. Owned by the `telemetry-readiness` skill; called from `/flow-new`, `/flow-verify`, `/flow-pr`, `/flow-harden`, `/flow-uat`, `/flow-release`.

## Rules that outrank every check
1. **A check that did not run is `UNVERIFIED`, never `PASS`.** Absence of evidence never becomes FAIL either.
2. **Read-only.** No `az login`, no Azure writes, no tool installs, no repo edits except the one output file named under Delivery.
3. **Never print or store a secret value.** Every projection excludes `value`, `connectionString`, `instrumentationKey`; never `--show-values`, never `az containerapp secret show`, never `azd env get-values`.
4. **Commented-out code is absent code.** A commented `UseAzureMonitor()` is FAIL.
5. **Repo claims are cache, not evidence** (`{devflow_root}/references/autonomy.md` → External state is a cache). A runbook can explain an UNVERIFIED; it can never turn one into a PASS.
6. **An excluded resource is listed as `N/A (reason)`**, never dropped.
7. **One verdict per environment.** A uat PASS says nothing about prod.
8. Code-scope checks read the files in the **local checkout of the branch under review**, not a code-search index.

## Target discovery
1. **AppHost**: `rg -l "DistributedApplication.CreateBuilder" --glob '*.cs'` (covers `Program.cs`, `AppHost.cs`, single-file `apphost.cs`).
2. **Deployable compute resources**: every `AddProject<…>`, `AddDockerfile`, `AddNextJsApp`, `AddJavaScriptApp`, `AddNodeApp`, `AddViteApp`, plus `AddContainer` resources that are app code. Note resources declared inside `if (builder.ExecutionContext.IsPublishMode)` or its `else` — the deployed set is the **publish-mode** set.
3. **Exclusions, listed**: deploying mocks and test doubles → `N/A (mock)`; third-party-image jobs with no app code (a `curlimages/curl` cron) → `N/A (no app code)`.
4. **Platform names**: resource group from `.planning/deploy/PIPELINE.md`, `azure.yaml`, or repo docs; ACA environment and app names from P1. **Never guess a name** — unresolvable means UNVERIFIED.

## Code scope — C1–C9
Grep to locate, then **read the matched file**. A check is UNVERIFIED in code scope only when the file cannot be located or parsed.

| ID | Check | PASS | FAIL | Sev |
|----|-------|------|------|-----|
| C1 | ServiceDefaults wired in every deployed .NET service (`AddServiceDefaults(`) | every deployed .NET service's `Program.cs` calls it | any deployed .NET service without it | BLOCK |
| C2 | traces + metrics + logs pipelines (`.WithTracing(`, `.WithMetrics(`, `builder.Logging.AddOpenTelemetry(`) | all three present | tracing or metrics missing → BLOCK. **Logs pipeline missing → WARN if P2 PASSes** (ACA console logs still reach Log Analytics), **BLOCK if P2 FAILs or is UNVERIFIED** | BLOCK / WARN |
| C3 | OTLP exporter for dev, gated on `OTEL_EXPORTER_OTLP_ENDPOINT` | gated (Aspire template shape) | absent → WARN (no local dashboard). Ungated `AddOtlpExporter()` → WARN: in ACA it targets localhost and only produces exporter noise | WARN |
| C4 | Azure Monitor exporter for deployed, gated on `APPLICATIONINSIGHTS_CONNECTION_STRING` — package `Azure.Monitor.OpenTelemetry.AspNetCore` (`UseAzureMonitor`) or `Azure.Monitor.OpenTelemetry.Exporter` (`AddAzureMonitor*Exporter`) | package present **and** the call is live code inside a guard on that key. Best practice: pass the read value explicitly, `UseAzureMonitor(o => o.ConnectionString = value)` | no package, or the call is commented out, or it is ungated (ungated crashes local runs) | BLOCK |
| C4b | the exporter covers all three signals (Exporter package only, not the Distro) | trace **and** metric **and** log exporters added | a signal never reaches Azure | WARN |
| C5 | the AppHost forwards the conn string to **every** deployed emitting service — `.WithEnvironment("APPLICATIONINSIGHTS_CONNECTION_STRING", <secret param or App Insights resource>)` or `.WithReference(<AddAzureApplicationInsights resource>)` | every deployed emitting service receives it | exporter code exists but the AppHost never forwards it (dead code in ACA), or some services get it and others do not | BLOCK |
| C5b | the value is supplied safely | secret parameter (`AddParameter…(secret: true)` / `AddParameterFromConfiguration(…, secret: true)`) or a resource output — the emitted bicep uses `secretRef` | plain literal via `WithEnvironment(string, string)`, which bakes the value into ARM deployment history | WARN |
| C6 | `service.name` explicit, `service.version` = the deployed git SHA (`ConfigureResource(r => r.AddService(name, serviceVersion: …))`, or `OTEL_SERVICE_NAME` / `OTEL_RESOURCE_ATTRIBUTES` set per resource in the AppHost, with a SHA source: deploy parameter, build arg, or `SourceRevisionId`) | name explicit and version resolves to the commit being deployed | no version/SHA → FAIL; name left to defaults → WARN | WARN — **promotes to BLOCK when the phase-2 rollout monitor starts**, whose change-scoped verdict correlates on this attribute |
| C7 | health endpoint, and whether it exists in **deployed** environments (`MapDefaultEndpoints()` / `MapHealthChecks(` / explicit routes; any `IsDevelopment()` gate; ACA probes via `WithHttpProbe(`) | a route mapped in deployed envs that returns non-2xx when unhealthy, ideally behind an ACA readiness probe | route only in Development, 200 on dependency failure, or no probe → WARN. **A probe pointing at a path not mapped in deployed envs → BLOCK** (the revision can never become healthy) | WARN / BLOCK |
| C8 | structured logging via `ILogger` → OTel, no Console-only (`Console.Write(Line)?(` outside tests/tools; Serilog in any `.csproj` requires an OTel sink or `writeToProviders`) | `ILogger` with message templates flowing through C2's logging pipeline | app logging via `Console.WriteLine` → WARN. **Serilog with Console-only sinks → BLOCK** (logs never reach App Insights) | WARN / BLOCK |
| C9 | Node/Next.js services instrumented — an OTel SDK or `@azure/monitor-opentelemetry` in the service's `package.json`, an init file, gated on the same env var | instrumented and gated | no telemetry package | WARN |

**Reference shapes to quote rather than invent:** OTLP gated on `OTEL_EXPORTER_OTLP_ENDPOINT` plus `UseAzureMonitor(options => options.ConnectionString = …)` gated on the connection string, in ServiceDefaults; a present-only secret parameter declared **inside** the present-check in the AppHost, so an unset key never creates a missing-value parameter; or App Insights modelled in the AppHost publish-only — `AddAzureLogAnalyticsWorkspace(name)` + `env.WithAzureLogAnalyticsWorkspace(law)` + `AddAzureApplicationInsights(name, law)` + `service.WithEnvironment("APPLICATIONINSIGHTS_CONNECTION_STRING", appInsights)`. New projects default to the modelled form where the AppHost owns the environment, and to the owner-supplied secret parameter where the component is managed outside Aspire.

## Platform scope — P0–P5 (read-only `az`, names only)
Record the exact command and its exit code for every check. Any of these → **UNVERIFIED with the error class and its remediation**, for that check and everything depending on it: `az` missing, P0 fails, `AuthorizationFailed`/403, `ResourceNotFound`/`ResourceGroupNotFound`, a missing extension, throttling, timeout, or a name that could not be resolved.

| ID | Check | Command (projection excludes every value) | PASS / FAIL / UNVERIFIED | Sev |
|----|-------|------------------------------------------|--------------------------|-----|
| P0 | `az` present + authenticated | `az version -o json`, then `az account show --query "{subscription:name, id:id, user:user.name}" -o json` | PASS: both exit 0. Otherwise **every** P-check is UNVERIFIED with the reason (`az not installed` / `not logged in`). Never runs `az login` | BLOCK |
| P0b | extensions present | `az extension show --name containerapp --query version -o tsv`; same for `application-insights` | missing → the dependents are UNVERIFIED with remediation "install extension" (P1/P2/P4 need `containerapp`; P3/P5 need `application-insights`). Never installs it unasked | BLOCK |
| P1 | resolve apps and environment | `az containerapp list -g <rg> --query "[].{name:name, envId:properties.managedEnvironmentId, latestRevision:properties.latestRevisionName, image:properties.template.containers[0].image}" -o json` | PASS: every deployed service maps to an app. An expected app not found → that service's P-checks are UNVERIFIED (name mismatch or not yet deployed), never FAIL | BLOCK |
| P2 | the ACA environment has Log Analytics attached | `az containerapp env show --ids <envId> --query "{destination:properties.appLogsConfiguration.destination, customerId:properties.appLogsConfiguration.logAnalyticsConfiguration.customerId}" -o json`, then `az monitor log-analytics workspace list --query "[?customerId=='<customerId>'].{name:name, id:id, retentionInDays:retentionInDays, sku:sku.name}" -o json` | PASS: destination `log-analytics` with a customerId that resolves to a workspace. destination `azure-monitor` → `az monitor diagnostic-settings list --resource <envId> --query "[].{name:name, workspaceId:workspaceId}" -o json`, PASS if any carries a `workspaceId`. FAIL: destination null/none, or azure-monitor with no workspace destination. UNVERIFIED: the workspace is not visible to this identity | BLOCK |
| P3 | workspace-based App Insights exists | `az monitor app-insights component show --app <name> -g <rg> --query "{name:name, appId:appId, workspaceResourceId:workspaceResourceId, ingestionMode:ingestionMode, retentionInDays:retentionInDays}" -o json` (drop `--app` and prefix the projection with `[]` to list the group) | PASS: exists with `workspaceResourceId` set. PASS + WARN: its workspace differs from P2's (one component per ACA environment on that environment's own workspace is the pattern). FAIL: `workspaceResourceId` null — a classic component. UNVERIFIED: none found or access denied | BLOCK |
| P4 | the deployed app actually carries the conn string (**name only**) | the P4 block below | PASS: every app container of an emitting service has the variable with a `secretRef` whose secret exists. PASS + WARN: `isLiteral: true`. FAIL: the variable is absent on a service C4 says exports — the exporter branch can never be true in ACA. UNVERIFIED: app not found / access denied. Checks the latest template; under multiple-revision mode every active revision | BLOCK |
| P5 | telemetry actually arrived in the last 24h | the P5 block below | PASS: each deployed service has rows, matched by role name. FAIL: a service has zero rows of any type. Scale-to-zero apps can legitimately be silent → UNVERIFIED. UNVERIFIED: query error / access denied. Also reports whether `application_Version`/`AppVersion` carries the SHA | WARN |

**P4** — the projection returns the variable name, its `secretRef`, and a boolean for whether a literal exists. The value is never printed.
```bash
az containerapp show -n <app> -g <rg> -o json --query "properties.template.containers[].{container:name, ai:(env[?name=='APPLICATIONINSIGHTS_CONNECTION_STRING'] | [0]).{name:name, secretRef:secretRef, isLiteral:value!=\`null\`}}"
az containerapp secret list -n <app> -g <rg> -o json --query "[].name"   # names only; never --show-values
```

**P5** — either form:
```bash
az monitor app-insights query --app <name-or-appId> -g <rg> -o json --analytics-query \
  "union requests, dependencies, traces, exceptions, customMetrics
   | where timestamp > ago(24h)
   | summarize rows=count(), last=max(timestamp) by cloud_RoleName, itemType, application_Version"

az monitor log-analytics query -w <customerId> -o json --analytics-query \
  "union AppRequests, AppDependencies, AppTraces, AppExceptions, AppMetrics
   | where TimeGenerated > ago(24h)
   | summarize rows=count(), last=max(TimeGenerated) by AppRoleName, Type, AppVersion"
```

Proving an app points at the *right* component would mean reading the value, which this never does. P4 plus P5 closes that loop instead: rows for the app's role arriving in the expected component is the wiring, end to end. Freeze neither block's syntax without a dry run on a real environment first.

## Verdict
Per check: `PASS` / `FAIL` / `UNVERIFIED` / `N/A (reason)`, each tagged `BLOCK` or `WARN`. Overall, for the scopes the calling moment requires:
- **PASS** — every BLOCK check is PASS.
- **FAIL** — any BLOCK check is FAIL.
- **UNVERIFIED** — no BLOCK FAIL, but at least one BLOCK check is UNVERIFIED. The normal state when `az` is unavailable.

**UNVERIFIED never blocks on its own, and can never produce PASS.** A pre-deploy run whose only gaps are UNVERIFIED goes to the human as a GATE asking for either platform access or an explicit "deploy with UNVERIFIED telemetry" decision. Any BLOCK FAIL stops a pre-deploy gate unless the human overrides; the override is a `.planning/DECISIONS.md` entry, per `{devflow_root}/references/autonomy.md`.

## Output — the PR-body section
```markdown
## Telemetry readiness

**Overall:** UNVERIFIED — code PASS · platform not checked (az not authenticated on runner)
**Commit:** <sha> · **Env:** uat · **Run:** <date time, tz> · **Scope:** all
**Services in scope:** api, frontend · **N/A:** warmup-daily (no app code)

### Code
| ID | Check | Service | Result | Sev | Evidence |
|----|-------|---------|--------|-----|----------|
| C1 | ServiceDefaults wired | api | PASS | BLOCK | <file:line> |
| C6 | service.version = SHA | api | FAIL | WARN | no service.version / OTEL_RESOURCE_ATTRIBUTES found |

### Platform (read-only az)
| ID | Check | Target | Result | Sev | Evidence (command → exit) |
|----|-------|--------|--------|-----|---------------------------|
| P0 | az authenticated | — | UNVERIFIED | BLOCK | `az account show` → exit 1 (not logged in) |
| P2 | ACA env → Log Analytics | <env> | UNVERIFIED | BLOCK | skipped (P0) |

**Blocking:** none failed · **Unverified blocking:** P0, P2, P3, P4
**Warnings:** C6 api (no SHA attribute)
**Overrides:** none
```
Every service in scope gets a row per applicable check; the two tables above are shape, not a subset to copy. Absent rows read as checks nobody ran.

## Delivery per harness
- **DevFlow** (`.planning/config.json` carries `deploy` / `agents` / `git.base`): return the section to the calling skill for the PR body. The caller — never this skill — writes `STATE.md`, `JOURNAL.md`, and `DECISIONS.md`.
- **GSD** (`.planning/config.json` carries `workflow` / `gates` / `git.phase_branch_template`): write `.planning/TELEMETRY-READINESS.md` with the section under a `## Checklist` heading, and nothing else in `.planning/`. The repo picks it up through one `ship.pr_body_sections` entry: heading `Telemetry readiness`, source `TELEMETRY-READINESS.md ## Checklist`, fallback `- Telemetry readiness: NOT RUN — UNVERIFIED` — the fallback is what makes a skipped run visible instead of silently absent. **How a GSD ship step resolves that source path (the `.planning/` root vs the phase directory), and whether the fallback covers a missing file as well as a missing heading, are UNVERIFIED** — confirm both on a repo that already has a `ship` block before adding the entry anywhere, and until then paste the section into the PR body by hand. The skill output is the evidence; GSD is only the delivery path.
- **Neither**: print the section.
- **Evidence** (all harnesses, never committed): one JSONL line per check — id, service, result, severity, command, exit code, evidence path, timestamp — under `~/telemetry-readiness/<repo>/<sha>/checks.jsonl`.
