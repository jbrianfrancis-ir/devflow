# Aspire + azd (Azure) cheatsheet

Flow deploys via the Aspire app model: the AppHost is the single source of truth for services, resources, and infrastructure, and azd derives Azure infra (Container Apps by default) from it. Auth and secrets are the human's job; commands are the agent's. Docs: https://aspire.dev · https://learn.microsoft.com/azure/developer/azure-developer-cli

## Version policy
Aspire updates **within the current major** apply automatically — bump the package references (`Aspire.*` in AppHost/ServiceDefaults, or `Directory.Packages.props` under central package management) to the latest within-major, e.g. 17.0.0 → 17.0.1 or 17.0 → 17.1. `aspire update` (and `aspire update --self` for the CLI) is the supported way to move a repo's packages; edit the refs by hand where it isn't available. Verify with restore + `aspire publish` (and `aspire --version`). **Do not touch `.planning/ARCHITECTURE.md`**: it records `Aspire 17.x`, the exact version lives only in the package refs, and a within-major bump is no deviation and no warning (conventions.md → Dependency versions). A **major** bump (e.g. 13 → 17) is never automatic: raise a `checkpoint:decision` with the breaking-changes/changelog link and wait for approval.

**A minor is not automatically a safe bump.** Aspire ships breaking changes in minor releases (13.5 renamed `ServiceProvider` to `Services` on hosting context types, obsoleted `PublishAsConnectionString`, and removed `aspire ps --resources`). Auto-apply still stands — but read the release notes' *Breaking changes* section, and treat a restore or `aspire publish` failure after the bump as a `CHECKPOINT`, never as something to route around by pinning back to a neighbouring version.

