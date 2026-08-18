# Findings — tests (round 2)

Baseline: `Ran 64 tests ... OK (skipped=2)` (was 49). Tree clean at start and at end;
every mutation reverted with `git checkout -- scripts tests plugins` and verified.
Real repo under the current checker: `0 failures, 162 references checked`.
CI (`.github/workflows/lint.yml:20`) runs `python3 -m unittest discover -s tests -v`,
so a caught mutation does go red in CI.

## Round 1 disposition

### [blocking] Fence masking had zero coverage — **RESOLVED**
`tests/test_check_links.py:293-318` (`FenceMaskingTests`) + `:272-290` (`UnterminatedFenceTests`).
- **M19** (disable the closing-fence branch at `scripts/check-links.py:310-311` so `in_fence`
  never clears) — round 1: suite OK. Round 2: **3 failures** —
  `FenceMaskingTests.test_reference_after_a_closed_fence_is_still_checked`,
  `FenceMaskingTests.test_reference_inside_a_fence_is_not_checked`,
  `UnterminatedFenceTests.test_a_closed_fence_elsewhere_in_the_file_reports_no_such_failure`.
- **M7** (`_code_fence_mask` masks nothing) — round 1: suite OK. Round 2: **2 failures**
  (`test_reference_inside_a_fence_is_not_checked`, `test_unterminated_fence_is_reported_as_a_failure`).
- Both directions are now pinned, and B2b turned the unterminated case into a `Failure`
  rather than a silent mask, which is a second independent tripwire. Fully closed.

### [blocking] `test_r1_...` was vacuous — **RESOLVED**
`tests/test_check_links.py:149-162`.
- **M2** (delete the R1 whitespace block, now `scripts/check-links.py:205-206`) — round 1:
  suite OK. Round 2: **1 failure**, `SkipRuleTests.test_r1_command_line_with_space_is_skipped`.
- The new fixture (`` `docs/read me.md` `` with `docs/existing.md` planted) is correctly
  isolated: R5 declines because `docs` is a real top-level entry, the backtick extension
  filter still admits the token because it ends in `.md`, and R2/R3/R4 do not match — so R1
  is the only rule that can skip it. The class docstring at `:150-157` now spells out both
  ways the old fixture was vacuous, which is the right record to leave.

### [should-fix] `test_exit_status_is_one_...` passes via staleness, not GATE — **NOT RESOLVED**
`tests/test_flow_fleet.py:215-219`, fixture default journal at `:146`.
- **M16** (drop `p["flow"] in ATTENTION` from `needs_human`, `plugins/devflow/scripts/flow-fleet.py:316`)
  — round 2 result is **identical to round 1**: `test_gate_reaches_json_as_structured_data`
  and `test_render_surfaces_gate_options_to_the_human` fail; **`test_exit_status_is_one_when_any_project_needs_a_human` still passes.**
- Measured today against the actual fixture under the wall clock:
  `age_days: 3, flags: ['ON-BASE', 'STALE:3d', 'NO-DECL'], flow: GATE, needs_human: True`.
  Two independent paths; the staleness one only strengthens with time.
- S6 fixed the *other* two date sites but left `project()`'s default journal (`:146`) literal,
  and this test is the one case that takes the default while driving `main()`. One-line fix:
  `journal="- %s | /flow-execute | phase 3 | GATE" % TODAY` at the `:216` call site.

### [should-fix] Both `main()`-driven fleet tests read `~/.devflow/fleet.json` — **NOT RESOLVED**
`tests/test_flow_fleet.py:218` and `:226` — neither `main()` argv list gained `--stale-days`.
- Re-demonstrated: `HOME=<dir with .devflow/fleet.json {"stale_days": 0}> python3 -m unittest tests.test_flow_fleet`
  → **`Ran 21 tests ... FAILED (failures=1)`** (`test_exit_status_is_zero_when_everything_is_fine`).
  Latent on this machine (no `~/.devflow/`), live on any machine where an operator has
  configured the fleet scanner.

### [should-fix] `TODAY` over-applied at `test_no_gate_is_null` — **RESOLVED**
`tests/test_flow_fleet.py:171-176`.
- `:174` is back to the literal `"- 2026-08-15 | /flow-execute | phase 3 | CONTINUE"`, matching
  `scan()`'s pinned `datetime.date(2026, 8, 15)`. Verified by running the fixture:
  `age_days: 0, flags: ['ON-BASE', 'NO-DECL'], needs_human: False` — the nonsensical `-3` is gone.
