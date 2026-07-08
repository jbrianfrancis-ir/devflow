# Aspire + azd (Azure) cheatsheet

Flow deploys via the Aspire app model: the AppHost is the single source of truth for services, resources, and infrastructure, and azd derives Azure infra (Container Apps by default) from it. Auth and secrets are the human's job; commands are the agent's. Docs: https://aspire.dev · https://learn.microsoft.com/azure/developer/azure-developer-cli

## Detection
- AppHost: `Glob **/*.AppHost/*.csproj`, or grep `Aspire.Hosting.AppHost` across csprojs, or a single-file `apphost.cs`.
- ServiceDefaults wired: grep `AddServiceDefaults` / `MapDefaultEndpoints` in service projects.
- CLIs: `aspire --version`, `azd version`. Missing → the user installs (aspire.dev quickstart; azd: https://aka.ms/azd).

## No AppHost? Create one (first hardening task)
`aspire new` (or `dotnet new aspire-apphost` + `dotnet new aspire-servicedefaults`), then in AppHost: `AddProject`/`AddContainer` for each existing service; `AddAzure*` resources for every external dependency (Postgres → `AddAzurePostgresFlexibleServer`, Redis → `AddAzureRedis`, storage, service bus, Key Vault). Each service: `builder.AddServiceDefaults()` + `app.MapDefaultEndpoints()`. Gate: `aspire run` works locally.

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
Parameters, not literals: `builder.AddParameter("name", secret: true)` in the AppHost → azd prompts and stores per-environment; secrets go to Key Vault, never code or appsettings. Per-env values: `azd env set KEY value`.

## Hardening checklist (audit before UAT)
- [ ] AppHost models every service AND every external resource (DB, cache, storage, queues)
- [ ] ServiceDefaults in every service: health endpoints (`/health`, `/alive`), OpenTelemetry, HTTP resilience
- [ ] No secrets or environment-specific literals in code/config — parameters/Key Vault; no hardcoded localhost URLs outside the AppHost
- [ ] `aspire publish` succeeds
- [ ] Telemetry has a destination in cloud (Application Insights / OTLP endpoint), not just the local dashboard
- [ ] Tests pass; CI (if present) runs build + tests

## Failure → fix
- `azd up` Bicep errors → usually resource-name conflict or region: `azd env set AZURE_LOCATION <region>`, rename resource.
- Container build fails → build the service locally; inspect `aspire publish` artifacts.
- Health check red after deploy → container logs (`azd monitor` / portal); usually a missing environment parameter.
- Auth errors mid-flow → `azd auth login` again (token expiry); never store credentials in the repo.
