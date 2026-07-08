# Project questioning

Goal: just enough shared understanding to write REQUIREMENTS.md — not a spec workshop. Max ~5 questions, one round, via AskUserQuestion. Ask only what the idea/codebase doesn't already answer; prefer concrete options over open-ended questions.

Cover:
1. **What** — one-sentence description + primary user.
2. **Done looks like** — 3–5 observable behaviors of v1 (these become REQ-NN lines).
3. **Out of scope** — tempting things we are NOT building (write them down; they prevent scope creep later).
4. **Architecture** — the exact stack: runtime, frameworks, and libraries **with versions**, patterns, Azure/Aspire resources, anything forbidden. Most users have this decided — capture it verbatim into ARCHITECTURE.md (hard constraints); record softer preferences as D-NN decisions instead.
5. **Risk** — the part the user is least sure about (candidate for research).

If the user rambles, reflect back a numbered summary and confirm it. Then write requirements as one-liners with acceptance hints — no prose paragraphs. Requirements the user hasn't confirmed are drafts; show them before writing the roadmap.
