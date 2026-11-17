<!-- .planning/DESIGN.md — cap 2KB. HARD UI constraints written by /flow-design: the org brand base (cited, never copied) + this app's brief + tokens. Build to them, never to framework defaults or a ui-design.json template_tell; changes are a checkpoint:decision. -->
---
brand: {canonical brand source: repo path, package, or URL — or [NEEDS CLARIFICATION] brand source}
project: {Claude Design project name, or none}
projectId: {uuid, or none}
pulled: {YYYY-MM-DD}
local: {repo path the design system is pulled into, e.g. design-system/}
---
# Design constraints

## Base
{brand source + version/date; what it supplies (logo, core palette, faces, shared components/tokens) — cite, never copy values}

## Brief
Users: {who, how often, on what screen}. Personality: {3 traits as visual facts per impact.md}. Reference: {named era/style or product, never "modern"}.
Siblings: {app — DESIGN.md path or screenshot — how this one differs, one line each}. Distinct: {accent (within the base's roles), layout, density, hero/dashboard composition}.
Not this: {the template_tells this app avoids, plus any sibling look}

## Tokens
{one line each: palette roles (60/30/10); type: real faces + weights + scale; layout + density: grid, spacing step, row height; radii; elevation}

## Components (by group)
{group}: {component names} — specs in {local}/{path}

## Rules
- {e.g. dark mode; WCAG AA; motion; IMPACT facts, not adjectives; template_tells found in the existing UI}
