# Production readiness

The platform bar a deployed app has to clear before real users reach it. AI-assisted builds reliably produce working code; what nobody prompts for is the hosting posture around it — the edge, the firewall, identity on every request, a database nobody can reach from the internet, and the operational basics that let someone other than the builder run it. This reference is the checklist `flow-prod-readiness` grades, and the evidence each item needs. Source: Mike Anderson's LinkedIn post on what vibe-coded apps miss in production (credited in `docs/acknowledgements.md`).

## When it runs
- **Once per app before its first go-live.**
- **Again after a major infrastructure change**: a new or removed edge (Front Door, Application Gateway, CDN), a WAF policy change, a region or environment move, a new data store, a change to how identity is enforced, a network change (VNet, private endpoints, ingress), or a new hosting platform.
- **Never per PR.** No routing rule sends a run here and no other skill calls it. It is explicit-only (`disable-model-invocation: true`).

## Rules that outrank every item
1. **Three results only: `pass`, `gap`, `unknown`.** A check that did not run is `unknown`, never `pass`; absence of evidence is never `gap` either. An item that genuinely does not apply (no database at all) is `pass` with `N/A —` and the reason as its evidence.
2. **Read-only.** No `az login`, no `az account get-access-token`, no Azure, Entra or network writes, no role or permission changes (including your own), no tool installs, no repo edits except the one report named under Delivery. Use an `az` session only if one is already signed in.
3. **Never print or store a secret value.** Secret findings are counts and file paths. `az` projections are names-only: never `--show-values`, never `az containerapp secret show`, never `azd env get-values`, never a projection that returns container `env` arrays, `value`, `connectionString`, or keys. Never open `.env*`, user-secrets, or deployment-state files.
4. **Live traffic is ordinary traffic.** A handful of unauthenticated `GET`/`HEAD` requests (root, one protected page, one API route, the health route). No scanners, no crawling, no load, no attack payloads, no credentials sent.
5. **Repo claims are cache, not evidence** (`{devflow_root}/references/autonomy.md` → External state is a cache). A runbook can explain an `unknown`; it cannot turn one into a `pass`.
6. **Every item has an owner** (below). Azure, Entra and network changes are always the platform owner's — never DevFlow's, never an executor task.

## Owners
| Owner | Means | How a gap gets fixed |
|-------|-------|----------------------|
| `app team` | the app's own code, AppHost, or repo config | ordinary `/flow-quick` or `/flow-plan` work after a human decides |
| `platform owner (human)` | Azure, Entra, or network configuration: edge, WAF, firewall, private endpoints, auth settings, backup policy, replica counts, alert routing, role assignments | the person who administers that subscription or tenant makes the change; DevFlow reports and re-checks only |
| `both` | a code half and a platform half (for example audit logging: the app writes the events, the platform keeps them) | each half is listed in the next step with its own owner |

