<!-- .planning/phases/NN-slug/VERIFICATION.md — cap 2KB. -->
---
phase: NN-slug
status: pass                # pass | gaps | human_needed
smoke: pass                 # pass | fail | undeclared — end-to-end gate, every phase
gaps: []                    # one line each
unverified: []              # backstop truths that abstained — non-inferable, need a held-out test
---

## Smoke
`{command run verbatim from ARCHITECTURE.md ## Smoke}` → {result vs the declared pass condition}
<!-- fail → a gap, even if every truth below VERIFIED; note if the evidence points at an earlier phase.
     undeclared → a human check asking for one; never an invented command. -->

## Truths
| must_have truth | result | evidence |
|-----------------|--------|----------|
| {behavior} | VERIFIED / GAP / HUMAN | {command output, test, or code trace} |
| {behavior} | VERIFIED (coincidental-reliance) | {evidence} — holds only because {the accident} |
| {non-inferable behavior} | HUMAN (non-inferable) | spec doesn't settle this; nothing pins it down |

## Human checks
- [ ] {batched item} — how: {what the user should do/see}
- [ ] {backstop truth} — decide the rule, then write a test that fixes it (or state it in REQUIREMENTS so it becomes inferable)

## Learnings
- {≤3 bullets: only what future phases must know}
