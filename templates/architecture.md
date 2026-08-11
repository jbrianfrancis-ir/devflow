<!-- .planning/ARCHITECTURE.md — cap 3KB. HARD constraints, owned by the human.
Agents must use exactly what's listed (no substitutes, no silent upgrades);
anything needed outside this file is a checkpoint:decision, never an improvisation. -->
# Architecture constraints

## Stack
| What | Exactly | Version |
|------|---------|---------|
| Runtime | {e.g. .NET} | {e.g. 9.0} |
| Language | {e.g. C#} | {13} |
| Orchestration | Aspire | {13.4.x} |
<!-- Aspire: within-major updates auto-apply (13.4.5→13.4.6, 13.3→13.4); a major bump (13→14) needs approval.
     Pin what the feed actually has — `dotnet package search Aspire.Hosting.AppHost --exact-match` — not the example above. -->



## Frameworks & libraries
| Library | Version | Use for |
|---------|---------|---------|
| {e.g. EF Core} | {9.0.x} | {data access} |
| {e.g. xUnit} | {2.9.x} | {tests} |

## Architecture & patterns
- {e.g. vertical slice per feature; API in Minimal APIs; no MediatR}
- {project layout rules: solution structure, naming}

## Infrastructure (Azure / Aspire resources)
- {e.g. PostgreSQL Flexible Server via AddAzurePostgresFlexibleServer; Redis for cache; Key Vault for secrets}

## Environment (names only — never values)
| Var / parameter | Source | Used by |
|-----------------|--------|---------|
| {e.g. POSTGRES_PASSWORD} | {azd parameter (secret) / Key Vault / .env.example (local) / CI secret} | {service} |

**Fail fast — no fallback values.** Every setting/env var here is required unless marked `(optional, default: X)`. Code must not silently default a required value (`?? "..."`, `os.environ.get(k, default)`, `GetValueOrDefault`, empty-string coalescing) — validate at startup and fail immediately with an error naming the missing key (e.g. options validation / `ValidateOnStart`).
<!-- Discovery never opens .env* files: names come from code accessors and .env.example.
/flow-harden audits code references against this list; values live in azd/Key Vault, never the repo. -->

## Forbidden
- {libraries, patterns, or shortcuts explicitly not allowed}
