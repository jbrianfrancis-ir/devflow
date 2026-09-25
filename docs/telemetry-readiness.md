# Telemetry readiness

A deployed service that isn't emitting telemetry doesn't announce itself. It serves traffic, passes its health probe, and tells you nothing when it starts failing — and the gap is usually not "nobody wrote instrumentation": it's an exporter whose connection string never reached the container, an App Insights component that turned out to be classic rather than workspace-based, or a `UseAzureMonitor()` call that got commented out during a local debugging session and stayed that way.

`telemetry-readiness` is the gate that answers that question with evidence instead of assumption. It is read-only: it grades, and never fixes.

## What it grades

Two scopes, each runnable on its own:

- **Code scope** (`C1`–`C9`) needs only the checkout, so it runs anywhere, including pre-PR. ServiceDefaults wired into every deployed service; traces, metrics *and* logs pipelines; the OTLP exporter gated for dev; the Azure Monitor exporter live and gated on `APPLICATIONINSIGHTS_CONNECTION_STRING`; the AppHost forwarding that connection string to **every** deployed emitting service; `service.name` and `service.version`; a health route that exists in deployed environments and fails when the service is unhealthy; structured logging that actually reaches the pipeline; Node/Next.js services instrumented.
- **Platform scope** (`P0`–`P5`) needs an authenticated `az` on the machine running it. The ACA environment has a Log Analytics workspace; the App Insights component exists and is workspace-based; the deployed app carries the connection string; telemetry arrived in the last 24 hours.

The checks, the exact commands, and the severity of each are in [`telemetry-readiness.md`](../plugins/devflow/references/telemetry-readiness.md).

## Verdicts, and why `UNVERIFIED` is a first-class answer

Every check returns `PASS`, `FAIL`, `UNVERIFIED`, or `N/A (reason)`, tagged `BLOCK` or `WARN`. Overall is `PASS` only when every `BLOCK` check passes in the scopes the calling moment requires.

`UNVERIFIED` is the point of the design. A check that couldn't run — `az` absent, not authenticated, access denied, an app that doesn't exist yet — is never `PASS`, and never `FAIL` by absence either. It doesn't block on its own, but it cannot produce an overall `PASS`, so a pre-deploy run whose only gaps are unverified platform checks reaches a human as a `GATE` asking for either platform access or an explicit decision to deploy with telemetry unproven. The decision gets recorded; it never gets assumed.

Two consequences worth stating plainly: a commented-out exporter call is *absent*, not present, and a runbook saying the sink exists is a cache, not evidence — it can explain an `UNVERIFIED`, never upgrade one.

## Where it runs

| Moment | Hook | Scope |
|--------|------|-------|
| Project scaffold | `/flow-new` records the connection-string name and a telemetry `SC-NN` | advisory — usually no service code to grade yet |
| A phase adds a service | `/flow-verify`, when the diff adds an AppHost compute resource | code, limited to the new services |
| Pre-PR | `/flow-pr` writes the `## Telemetry readiness` section into the PR body | code |
| Pre-deploy | `/flow-harden`'s audit, and `/flow-uat` / `/flow-release` before deploying | all |
| Post-deploy | `/flow-uat` / `/flow-release` after the revision is live | platform, `P2`–`P5` |

`P4` and `P5` cannot pass before an environment's first deploy — there is no revision to inspect — so on a first-ever deploy they are `UNVERIFIED` by construction and get re-run once the revision is up. That post-deploy re-run is the only moment they can go green.

Projects with `deploy.tool: null` — a library, CLI, plugin, or docs repo — skip the gate entirely with `N/A — no deployable surface`. Nothing deploys, so there is nothing to instrument for.

## Repos that aren't DevFlow projects

The skill needs no `.planning/` directory. It detects the harness only to decide where its output goes:

- **DevFlow**: the section goes back to the calling skill for the PR body. The caller owns `STATE.md`, `JOURNAL.md`, and `DECISIONS.md` writes — this skill makes none of them.
- **GSD**: it writes one file, `.planning/TELEMETRY-READINESS.md`, with the checklist under a `## Checklist` heading, which a `ship.pr_body_sections` entry pulls into the PR. **How a GSD ship step resolves that source path, and whether its fallback covers a missing file as well as a missing heading, are unverified** — confirm both against a repo that already has a `ship` block before relying on the entry, and until then paste the section in by hand. The skill's output is the evidence; GSD is only delivery.
- **Neither**: it prints the section.

## Relationship to post-deploy rollout monitoring

Readiness is the precondition, not the claim. A future rollout monitor compares a deployment against a baseline and says whether the change regressed anything — and it can only say so for signals that exist. Readiness `PASS` is what makes those signals trustworthy; readiness `FAIL` or `UNVERIFIED` caps any such verdict, carrying the same reason forward rather than relabelling it.

That relationship is also why `C6` — the git SHA stamped as `service.version` — is currently a `WARN` that is expected to become a `BLOCK`. Correlating a deployment to its telemetry by timestamp works until two revisions overlap; correlating it by the commit attribute always works. Nothing depends on it yet, so it warns. The moment change-scoped verdicts depend on it, a missing SHA stops being cosmetic.
