# Execution model

## Context economy
20 shared Agent Skills and 11 subagents across ~220KB of prompt content — but nothing loads it all: skills load progressively at ~1–5k tokens each, and heavy work runs in bounded native subagents or, when explicitly selected, through the other provider's authenticated CLI.

## Graph execution
A phase's plans form a dependency graph — plans are nodes, `depends_on` edges exist only where one plan consumes another's output (the *fake-edge test*), and waves are the graph's parallel layers. Same-wave plans share no files and no mutable resources (a shared migration chain or lockfile is a *hidden edge*). `/flow-execute` fans out one fresh-context executor per plan per wave; a *fan-in guard* counts results against spawns so a dead executor can't slip silently into a "complete" phase; and a fresh-context verifier — never the executors that did the work — proves the phase's `must_haves` against *anchors*: commands actually run, tests actually passed, code traced. must_haves freeze at execution start; gaps close by changing code, never by weakening a truth. Wave arithmetic, the fake-edge test's exact statement, must_haves field lists, and the split signals that force a plan apart are specified in [`plan-format.md`](../plugins/devflow/references/plan-format.md).

## Smoke gate
Per-phase truths only prove *this* phase, which is exactly how phase 5 silently breaks phase 2. So every phase also has to clear one end-to-end check — the command declared in `.planning/ARCHITECTURE.md` → `## Smoke`, run verbatim and judged against its stated pass condition. A failure is a gap even when every phase truth verified, and it's flagged as pointing at earlier work when the evidence says so, so replanning targets the right phase. Undeclared, it becomes a standing human check — the verifier never invents a smoke command and never quietly skips the gate. The abstention rule and the full smoke-gate procedure are specified in [`verification.md`](../plugins/devflow/references/verification.md).

## State
State lives in `.planning/` (hard size caps, sections overwritten not appended — see `plugins/devflow/templates/`). Every skill reads `STATE.md` first, so any session resumes cold. `JOURNAL.md` keeps a capped, newest-first one-line history of skill runs — warm starts, audit trail, and the lines context repos index.

## Docs that don't quietly rot
Planners tell executors to match the conventions in `.planning/codebase/MAP.md`, so a phase that reshapes the codebase and leaves the map alone arms the *next* phase to plan against a codebase that no longer exists. `MAP.md` now carries a `mapped_sha`, which makes staleness computable rather than guessed: at phase close, `/flow-execute` and `/flow-verify` diff `mapped_sha..HEAD` and re-map only on *structural* movement — a new top-level directory or service, a changed manifest or pin, a new env var, a changed build/test/run command. Feature work inside existing structure skips it. If the diff can't be read or the refresh fails, it reports `map: not refreshed` and leaves the date alone: a map that merely looks current is the failure this exists to prevent.

## Conventions
Code lives under `src/` and tests under `tests/` off the repo root, and every change flows through git the same way — a feature branch off `dev` (or `main`), commits pushed to `origin`, integrated by pull request against `upstream` (or the base branch when there's no separate upstream). Deploy runs from merged base code. A **fail-closed secret scan** guards every commit and push (a hit is a human gate — the value is never echoed), and `ARCHITECTURE.md` carries a names-only **Environment manifest** (env vars/parameters + provisioning source; `.env` files are never opened) that `/flow-harden` audits against the code. Aspire updates within the current major apply automatically; a major bump (e.g. 13→14) needs approval. `ARCHITECTURE.md` can override the layout; the git workflow always applies. The exact layout rule, the branch → origin → PR sequence, and the secret-scan pattern are specified in [`conventions.md`](../plugins/devflow/references/conventions.md).

## Architecture constraints
`.planning/ARCHITECTURE.md` (created by `/flow-new`, or write it yourself from `plugins/devflow/templates/architecture.md`) pins your exact stack — runtime, frameworks, and library versions, patterns, Azure/Aspire resources, forbidden items. Planner, plan-checker, executor, and researcher treat it as law: plans pin the listed versions, nothing gets substituted or upgraded silently, and anything outside it surfaces as a decision checkpoint. `/flow-harden` audits for drift between the pins and reality.

## Design constraints
`/flow-design` links a [Claude Design](https://claude.ai/design) design-system project up front (offered during `/flow-new` for UI projects), pulls it into `design-system/`, and distills tokens + component inventory into `.planning/DESIGN.md`. UI plans must name the component and its local spec path; executors read the spec before building; invented styles and one-off components are verification gaps. Missing components route back to the design system via a decision checkpoint, then `/flow-design --refresh`.

## Ship pipeline
No Node runtime and no hooks. "Ship" is a real pipeline: harden → UAT → human sign-off → production, orchestrated with [Aspire](https://aspire.dev) + azd on Azure.
