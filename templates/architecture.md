<!-- .planning/ARCHITECTURE.md — cap 3KB. HARD constraints, owned by the human.
Agents must use exactly what's listed (no substitutes, no silent upgrades);
anything needed outside this file is a checkpoint:decision, never an improvisation. -->
# Architecture constraints

## Stack
| What | Exactly | Version |
|------|---------|---------|
| Runtime | {e.g. .NET} | {e.g. 9.0} |
| Language | {e.g. C#} | {13} |
| Orchestration | Aspire | {9.x} |

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

## Forbidden
- {libraries, patterns, or shortcuts explicitly not allowed}
