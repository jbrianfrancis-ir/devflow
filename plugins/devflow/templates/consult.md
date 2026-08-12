<!-- .planning/consults/NNN-slug.md — persistent consult state; resumable across sessions.
Bundle + full responses live in .planning/consults/NNN-slug/ (BUNDLE.md, RESPONSE-<model>.md). -->
---
status: draft               # draft | sent | answered | applied | discarded
question: {one line}
engine: cli                 # cli | mcp | manual
models: {model, or csv for a panel}
session: —                  # engine session id for follow-up/collect, or —
parent: —                   # NNN of the consult this follows up, or —
started: {YYYY-MM-DD}
---

## Question
{full question + which decision or stuck point it informs}

## Bundle manifest
| File | Bytes | Why it changes the answer |
|------|-------|---------------------------|
<!-- Excluded (over cap or irrelevant): {list or none} -->

## Verdict
{≤10 lines: recommendation, key reasoning, per-model disagreements, [CONFLICTS: pin] flags, what it would change here — fill when answered}

## Outcome
{applied → what changed + commit/plan/debug ref; discarded → why — fill when closed}
