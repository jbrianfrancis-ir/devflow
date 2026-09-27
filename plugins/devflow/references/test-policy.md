# Test policy (agent work)

**Status:** Standing DevFlow reference for Special Projects / AutomationHub–style product work.
**Lead rationale:** Birgitta Böckeler (Thoughtworks) on martinfowler.com — classic unit-TDD fully inside the agent loop showed no clear quality/mutation win and often invited "TDD theater" (announce test-first, implement, skip/fake red). Prefer outcome sensors and behavior proof over process rituals.

## Defaults

1. **Do not encode classic unit-TDD as the agent default.** Do not spend the loop on red-green-refactor micro-units unless the change is pure logic (below).
2. **Prefer behavior / integration / API-level tests as the feedback driver** for anything that crosses a boundary: HTTP, DB, queue/bus, file, external API, multi-component Aspire graph.
3. **Thin unit layer only:**
   - Dense pure logic (pricing/fee math, parsers, checksums, predicate evaluation, deterministic state transitions).
   - **Regression pins** after a real defect (minimal failing unit that locks the bug). Name the defect (issue, PR, incident, quick-task id) in the test.
4. **Forbidden — coverage theater:** After implementation is already green, do not add unit suites whose primary purpose is raising line/branch coverage, asserting non-null, or restating the implementation.
5. **TDD-ish loops (when used):** Prefer a **failing integration / acceptance / behavior test first** (one AC or one must_have truth), confirm it fails for the right reason, implement until green, then add thin units only if pure logic appeared. Freeze the behavior test — do not edit it to cheat.
6. **Do not invent unit tests for:** wrappers, DTO/record mapping with no rules, pass-through glue, generated clients, framework/DI/constructor wiring, "the mock was called" interaction checks, tests that re-implement the code under test inside the test, or source-text greps of your own code (read a `.cs`/`.ts`/`.sql` file and assert a string) when the behaviour can be exercised instead.
7. **Proof:** A claim that tests passed needs a **command that ran + exit/key output**. Align with Outer Loop proof bar when this repo is under Outer Loop: CI green on tip, harness honesty, human merge GO — **never auto-merge**.

## How this interacts with verification

- Phase truths should usually be proven by **running behavior** (integration/API/Smoke) or tracing a wired path — not by counting new `*Tests.Unit` files.
- `ARCHITECTURE.md ## Smoke` remains the standing end-to-end gate (`references/verification.md`). Do not replace Smoke with a large new unit suite.
- Fixture-only or coincidental-reliance greens stay advisory/GAP per `references/verification.md` — especially over-mocked boundaries.

## SP / AutomationHub notes

- Prefer tests that exercise real-ish boundaries (test DB, emulator, WebApplicationFactory, Aspire testing) over mocking every collaborator.
- Live/external systems (e.g. ICE) stay opt-in / trait-gated; never silent-skip to false green.
- AccountChek remains VOIE+VOA only where that product split applies — do not expand scope via tests.

## What every test must protect

A test earns its place only by protecting **current behaviour that matters**. Each kept test (or test class/describe) must be able to finish the sentence *"protects: …"* with one of:

| Protects | Examples |
|---|---|
| Money / pricing / fee math | margin, rate cards, invoice totals, fee rules |
| PII / security | masking, redaction, authn/authz, tenancy isolation, signature verification, secret scrubbing |
| Contract with an outside system | external API request/response shapes, webhook payloads, message envelopes, license/token formats, parity guards against a vendor schema |
| A regression that actually happened | names the defect it pins |
| Dense pure logic | a real algorithm/state machine whose failure a behaviour test would not localise |
| A user-visible behaviour through a real entry point | HTTP endpoint, service method, job, DB round-trip |

If none applies, do not write it. If it already exists, delete it. The "protects" line belongs in the test name or a one-line comment above the class. It is not a separate mapping document.

## Evidence is frozen in git; tests follow the code

- Tests cover the code **as implemented now**. Being cited in a phase `VERIFICATION.md`, UAT plan or security report is **not** a reason to keep a test. The phase commit already freezes that evidence: the test, the code and the command output are recoverable at that SHA.
- VERIFICATION/UAT/SECURITY evidence cites **the command that ran, its result, and the commit SHA**. It does not cite a list of test names that must survive. Never add name-by-name mapping tables between docs and tests.
- When a feature is **removed or replaced**, delete its tests **in the same change**. Optionally add **one line** per affected doc: `Tests cited here last existed at <sha>.` Nothing more.
- When tests are deleted and a real gap is left (behaviour that matters is no longer exercised), replace them with **one** behaviour test through a real entry point. Do not re-grow the unit pile.

## Layout: by behaviour, not by phase

- No per-phase test folders or names (`tests/Phase21/`, `phase-24.1/`, `…Phase13Tests`). Place tests by feature/boundary (e.g. `Api/`, `Pricing/`, `Security/`, `Contracts/`, `Integration/<adapter>/`). A phase adds tests to the folder of the behaviour it changes.
- Name tests for the behaviour (`Quote_total_includes_rack_adjustment`), not the requirement id (`APROG_03_satisfied`).
- One shared test host (WebApplicationFactory/test auth handler/DB fixture) per test project, not one per class.
- Live/credential-gated tests stay opt-in and trait-gated (Default 7 / SP notes). A suite that no CI job runs is either wired into CI or deleted. "Skipped forever" is not a state.

## Pruning checklist (use in `/flow-harden`, `/flow-pr` tests lens, or a dedicated prune)

1. Delete: removed/replaced-feature tests, duplicates (keep the one nearest a real entry point), mirror/tautology, mock-everything, DI/ctor/framework wiring, DTO/constant shape, per-phase scaffolds and stubs, retired source-text checks.
2. Keep, with a "protects:" line: money/fee, PII/security, external contracts, real regressions, dense pure logic, behaviour through real entry points.
3. For each real gap a delete leaves, propose one behaviour test (name + entry point).
4. Stricter bar in a **released** product: do not cut a test that guards live behaviour in the categories above without a replacement. Pre-release products take aggressive cuts.
5. Proof: the before/after command, the test counts and (if measurable) line coverage, each marked measured or estimated.
