<!-- .planning/codebase/MAP.md — cap 6KB. Memory for planners/executors, not documentation. Overwrite whole file on refresh. -->
---
mapped: {YYYY-MM-DD}
mapped_sha: {full SHA of HEAD when this map was written}
---
<!-- `mapped_sha` makes staleness computable instead of guessed: `git diff --name-only <mapped_sha>..HEAD`
     is exactly the set of changes this map has not seen. Planners tell executors to match the
     conventions recorded here, so a map that silently falls behind teaches the wrong ones.
     Never advance either field for a refresh that did not actually run. -->
# Codebase Map

## Stack
{language, framework, key libs + versions — one line each}

## Layout
{annotated tree, depth 2, only dirs that matter}

## Architecture
{how data flows, in ≤10 lines}

## Conventions
{naming, error handling, DI, test patterns — what an executor must match}

## Commands
build: {cmd} | test: {cmd} | run: {cmd}   <!-- verified where safe -->

## Env vars
{NAMES only + accessor location — never values; from code accessors and .env.example. Omit section if none.}

## Related repos
- {repo/URL} — {relation: consumes API of / shares contracts / deployed together}   <!-- omit section if none -->

## Gotchas
- {trap: generated dirs, pinned versions, unusual patterns}