- `:223` (the `main()`-driven case) correctly keeps `TODAY`. Neither is now wrong.
- The comment at `:22-27` still states the rule generally rather than narrowing it to
  `main()`/`date.today()` fixtures. Cosmetic; not worth another commit.

### [should-fix] No positive multi-base test — **NOT RESOLVED**
`scripts/check-links.py:259-275`.
- **M9** re-run in its round-2 form (`bases = [os.path.dirname(relfile)] if is_link else [""]`,
  i.e. backticked/`{devflow_root}` tokens resolve against the root base only) → **suite OK**.
- B1 narrowed `[text](target)` to a single base and `LinkResolutionTests` pins that half well
  (M-N1 below catches it in both directions), but the surviving multi-base walk — the one
  backticked tokens and `{devflow_root}/...` still use — has no fixture where a reference
  resolves *only* against a non-root base. `test_r5_is_per_base_...` pins `_bases_for` for the
  **skip** decision only; its `helpers/missing.py` is expected to fail either way.
- Still the false-positive direction (spurious red, not silent green), so still should-fix.
  One-line fix: add `` `helpers/present.py` `` to the existing `sub/a.md` fixture at `:191-200`
  and assert it produces no failure.

### [should-fix] `Failure.reason` never asserted — **PARTIALLY RESOLVED**
- `"target does not exist"` is now asserted twice (`:354`, `:369`) and `"unterminated"` once
  (`:284`). Replacing both reason strings with nonsense (M20) now fails 2 tests.
- But **M20b** — replace only `f"no such heading #{frag}"` (`scripts/check-links.py:293`) with
  `"ok"` — **still leaves the suite green**. `test_anchor_to_no_such_heading_fails` (`:75-84`)
  asserts `.file`, `.line`, `.target` and not `.reason`. One `assertEqual` closes it.

### [nit] Anchor slugging pinned only at its most trivial point — **UNCHANGED** (accepted, D-12)
### [nit] `_parse_link_target` and the external-URL skip untested — **NOT RESOLVED**
M11 (delete the `http://`/`https://`/`mailto:` early return) and M13 (`_parse_link_target`
returns `raw` unchanged) both still leave the suite green. Unchanged from round 1.
### [nit] `test_flow_fleet.py` does not sanitize git config — **NOT RESOLVED**
`tests/test_flow_fleet.py:152-156` still has no `env=`; `tests/test_check_links.py:25` still
has the `GIT_ENV` pattern. Two suites in one directory, two conventions.
### [nit] Redundant local `import datetime` — **RESOLVED**
Removed; `tests/test_flow_fleet.py:159-160` uses the module-level import at `:8`.

## New findings

### [blocking] Frontmatter masking is fence masking's twin — this round wired it into `_check_file` and shipped only the "masked" half of the test pair; breaking the closing branch takes 72% of the repo's references out of the scan with CI green
- `tests/test_check_links.py:417-429` (`FrontmatterMaskingTests`, one test); mechanism at
  `scripts/check-links.py:127`, `:323-331`
- S5 moved `_frontmatter_mask` from a heading-extraction detail into `_check_file`'s per-line
  skip (`:127`). It is now a line-range mask over the reference scan — the same category of
  lever that made fence masking blocking in round 1 — and the new test pins exactly one
  direction (a token inside frontmatter is skipped). The other direction, "a reference *after*
  the frontmatter closes is still checked", has no test at all. B3 added precisely that
  counterpart for fences (`FenceMaskingTests:309`) and did not add it for the mask it was
  newly wiring in.
- Reproduced scenario (mutation **M-N10**): delete the closing test in `_frontmatter_mask`
  (`:329-330`), so a leading `---` masks to EOF. **Full suite: `Ran 64 tests ... OK`.**
  Measured against this repo's real tree, that mutation drops the checker from
  **162 references checked to 45 — 117 of 162 (72%) silently unscanned** —
  and it still prints `0 failures` and CI still goes green. That is a larger blast radius
  than round 1's fence finding (31.7% of lines). **33 of the 50 in-scope `.md` files begin
  with `---`.**
- The same hole exists in the shipped code, not just the tests: an *unterminated* leading
  `---` masks the whole file today, with no signal. Reproduced against the current, unmutated
  checker — fixture `doc.md` = `"---\n\n# Doc\n\nSee [x](sub/missing.md) here.\n"` with
  `sub/existing.md` planted → `check()` returns `failures: [], checked: 0`; the identical file
  without the leading `---` returns one failure and `checked: 1`. B2b made exactly this case a
  `Failure` for fences (`scripts/check-links.py:119-125`) and left the frontmatter twin
  fail-open. Every one of those 33 files is one deleted delimiter away from going dark.
