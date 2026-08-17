# Phase 01 — Link safety net · Context

## Locked
- **D-07** — The checker validates **backticked repo-relative paths**, not only `[text](target)` links. Measured surface: 619 backticked file refs vs **2** markdown links repo-wide. A syntax-only checker would validate two links and protect nothing this project puts at risk.
- **D-08** — `{devflow_root}/…` refs resolve to `plugins/devflow/…` and are validated. ~80 references, currently unprotected by anything; this also catches a renamed or moved `references/*.md` independent of the docs refactor.
- **D-09** — Walk all tracked `.md` **except** `plugins/devflow/templates/**` and `.planning/**`. Both legitimately contain paths describing a *consuming* project, not this repo. Non-repo-relative refs (bare filenames like `STATE.md`, consuming-project artifacts like `.planning/config.json`, external URLs) are skipped **by rule, never a committed allowlist** — an allowlist drifts and becomes a place to hide failures.
- REQ-09 was amended during this discussion from "markdown links and anchors" to the above; REQ-09a–e carry the detail.

## Deferred
- External-URL checking — out of scope per PROJECT.md: it makes CI depend on third-party uptime.
- Mechanized detection of **prose** section mentions (e.g. `flow-status/SKILL.md` → "README → Session hygiene"). No link checker can catch these; REQ-08 handles them as a deliberate manual sweep in phase 04.
- An allowlist/ignore file for exceptions — explicitly rejected in D-09.

## Discretion
- Internal structure of `check-links.py` (single pass vs. collect-then-report), error message wording, and exit-code granularity beyond "non-zero on any failure".
- Whether the reference extractor is one regex or several, so long as the four reference kinds in REQ-09a–c are covered and REQ-09e's skips are rule-based.
- How anchors are harvested from target files (ATX headings at minimum), provided GitHub slug rules are applied per the assumption in REQUIREMENTS.md.
- Test layout under `tests/`, following the existing `importlib.util.spec_from_file_location` idiom that `tests/test_flow_agent.py` uses for hyphenated script names (see `.planning/codebase/MAP.md` → Conventions).

## Watch out
- The repo's own smoke command must keep passing at every point: do **not** add `check-links.py` to `ARCHITECTURE.md` `## Smoke` (REQ-11) before the script exists in the same change.
- The checker must exit 0 against the repo **as it stands today** — it is the baseline that makes phases 02–04 meaningful. If it reports failures on current content, those are either real pre-existing rot (fix and note) or over-broad rules (tighten), and the distinction has to be stated, not assumed.
