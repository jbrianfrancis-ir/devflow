# Requirements clarity

*Saying "unknown" out loud*

## Confident sentences
An agent asked to write requirements will write confident sentences, because that is what requirements look like. The gap between what the user actually settled and what the document asserts is where silent wrong decisions come from, and DevFlow now refuses to close that gap by guessing.

## Markers, backstop truths, abstention
**`[NEEDS CLARIFICATION: …]`** markers sit inline in `REQUIREMENTS.md` wherever an unsettled choice would change what gets built (`- REQ-03: authenticates users via [NEEDS CLARIFICATION: email/password, SSO, or OAuth?]`). `/flow-plan` asks about the markers its phase touches, before anything it newly noticed; answering one resolves it in place as a D-NN decision. Any still open when the phase is planned become `must_haves.backstop_truths` — tagging rule in [`plan-format.md`](../plugins/devflow/references/plan-format.md) — and the verifier abstains rather than certifying whichever behavior got built, per [`verification.md`](../plugins/devflow/references/verification.md). That is one chain from *the spec didn't say* to *nobody claimed it was right* — with a human asked at each cheap moment along the way.

## Assumptions and success criteria
Two companions in the same file. **`## Assumptions`** records the defaults chosen where the description was silent — written down they're reviewable, unwritten they're landmines; an assumption too load-bearing to be wrong is a requirement or a marker instead. **`SC-NN` success criteria** are measurable and technology-agnostic ("p95 under 400ms at 500 concurrent users", "90% finish onboarding unaided") — the only place a performance, scale, or UX threshold can live. `/flow-harden` audits them before deploy (a number nothing measures is a finding; a human-judged one is deferred, never dropped) and `/flow-uat` writes an acceptance case per criterion, threshold included, since "felt fast" is not a result.

## Cross-artifact audit
**`/flow-audit`** checks the artifacts against each other, read-only and severity-rated: coverage in *both* directions (a plan tracing to no requirement is work nobody asked for), status drift where disk disagrees with ROADMAP or STATE, markers still open on already-executed work, acceptance resting on unmeasurable adjectives, and conflicts with `ARCHITECTURE.md`'s **`## Principles`** — the project's own practice law, where a conflict is resolved by changing the plan, never by reinterpreting the principle.