- Partial mitigation, stated plainly: B2a's `checked` counter *does* move (162 → 45), so a
  human reading the CI log could notice. Nothing asserts it and no CI step gates on it, so the
  build is still green — which is the condition round 1 called blocking.
- Fix: (a) mirror `FenceMaskingTests:309` — a fixture with closed frontmatter and a broken
  reference *after* the closing `---`, asserting exactly one failure at the right line; this is
  what kills M-N10. (b) mirror B2b in `scripts/check-links.py` — have `_frontmatter_mask`
  return an `unterminated_at` and report it as a `Failure`, with the test that pins it.

### [should-fix] `ReferenceCountTests` pins `.checked` at one value and never at its actual semantics — a hardcoded constant and a counter that counts skipped references both survive
- `tests/test_check_links.py:246-269`; mechanism at `scripts/check-links.py:58-65`, `:165-199`
- Both fixtures contain exactly two references and both assert `.checked == 2`, so the value
  is pinned at a single point, and neither fixture contains a *skipped* reference — so the one
  thing `.checked` is documented to mean ("references actually graded — passed or failed — as
  opposed to skipped by rule", `scripts/check-links.py:166-168`) is never exercised.
- Reproduced scenario, two mutations, both leaving `Ran 64 tests ... OK`:
  - **M-N4b**: `return CheckResult(failures, checked)` → `return CheckResult(failures, 2)`.
    A counter that has stopped counting and just prints `2` passes both tests.
  - **M-N4c**: `_check_reference`'s skip path (`:185-186`) returns `None, True` instead of
    `None, False`, so every rule-skipped reference is counted as checked. Demonstrated on a
    fixture with one graded link and one R2-skipped glob: real code → `checked: 1`,
    mutant → `checked: 2`.
  - M-N4c defeats the exact guarantee `test_zero_failures_still_reports_a_nonzero_checked_count`'s
    docstring claims ("a checker that skipped everything would also print '0 failures'") — under
    it, a checker that skips everything reports a healthy non-zero count.
- This matters more than a normal counter test because `.checked` is the only visibility
  mitigation standing behind every mask-widening failure mode in this file, including the
  blocking finding above.
- Fix: give one fixture an asymmetric count (e.g. 3 references, one of them rule-skipped) and
  assert `checked == 2` — that kills both M-N4b and M-N4c in one case.

### [nit] The `checked` counter is reported but nothing gates on it
- `scripts/check-links.py:77-79`; `.github/workflows/lint.yml:21`
- `main()` prints `N failure(s), M references checked`, but CI only reads the exit code, and no
  test covers `main()`'s output path at all (`MainSignatureTests:407-414` pins arity only). A
  floor assertion — CI failing if `references checked` drops below a committed baseline — is
  what would convert B2a from advisory to protective. Worth a line in the open-items list
  rather than a change now.

### [nit] `check(root)` against a non-repo root is still untested
- `scripts/check-links.py:93-102`; round-1 coverage gap #6, unchanged
- Confirmed still fail-closed by construction: `check(tempfile.mkdtemp())` raises
  `RuntimeError: git ls-files failed: fatal: not a git repository`. Deliberate per 01-02's
  plan ("never the CLI"), and `check(root)` is the pinned seam, so one case would cover it
  without touching the CLI.

## Mutation table

| # | Mutation | Caught? |
|---|---|---|
| M19 | `_code_fence_mask`: closing-fence branch disabled (`:310-311`) | **YES** — 3 tests (was NO in round 1) |
| M2 | R1 whitespace skip deleted (`:205-206`) | **YES** — `test_r1_command_line_with_space_is_skipped` (was NO) |
| M7 | `_code_fence_mask` masks nothing | **YES** — 2 tests (was NO) |
| M-N1 | `_resolve`: `is_link` strictness reverted to multi-base (`:263`) | YES — both `LinkResolutionTests` |
| M-N2 | Containment check removed (`:272-274`) | YES — both `ContainmentTests` |
| M-N3 | `git ls-files -z` → plain `ls-files` + `splitlines()` (`:97-102`) | YES — `test_broken_reference_inside_a_specially_named_file_is_still_caught` |
| M-N4a | `CheckResult(failures, 0)` — counter always zero | YES — both `ReferenceCountTests` |
| M-N4b | `CheckResult(failures, 2)` — counter hardcoded to the expected value | **NO** — suite OK → should-fix |
| M-N4c | Skipped references counted as checked (`:185-186` → `None, True`) | **NO** — suite OK → should-fix |
| M-N5a | Unterminated-fence `Failure` suppressed (`:119`) | YES — `test_unterminated_fence_is_reported_as_a_failure` |
| M-N5b | `_code_fence_mask` never reports `unterminated_at` (`:320`) | YES — same test |
| M-N6 | Directory targets rejected again (`:267`, isfile only) | YES — both `DirectoryTargetTests` |
| M-N7 | Fragment-against-directory branch removed (`:193-195`) | YES — `test_anchor_into_a_directory_target_is_not_heading_graded` |
| M-N8 | `main()` accepts and discards `argv` again (`:68`) | YES — `test_main_does_not_silently_accept_an_argv_list` |
| M-N9 | Frontmatter mask dropped from `_check_file` (`:127`) | YES — `test_path_shaped_token_in_frontmatter_is_not_checked_as_a_reference` |
| M-N10 | `_frontmatter_mask`: closing branch deleted, masks to EOF (`:329-330`) | **NO** — suite OK; 117/162 (72%) of real references silently unscanned → blocking |
| M9 | `_resolve`: backticked/`{devflow_root}` walk reduced to root base only | **NO** — suite OK (round-1 should-fix, still open) |
| M16 | `flow-fleet.py:316`: drop `p["flow"] in ATTENTION` from `needs_human` | PARTIAL — 2 tests fail; `test_exit_status_is_one_...` **still passes** (round-1 should-fix, still open) |
| M20 | Both `Failure.reason` strings replaced with nonsense | YES — both `ContainmentTests` (was NO) |
| M20b | Only `f"no such heading #{frag}"` replaced (`:293`) | **NO** — suite OK → round-1 finding only partially closed |
| M11 | External-URL skip deleted (`:170-171`) | **NO** — suite OK (round-1 nit, still open) |
| M13 | `_parse_link_target` returns `raw` unchanged (`:152`) | **NO** — suite OK (round-1 nit, still open) |

Non-mutation checks: unterminated leading `---` against the **unmutated** checker →
`failures: [], checked: 0` vs `checked: 1` for the same file without it; 33/50 in-scope `.md`
files begin with `---`; `test_exit_status_is_one_...` fixture under the real clock →
`age_days 3, flags ['ON-BASE','STALE:3d','NO-DECL']`; `HOME=<fake>` with
`.devflow/fleet.json {"stale_days":0}` → `FAILED (failures=1)`; `test_no_gate_is_null` fixture
→ `age_days 0` (S6 verified correct); `check(<non-repo tmpdir>)` → `RuntimeError`.

## Verification of the S6 fix (task item 4)
- `tests/test_flow_fleet.py:174` — literal `2026-08-15`, matching `scan()`'s pinned reference
  date at `:160`. Correct; `age_days` measured at 0.
- `tests/test_flow_fleet.py:223` — keeps `TODAY`. Correct; this is the `main()`-driven case
  that reads `date.today()`.
- Neither is now wrong. The redundant method-local `import datetime` is gone.
- `git diff 31e858b..HEAD -- tests/` shows exactly three removed lines across the three fix
  commits (the vacuous R1 fixture line, the local `import datetime`, the over-applied `TODAY`).
  No existing assertion was deleted or weakened anywhere in this round.

## Test isolation
- `tests/test_check_links.py` — still clean. The new `ContainmentTests` builds its fixture in a
  nested tempdir with its own `addCleanup`, uses `GIT_ENV`, and the file it plants outside the
  repo is inside that same tempdir — nothing touches the real tree.
  `TrackedFileEnumerationTests` creates a file with a `"` in its name, which is fine on Linux
  and on the ubuntu-latest runner; it would fail on Windows, which this project does not target.
- `tests/test_flow_fleet.py` — still leaks on `~/.devflow/fleet.json` (demonstrated failure
  above) and on the global gitconfig. Unchanged from round 1.
- `git status --porcelain` confirmed clean after every one of the 22 mutation cycles and at the
  end (only the untracked `.planning/reviews/` output dir).

## Summary
**1 blocking, 1 should-fix, 2 nit (new only).**

Round-1 disposition: 2 blocking **RESOLVED**, 1 should-fix RESOLVED, 1 PARTIALLY, 3 NOT RESOLVED,
1 nit RESOLVED, 3 nits unchanged.

Candidates for the PR's open-items list (round-1 items outside the fix scope, all re-verified as
still standing): the `~/.devflow/fleet.json` host dependency, `needs_human` passing via staleness
in `test_exit_status_is_one_...`, the missing positive multi-base test, the un-asserted
`no such heading` reason, `_parse_link_target` + the URL skip, and the fleet suite's unsanitized
git config.
