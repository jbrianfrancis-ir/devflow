# Project questioning

Goal: just enough shared understanding to write REQUIREMENTS.md — not a spec workshop. Max ~5 questions, one round, using the host question mechanism. Ask only what the idea/codebase doesn't already answer; prefer concrete options over open-ended questions.

Cover:
1. **What** — one-sentence description + primary user.
2. **Done looks like** — 3–5 observable behaviors of v1 (these become REQ-NN lines).
3. **Out of scope** — tempting things we are NOT building (write them down; they prevent scope creep later).
4. **Architecture** — the exact stack: runtime, frameworks, and libraries **with versions**, patterns, Azure/Aspire resources, anything forbidden. Most users have this decided — capture it verbatim into ARCHITECTURE.md (hard constraints); record softer preferences as D-NN decisions instead.
5. **Risk** — the part the user is least sure about (candidate for research).

Also cover, briefly, **how good is good enough** — the one or two thresholds that would make the result unacceptable if missed (speed, scale, or a completion rate). They become `SC-NN` success criteria: measurable and technology-agnostic. Most users have a rough number; "no idea yet" is a fine answer and becomes a marker, not an invented figure.

If the user rambles, reflect back a numbered summary and confirm it. Then write requirements as one-liners with acceptance hints — no prose paragraphs. Requirements the user hasn't confirmed are drafts; show them before writing the roadmap.

**One round means unknowns survive the round.** You get ~5 questions; a real project has more open points than that, and the leftovers do not become known by being written confidently. Each one lands in exactly one of three places, never in your head:
- **`[NEEDS CLARIFICATION: <question — 2–4 options>]`** inline in the requirement — the answer would change what gets built, and you must not pick it. This is the default for anything load-bearing.
- **`## Assumptions`** — you chose a sensible default and the project can proceed on it. Write the default you chose, not the fact that you chose one.
- **`## Out of scope`** — the user ruled it out.

Prefer a marker over an assumption whenever being wrong would mean rework rather than an edit. Markers are cheap here and expensive later: unresolved by planning time they become `backstop_truths`, and the verifier abstains rather than certifying a coin-flip.