## The checklist
| ID | Item | `pass` needs | Repo evidence | Platform / live evidence (read-only) | Default owner |
|----|------|--------------|---------------|--------------------------------------|---------------|
| R1 | **Geo-filter at the edge** | traffic from outside the countries the app serves is dropped before it reaches the app, and the app's origin cannot be reached around the edge | infra-as-code for an edge with a geo-match rule; origin restrictions | response headers on a plain `GET` (`x-azure-ref` → Front Door; an App Gateway or CDN header); `az afd profile list`, `az network front-door waf-policy show --query "customRules.rules[].{name:name,vars:matchConditions[].matchVariable}"`; `az containerapp show --query "properties.configuration.ingress.ipSecurityRestrictions[].name"` | platform owner |
| R2 | **WAF with OWASP rules in front of the app**, plus a **false-positive check** | a WAF policy with a managed OWASP/DRS rule set in Prevention mode sits on the path real users take, the origin is locked to it, and a documented false-positive check shows ordinary user text is not blocked | infra-as-code for the WAF policy and its exclusions; a recorded false-positive test result | WAF policy `--query "{mode:policySettings.mode,state:policySettings.enabledState,sets:managedRules.managedRuleSets[].{type:ruleSetType,ver:ruleSetVersion}}"`; headers on a plain `GET` | platform owner (rules), app team (test cases) |
| R3 | **Identity gating every request, not just the login page** | an unauthenticated request to any page or API route other than an explicit allowlist (health, static assets, the sign-in callback) gets a sign-in redirect or `401`/`403`, never data | default-deny auth: a fallback authorization policy, global middleware whose matcher covers every route including `/api`, or platform auth set to reject unauthenticated callers; list every `AllowAnonymous` / excluded matcher | plain unauthenticated `GET` to one protected page (expect `302` to the identity provider or `401`) and one API route (expect `401`/`403`/redirect, never `200` with data); `az containerapp auth show --query "{enabled:platform.enabled,unauth:globalValidation.unauthenticatedClientAction}"` | app team (middleware), platform owner (Entra app, platform auth) |
| R4 | **Database with no public IP or public network access** | every data store the app uses (SQL, PostgreSQL, Cosmos DB, Storage, Redis) has public network access disabled and is reached over a private endpoint or VNet | AppHost / infra resources; how connection settings are resolved | `az sql server list --query "[].{name:name,public:publicNetworkAccess}"`, `az postgres flexible-server list --query "[].{name:name,public:network.publicNetworkAccess}"`, `az cosmosdb list --query "[].{name:name,public:publicNetworkAccess}"`, `az storage account list --query "[].{name:name,public:publicNetworkAccess}"`, `az network private-endpoint list --query "[].name"` | platform owner |
| R5 | **Secrets never in code** | no credential material in the tracked tree or its history; secrets come from Key Vault, platform secrets, or managed identity | the `conventions.md` secret-scan pattern set run over the whole tracked tree with `grep -cE` / `grep -lE`, plus `git ls-files` for tracked `.env*`, `*.pem`, `*.pfx`, `*.key`; report **counts and paths only** | — (values are never fetched) | app team; rotation of anything found is the platform owner's |
| R6 | **Audit logging that answers who accessed what and when** | each read or change of protected data logs the user's identity, the action, the record or scope, and a timestamp, to a store the app cannot rewrite, kept long enough for the app's audit needs | structured log calls that carry the user identity on data access; where they are sent | `az monitor log-analytics workspace show --query "{retention:retentionInDays}"`; `az monitor diagnostic-settings list --resource <db id> --query "[].name"` | both |
| R7 | **Backups with a tested restore** | automated backups are on with known retention, and a restore has actually been performed and recorded (date, target, result) within the last six months | a runbook or log entry recording the last restore test | `az sql db str-policy show`, `az postgres flexible-server show --query "{days:backup.backupRetentionDays,geo:backup.geoRedundantBackup}"` | platform owner (policy, restore test), app team (record) |
| R8 | **Minimum capacity and graceful shutdown** | user-facing services do not scale to zero unless a recorded decision accepts the cold start; on `SIGTERM` the app stops taking new work and finishes in-flight requests within the platform's grace period; readiness and liveness probes exist | host shutdown timeout, `SIGTERM` handling in Node services, health endpoints, probe definitions in infra | `az containerapp show --query "{min:properties.template.scale.minReplicas,max:properties.template.scale.maxReplicas,grace:properties.template.terminationGracePeriodSeconds,probes:properties.template.containers[].probes[].type}"` | app team (shutdown, probes), platform owner (replicas) |
| R9 | **Monitoring someone other than the builder can read** | alerts exist for availability and errors, route to a group that includes someone other than the builder, and that person has read access to the logs and dashboards | runbook naming who is on the receiving end | `az monitor metrics alert list --query "[].{name:name,enabled:enabled}"`, `az monitor scheduled-query list --query "[].{name:name,enabled:enabled}"`, `az monitor action-group list --query "[].{name:name,emails:length(emailReceivers)}"`; `az role assignment list --scope <workspace id> --query "length(@)"` (counts, not identities) | platform owner |

## The false-positive check (R2)
A WAF tuned only by its default rules will block real users saving ordinary text — names with apostrophes, quoted phrases, notes that mention SQL words. The check is a **test plan**, run by a human or in a non-production environment with the owner present, never fired at production by this skill:
1. List the app's free-text save paths (notes, comments, names, addresses, descriptions).
2. Save one record per path containing ordinary text such as `O'Brien`, `the "Smith" account`, `it's 5' 11"`, `select one option & continue`, `<3 thanks`.
3. Confirm each save succeeds and the text reads back unchanged.
4. Read the WAF log for the test window: any block on those requests is a false positive; record the rule ID and the narrowest exclusion that clears it.
5. Record date, environment, paths tested, and result. No record → R2 cannot be `pass`.

## Report format
One table, one row per item, in ID order, then the unknowns and the evidence notes:

```markdown
## Production readiness — <app> (<env>) — <date>
Commit: <sha>  ·  URL: <url>  ·  az session: signed in | not signed in

| ID | Item | Result | Evidence | Owner | Next step |
|----|------|--------|----------|-------|-----------|
| R1 | Geo-filter at the edge | gap | ... | platform owner (human) | ... |

Unknowns: <ids and what access or record would settle each>
Secrets: <count> files with pattern hits, <count> tracked secret-type files (values never printed)
```

Summary line: `N pass · N gap · N unknown`. Gaps first in the next-steps list, ordered by exposure (public reachability of data beats operational polish).

## Delivery per harness
- **DevFlow**: write `.planning/deploy/PROD-READINESS.md` (or `--out`). The human decides whether to commit it.
- **GSD**: write `.planning/PROD-READINESS.md` (or `--out`), nothing else in `.planning/`.
- **Neither**: write to `--out` when given, else print the report.