**Aspire 17 (the 13 → 17 major; there is no 14–16).** After approval, `aspire update --self` then `aspire update`: it bumps inline `#:package`/`#:sdk` versions and writes `"sdk": {"version": …}` into `aspire.config.json`. Then by hand ([breaking changes](https://aspire.dev/whats-new/aspire-17/)):
- `Aspire.AppHost.Sdk` is obsolete (ASPIRE012) and `aspire update` leaves it in place. Use `Microsoft.NET.Sdk` + a `Aspire.Hosting.AppHost` PackageReference (file-based AppHost: `#:package Aspire.Hosting.AppHost@<ver>` instead of `#:sdk`). Add `Aspire.Hosting.Dotnet` only when the AppHost has .NET project resources. C# AppHosts need the CLI bundle (ASPIRE013).
- `AddProject<T>` and `AddCSharpApp` are obsolete: use `AddDotnetProject(name, path)` from `Aspire.Hosting.Dotnet`.
- Required parameters reject empty values (`MissingParameterValueException`), so a "leave it blank" path needs `.AsOptional()` (Environment config below).
- Retired experimental diagnostics (e.g. ASPIREJAVASCRIPT001, ASPIREAZURE001, ASPIREPIPELINES001): delete their suppressions. The AppHost minimum is .NET 10. New ServiceDefaults use OpenTelemetry 1.18, whose default OTLP max request is 64 MiB.
- Proof: `aspire publish` with the old and the new CLI, `diff -r` the two outputs, and confirm generated Azure resource names still match the live resource group before any deploy. A trial CLI installed with `install.sh --install-path <dir>` keeps deploy state under `<dir>/../deployments`, so it starts with an empty cache: copy the real `~/.aspire/deployments/<hash>/` files in to prove the new version reads them. `aspire start`, `aspire describe` and `aspire stop` run and inspect an AppHost without a TTY.

**Resolve the current version from the feed, never from this file.** Every version number here is illustrative and goes stale between DevFlow releases — treat them as format examples, not as targets. Before bumping, ask the feed what exists:
```
dotnet package search Aspire.Hosting.AppHost --exact-match --take 5
curl -s https://api.nuget.org/v3-flatcontainer/aspire.hosting.apphost/index.json   # every published version
aspire --version                                                                   # the installed CLI
```
Latest stable when this was last checked: **17.0.0** (released 2026-11-17; release notes at https://aspire.dev/whats-new/aspire-17/). A version a document mentions but the feed doesn't carry is not a near-miss to route around — per the executor's package rule, a package that can't be found is a `CHECKPOINT` (human-action), never a retry with a neighbouring version.

## Detection
- AppHost: `Glob **/*.AppHost/*.csproj`, or grep `Aspire.Hosting.AppHost` across csprojs, or a single-file `apphost.cs`.
- ServiceDefaults wired: grep `AddServiceDefaults` / `MapDefaultEndpoints` in service projects.
- CLIs: `aspire --version`, `azd version`. Missing → the user installs (aspire.dev quickstart; azd: https://aka.ms/azd).

## No AppHost? Create one (first hardening task)
`aspire new` (or `dotnet new aspire-apphost` + `dotnet new aspire-servicedefaults`), then in AppHost: `AddDotnetProject`/`AddContainer` for each existing service; `AddAzure*` resources for every external dependency (Azure SQL → `AddAzureSqlServer`, Postgres → `AddAzurePostgresFlexibleServer` (EF Core 11: pin Npgsql at its current rc until stable), both on managed identity; Redis → `AddAzureRedis`, storage, service bus, Key Vault). Each service: `builder.AddServiceDefaults()` + `app.MapDefaultEndpoints()`. Gate: `aspire run` works locally.

## Build gate
`aspire publish` — generates deployment artifacts from the AppHost model. Must succeed before any deploy; failures are hardening findings.

## Environments (uat, prod)
```
azd auth login --check-status        # gate: user logs in if needed
azd env list                         # what exists already
# first deploy to an environment:
azd init                             # once per repo; detects the AppHost
azd env new <name> && azd env select <name>
azd up                               # provision (infra derived from AppHost) + deploy
# subsequent deploys:
azd env select <name>
azd provision                        # only if the infra model changed since last deploy
azd deploy
```
`aspire deploy` is the newer front-door for the same flow — fine where available; azd is the reliable path. Endpoint URLs: from `azd up`/`azd deploy` output or `azd env get-values` — record them in PIPELINE.md.

## Environment config
Parameters, not literals: `builder.AddParameter("name", secret: true)` in the AppHost → azd prompts and stores per-environment; secrets go to Key Vault, never code or appsettings. Per-env values: `azd env set KEY value`. Genuinely optional config (a switch that may be unset) uses `.AsOptional()` (Aspire 17+): unset resolves to null and the env var is omitted, so the consumer branches on absent. Never make a credential optional to dodge the required check.

## Hardening checklist (audit before UAT)
- [ ] AppHost models every service AND every external resource (DB, cache, storage, queues)
- [ ] ServiceDefaults in every service: health endpoints (`/health`, `/alive`), OpenTelemetry, HTTP resilience
- [ ] No secrets or environment-specific literals in code/config — parameters/Key Vault; no hardcoded localhost URLs outside the AppHost
- [ ] Every env var / parameter name referenced in code appears in ARCHITECTURE.md's Environment section (names only, provisioning source recorded); the secret scan (`conventions.md`) over the branch diff is clean
- [ ] No silent fallbacks on required settings (`?? "..."`, `os.environ.get(k, default)`, `GetValueOrDefault`) — required values fail fast at startup naming the missing key; defaults only on settings the Environment section marks optional
- [ ] `aspire publish` succeeds
- [ ] Telemetry readiness: every deployed service emits traces, metrics and logs to a workspace-based Application Insights that actually exists and is wired to it — the checkable bar, and the `telemetry-readiness` skill that grades it, are in `{devflow_root}/references/telemetry-readiness.md`. A local dashboard is not a destination
- [ ] Tests pass; CI (if present) runs build + tests

This checklist covers the code and the build. The hosting posture around a deployed app — edge geo-filter, WAF, identity on every request, private data stores, audit logging, tested restore, minimum capacity, monitoring — is the separate, explicit-only `/flow-prod-readiness` review (`{devflow_root}/references/prod-readiness.md`), run once per app before go-live and after major infrastructure changes; `/flow-harden` neither runs nor requires it.

## Failure → fix
- `azd up` Bicep errors → usually resource-name conflict or region: `azd env set AZURE_LOCATION <region>`, rename resource.
- Container build fails → build the service locally; inspect `aspire publish` artifacts.
- Health check red after deploy → container logs (`azd monitor` / portal); usually a missing environment parameter.
- Auth errors mid-flow → `azd auth login` again (token expiry); never store credentials in the repo.
