<!-- .planning/ARCHITECTURE.md — cap 3KB. HARD constraints, owned by the human.
Agents must use exactly what's listed (no substitutes, no silent upgrades);
anything needed outside this file is a checkpoint:decision, never an improvisation. -->
# Architecture constraints

## Stack
| What | Exactly | Version |
|------|---------|---------|
| Runtime | {e.g. .NET} | {e.g. 9.0} |
| Language | {e.g. C#} | {13} |
| Orchestration | Aspire | {13.5.x} |
<!-- Aspire: within-major updates auto-apply (13.5.0→13.5.1, 13.4→13.5); a major bump (13→14) needs approval.
     Pin what the feed actually has — `dotnet package search Aspire.Hosting.AppHost --exact-match` — not the example above. -->



## Principles
<!-- Practice law for THIS project — the rules a plan may not trade away for convenience.
     The stack tables above say what to build with; this says how work is done here.
     Keep 3–6, each testable enough that a reviewer can point at a violation. Delete the rest —
     a principle nobody would enforce is a comment.
     DevFlow's own defaults (src//tests/ layout, dead-code deletion, regression test per bug fix,
     fail-closed guards) already apply everywhere and don't need restating; write only what is
     specific or stricter here. A conflict is resolved by changing the plan, never by reinterpreting
     the principle — if a principle is wrong, amend this file deliberately, as its own decision. -->
- {e.g. No feature merges without an integration test against a real database — mocks don't count}
- {e.g. Every endpoint enforces authorization at the handler; no reliance on gateway filtering}
- {e.g. Public API changes ship behind a version; no breaking change without a deprecation window}

## Smoke
<!-- The one command proving the app still works end to end. Every phase must clear it before
     verification can pass — it catches what per-phase truths cannot: phase 5 breaking phase 2.
     Exercise a real critical path (build + start + one user-visible action), not just compile;
     keep it under ~2 min. None yet → `none (not yet defined)`; the verifier then raises a human
     check rather than inventing a command. -->
- **Command**: {e.g. `dotnet test tests/Smoke` — or `./scripts/smoke.sh`}
- **Pass looks like**: {e.g. exit 0; "8 passed"; health endpoint 200 and /orders renders a seeded order}

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
