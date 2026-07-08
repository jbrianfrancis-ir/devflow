<!-- .planning/phases/NN-slug/NN-MM-PLAN.md — cap 4KB. A plan is an executor prompt: complete, unambiguous. -->
---
phase: NN-slug
plan: MM
wave: 1
depends_on: []           # plan ids, e.g. [01-01]
files_modified: []       # same-wave plans must not overlap
autonomous: true         # false if any checkpoint task
requirements: [REQ-01]   # never empty
must_haves:
  truths: []             # observable behaviors that prove the goal
  artifacts: []          # files that must exist
  key_links: []          # critical connections ("X calls Y")
---

<objective>{What this plan accomplishes and why — 2 lines.}</objective>

<context>
{Paths only, no contents: .planning/PROJECT.md, .planning/codebase/MAP.md, relevant source files.
Reference a prior plan's SUMMARY only if this plan genuinely uses its outputs.}
</context>

<tasks>
<task type="auto">
  <name>Task 1: {action-oriented name}</name>
  <files>{paths}</files>
  <action>{specific implementation — what to build and how}</action>
  <verify>{command or observable check; human verification goes in <human-check> for end-of-phase batching}</verify>
  <done>{acceptance criteria}</done>
</task>
<!-- type="checkpoint:decision" or "checkpoint:human-action" for human gates -->
</tasks>
