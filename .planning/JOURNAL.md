<!-- .planning/JOURNAL.md — cap 2KB (~25 lines). Newest first; when over cap, MOVE the oldest lines
to .planning/history/JOURNAL-<YYYY>.md (append, chronological, uncapped) — never drop them.
The cap bounds what loads into context each run; it is not permission to forget.
One line per completed state-changing skill run. Warm-start + audit trail; context repos (docs/blitzos.md) index these lines verbatim. -->
# Journal
- 2026-09-04 | /flow-pr | PR #36 opened (github.com/jbrianfrancis-ir/devflow/pull/36) — release
  0.20.0 (covers #34/#35, which merged untagged) + a CI gate failing any PR that changes
  plugins/devflow/** without a bump; 3 review rounds found 3 fail-opens in the gate itself,
  2 blocking, each raised by 2 lenses independently | CONTINUE
- 2026-09-01 | /flow-pr | PR #33 opened (github.com/jbrianfrancis-ir/devflow/pull/33) — quick 012,
  /flow-triage skill (incoming PR pre-screening), v0.19.0; 1 blocking (gh JSON field) fixed pre-push | CONTINUE
- 2026-08-27 | /flow-pr | PR #32 opened (github.com/jbrianfrancis-ir/devflow/pull/32) — quick 011, v0.18.0; external state is a cache, plus 'observation answers a fact, never an authorization' after a blocking finding on self-clearing release gates | CONTINUE
- 2026-08-27 | quick 011 | PRs #30 and #31 merged to main (16:28-16:29Z); STATE.md had
  asserted both open with a live rule-10 gate — the stale-external-state defect quick 011 fixes | CONTINUE
- 2026-08-27 | /flow-pr | PR #30 opened (github.com/jbrianfrancis-ir/devflow/pull/30) — /flow-hooks skill (base-branch/protected-paths/secret-scan guards), v0.17.0; 3 review rounds, 6 blocking (all live-verified bypasses) fixed | CONTINUE
- 2026-08-27 | /flow-pr | PR #31 opened (github.com/jbrianfrancis-ir/devflow/pull/31) — quick 010, flow-pr's PR gate now pauses only for autonomous runs, not direct invocation | CONTINUE
