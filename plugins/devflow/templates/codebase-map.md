<!-- .planning/codebase/MAP.md — cap 6KB. Memory for planners/executors, not documentation. Overwrite whole file on refresh. -->
---
mapped: {YYYY-MM-DD}
mapped_sha: {full SHA of HEAD when this map was written}
---
<!-- `git diff --name-only <mapped_sha>..HEAD` = what this map has not seen. Never advance either field for a refresh that did not actually run. -->
# Codebase Map

## Stack
{language, framework, key libs + major versions — one line each; exact versions live in the manifests}

## Layout
{annotated tree, depth 2, only dirs that matter}

## Architecture
{how data flows, in ≤10 lines}

## Features
- {user-facing name / where in the UI} → {route} → {entry file}   <!-- ≤15 rows from router/pages/nav; omit section if no UI -->

## Conventions
{naming, error handling, DI, test patterns — what an executor must match}

## Do not copy
- {pattern} — {where} → use {instead}   <!-- omit section if none -->

## Commands
build: {cmd} | test: {cmd} | run: {cmd}   <!-- verified where safe -->

## Env vars
{NAMES only + accessor location — never values; from code accessors and .env.example. Omit section if none.}

## Related repos
- {repo/URL} — {relation: consumes API of / shares contracts / deployed together}   <!-- omit section if none -->

## Gotchas
- {trap: generated dirs, pinned versions, unusual patterns}
