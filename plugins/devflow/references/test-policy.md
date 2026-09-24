# Test policy (agent work)

**Status:** Standing DevFlow reference for Special Projects / AutomationHub–style product work.
**Lead rationale:** Birgitta Böckeler (Thoughtworks) on martinfowler.com — classic unit-TDD fully inside the agent loop showed no clear quality/mutation win and often invited "TDD theater" (announce test-first, implement, skip/fake red). Prefer outcome sensors and behavior proof over process rituals.

## Defaults

1. **Do not encode classic unit-TDD as the agent default.** Do not spend the loop on red-green-refactor micro-units unless the change is pure logic (below).
2. **Prefer behavior / integration / API-level tests as the feedback driver** for anything that crosses a boundary: HTTP, DB, queue/bus, file, external API, multi-component Aspire graph.
3. **Thin unit layer only:**
   - Pure functions (pricing math, parsers, checksums, predicate evaluation, deterministic state transitions).
   - **Regression pins** after a real defect (minimal failing unit that locks the bug).
4. **Forbidden — coverage theater:** After implementation is already green, do not add unit suites whose primary purpose is raising line/branch coverage, asserting non-null, or restating the implementation.
5. **TDD-ish loops (when used):** Prefer a **failing integration / acceptance / behavior test first** (one AC or one must_have truth), confirm it fails for the right reason, implement until green, then add thin units only if pure logic appeared. Freeze the behavior test — do not edit it to cheat.
6. **Do not invent unit tests for:** wrappers, DTO/record mapping with no rules, pass-through glue, generated clients, or "constructor took dependencies" checks.
7. **Proof:** A claim that tests passed needs a **command that ran + exit/key output**. Align with Outer Loop proof bar when this repo is under Outer Loop: CI green on tip, harness honesty, human merge GO — **never auto-merge**.

## How this interacts with verification

- Phase truths should usually be proven by **running behavior** (integration/API/Smoke) or tracing a wired path — not by counting new `*Tests.Unit` files.
- `ARCHITECTURE.md ## Smoke` remains the standing end-to-end gate (`references/verification.md`). Do not replace Smoke with a large new unit suite.
- Fixture-only or coincidental-reliance greens stay advisory/GAP per `references/verification.md` — especially over-mocked boundaries.

## SP / AutomationHub notes

- Prefer tests that exercise real-ish boundaries (test DB, emulator, WebApplicationFactory, Aspire testing) over mocking every collaborator.
- Live/external systems (e.g. ICE) stay opt-in / trait-gated; never silent-skip to false green.
- AccountChek remains VOIE+VOA only where that product split applies — do not expand scope via tests.
