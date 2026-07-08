<!-- .planning/DESIGN.md — cap 2KB. HARD design constraints, linked from Claude Design (claude.ai/design).
UI work uses these tokens and components exactly — no invented styles, colors, or one-off components.
Additions/changes to the design system are a checkpoint:decision, then updated in Claude Design, then re-pulled. -->
---
project: {Claude Design project name}
projectId: {uuid}
pulled: {YYYY-MM-DD}
local: {repo path the design system is pulled into, e.g. design-system/}
---
# Design constraints

## Tokens
{distilled: colors (semantic names + values), type scale, spacing scale, radii, shadows — one line each}

## Components (by group)
{group}: {component names} — specs in {local}/{path}
<!-- one line per group; executors Read the local spec file before building that component -->

## Rules
- {e.g. dark-mode required; density; accessibility floor (WCAG AA); motion rules}
