<!-- .planning/ARCHITECTURE.md — cap 3KB. HARD constraints, owned by the human.
Agents must use what's listed (no substitutes, no silent major upgrades);
versions are MAJOR only — exact versions live in manifests/lockfiles;
anything needed outside this file is a checkpoint:decision, never an improvisation. -->
# Architecture constraints

## Stack
| What | Exactly | Major |
|------|---------|-------|
| Runtime | {e.g. .NET} | {e.g. 10} |
| Language | {e.g. C#} | {14} |
| Orchestration | Aspire | {13.x} |
<!-- MAJOR VERSIONS ONLY — this table AND `## Frameworks & libraries` below. Write `10`, `13.x`,
     `24 LTS`; never `13.5.1`. The exact version lives only in the manifest/lockfile
     (csproj, Directory.Packages.props, global.json, package.json + lockfile, ...), so a
     minor/patch bump changes the manifest and never this file, and raises no warning. Only a
     major change (e.g. Aspire 13 → 14) is a checkpoint:decision, and then the major here changes.
     A deliberate exact pin must carry its reason — `10.0.3 (exact: <why>)` — and only then
     binds below the major. Every number shown is an illustrative example: resolve the current
     major from its own source (`dotnet --list-sdks`, the vendor's release page,
     `dotnet package search <id> --exact-match`), never from this template.
     Aspire: within-major updates auto-apply; a major bump needs approval. -->



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
     check rather than inventing a command. Smoke is the standing end-to-end gate: never
     substitute a pile of new unit tests for it. -->
- **Command**: {e.g. `dotnet test tests/Smoke` — or `./scripts/smoke.sh`}
- **Pass looks like**: {e.g. exit 0; "8 passed"; health endpoint 200 and /orders renders a seeded order}

## Frameworks & libraries
| Library | Major | Use for |
|---------|-------|---------|
| {e.g. EF Core} | {10.x} | {data access} |
| {e.g. xUnit} | {2.x} | {tests} |

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
<!-- An entry may end with an optional backticked regex, e.g. a bullet ending
" — pattern: `\b[A-Z0-9]{10}\b`". Optional: a prose-only entry stays valid and stays
unenforced — only entries that carry a regex are machine-checked. **Python `re` syntax,
matched case-sensitively** — that is what the guard compiles, so POSIX classes like
`[[:digit:]]` are accepted by the parser and then silently never match. Write `[0-9]`, `\d`.
Keep it simple: a pattern with nested quantifiers (`(a+)+`) backtracks catastrophically and is
blocked as could-not-check rather than run. See conventions.md's "Secret scan (fail-closed)"
section for how the regex gets enforced. -->
