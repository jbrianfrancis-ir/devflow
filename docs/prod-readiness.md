# Production readiness review

## What it is
`/flow-prod-readiness` is a **read-only** review of the hosting posture around one deployed app: the things an AI-assisted build reliably skips because nobody prompts for them. It grades nine items `pass`, `gap`, or `unknown`, names an owner for each, and writes one report. It never fixes anything.

The checklist comes from Mike Anderson's [LinkedIn post on what vibe-coded apps miss in production](https://www.linkedin.com/posts/mikeanderson0289_vibe-coding-or-just-have-claude-do-it-share-7522046972195815424-MXrB/) — including the lesson that a WAF on default OWASP rules can block real users saving ordinary text.

## When to run it
- **Once per app before go-live.**
- **Again after a major infrastructure change** — new edge, WAF policy change, region or environment move, new data store, a change to how identity is enforced, a network change.
- **Not per PR.** It is explicit-only (`disable-model-invocation: true`): `/flow-next` never routes to it and no other skill calls it.

## The nine items
| ID | Item |
|----|------|
| R1 | Geo-filter at the edge |
| R2 | WAF with OWASP rules, plus a false-positive check (ordinary text with quotes is not blocked) |
| R3 | Identity gating every request, not just the login page |
| R4 | Database with no public IP or public network access |
| R5 | Secrets never in code (counts and paths only, never values) |
| R6 | Audit logging that answers who accessed what and when |
| R7 | Backups with a tested restore |
| R8 | Minimum capacity and graceful shutdown |
| R9 | Monitoring someone other than the builder can read |

What counts as evidence for each, and the read-only commands, are in [`plugins/devflow/references/prod-readiness.md`](../plugins/devflow/references/prod-readiness.md).

## Owners
- `app team` — the app's code or repo config; fixed through ordinary `/flow-quick` or `/flow-plan` work.
- `platform owner (human)` — any Azure, Entra, or network change. DevFlow reports and re-checks; it never makes these changes.
- `both` — split items, with each half's owner in the next step.

## What it will not do
No `az login`, no token minting, no writes to Azure, Entra, or the network, no secret values, no scanners, no load tests, no attack payloads. Live traffic is a few plain unauthenticated `GET`s. The WAF false-positive check is handed over as a test plan for a human to run in a non-production environment. Anything it cannot read is `unknown`, and the run keeps going.

## How it differs from `/flow-harden` and `/flow-security-audit`
- `/flow-harden` audits the **code and build** against the Aspire hardening checklist and fixes what it finds.
- `/flow-security-audit` hunts **vulnerabilities in source** across trust boundaries.
- `/flow-prod-readiness` checks the **platform around the running app** and fixes nothing.
