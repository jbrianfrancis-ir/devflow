<!-- .planning/REQUIREMENTS.md — cap 3KB. One line per requirement. -->
# Requirements

## Must have (v1)
- REQ-01: {user-observable behavior} — accept: {how to check it}
- REQ-02: {behavior} — accept: {check}

<!-- Mark what the user never settled instead of choosing for them:
     - REQ-03: system authenticates users via [NEEDS CLARIFICATION: email/password, SSO, or OAuth?]
     A marker is a question with options, never a shrug. It survives here until answered — /flow-plan
     asks about the ones its phase touches, and any still open when the phase is planned become
     must_haves.backstop_truths so the verifier abstains instead of certifying whatever got built.
     Guessing silently is the one thing this file exists to prevent. -->

## Success criteria
<!-- Measurable and technology-agnostic — a number and a unit, true of the product no matter how it's built.
     These are where performance, scale, and UX thresholds live; nothing else in .planning/ has room for them.
     /flow-harden audits them before deploy and /flow-uat writes an acceptance case per criterion. -->
- SC-01: {e.g. a signed-in user completes checkout in under 2 minutes}
- SC-02: {e.g. the API serves 500 concurrent users with p95 latency under 400ms}
- SC-03: {e.g. 90% of first-time users finish onboarding without help}

## Assumptions
<!-- Reasonable defaults chosen where the description was silent — the guesses this project is standing on.
     Written down they are reviewable and testable; unwritten they are landmines a later phase steps on.
     An assumption too load-bearing to be wrong is not an assumption: make it a REQ or a [NEEDS CLARIFICATION]. -->
- {e.g. users are on modern browsers; IE support is not required}
- {e.g. the existing auth service is reused rather than replaced}
- {e.g. single region deployment; multi-region is out of scope for v1}

## Out of scope
- {explicitly not building}
