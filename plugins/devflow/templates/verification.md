<!-- .planning/phases/NN-slug/VERIFICATION.md — cap 2KB. -->
---
phase: NN-slug
status: pass                # pass | gaps | human_needed
gaps: []                    # one line each
unverified: []              # backstop truths that abstained — non-inferable, need a held-out test
---

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
