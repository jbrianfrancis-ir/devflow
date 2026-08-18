# Findings — tests

## Summary
2 blocking, 5 should-fix, 4 nit

## Findings

### [blocking] Fence masking is a sixth, unbounded skip rule with zero test coverage — breaking it silences 32% of the repo while CI stays green
- `tests/test_check_links.py:1-207` (no case); mechanism at `scripts/check-links.py:96-100`, `:247-265`, `:281`
- The suite's own docstring says it exists so "the skip rules (R1-R5) cannot be quietly widened later to make a failing check go green". Fence masking is functionally a sixth skip rule, it is strictly more powerful than R1-R5 (it silences whole line ranges rather than one token), it is not in REQ-09e, and **no test exercises it in either direction**. `VERIFICATION.md` → Learnings already predicts the hit: "phases 02-04 moving examples into fences would lose that coverage with no signal."
- Failure scenario (mutation-proved, M19): disable the closing-fence branch in `_code_fence_mask` (`scripts/check-links.py:256-257`) so `in_fence` never clears. **Full suite: `Ran 49 tests ... OK`.** Measured against this repo's real tree, that mutation leaves **672 of 2118 scoped lines (31.7%) across 50 `.md` files permanently unchecked** — every line after each file's first fence. `scripts/check-links.py` still prints `0 failures` and CI still goes green. This is precisely the "guard reporting success it did not establish" failure `references/conventions.md` → Fail-closed guards names as a bug, and the safety net would be gone with no signal at all.
- Suggested fix: add two cases to `CleanFixtureTests`/a new `FenceTests` — (a) a broken reference inside a ```` ``` ```` fence yields `[]`, and (b) a broken reference on a line **after** the fence closes still yields exactly one failure naming file/line/target. (b) is the one that kills M19. Add the `~~~` variant while you are there, since `_code_fence_mask` accepts both.

### [blocking] `test_r1_command_line_with_space_is_skipped` is vacuous — R1 can be deleted outright and the suite stays green
- `tests/test_check_links.py:149-154` (and the class docstring at `:145-147`)
- The class docstring asserts: "Each fixture also plants a real top-level entry matching the token's first segment, so the case pins its own rule specifically — not an incidental R5 skip." **That claim is false for R1.** The fixture plants `docs/existing.md`, but the token is `cat docs/readme.md`, and `_r5_skip` splits on `/` — so the first segment is `"cat docs"`, not `"docs"`. `"cat docs"` is not a top-level entry of any base, so R5 (`scripts/check-links.py:210-217`) skips the token before R1 is ever load-bearing. Verified directly: `_r5_skip("cat docs/readme.md", "doc.md", ["doc.md","docs/existing.md"])` → `True`.
- Failure scenario (mutation-proved, M2): delete the R1 block at `scripts/check-links.py:166-167` entirely. **Full suite: `Ran 49 tests ... OK`.** The rule the test names can be removed, inverted, or widened (e.g. "skip any token containing a dot") and nothing in the suite fires. The other four rules are genuinely pinned — M3 (R2 removed) → `test_r2_...` fails; M4 (R3 removed) → `test_r3_...` fails; M5 (R4 removed) → `test_r4_...` fails; M6 (`_r5_skip` forced `True`) → 4 tests fail — so R1 is the single hole in a set the suite claims is complete.
- Suggested fix: make the whitespace land *after* the first path separator so R5 cannot pre-empt it, e.g. token `` `docs/readme.md and more` `` with `docs/existing.md` planted (first segment `docs` is a real top-level entry → R5 declines → only R1 can skip it). Re-run with R1 deleted to confirm the case now fails. Fix the class docstring's claim or drop it.

### [should-fix] `test_exit_status_is_one_when_any_project_needs_a_human` now passes partly because of staleness, not the GATE it names
- `tests/test_flow_fleet.py:216-220` (fixture default journal date at `:146`)
- This is the contamination the commit message admits, and it is real. The fixture's journal line is hardcoded `2026-08-15`; this test drives `MODULE.main()`, which uses the **wall clock** (`plugins/devflow/scripts/flow-fleet.py:438`). Measured today: `age_days 3`, `flags ['ON-BASE', 'STALE:3d', 'NO-DECL']` — `needs_human` is now `True` via two independent paths, and the staleness path only gets stronger with time. The test's name says GATE; it no longer requires GATE.
- Mutation-proved (M16): strip `p["flow"] in ATTENTION` from `needs_human` (`flow-fleet.py:316`). This test **still passes**. It is not blocking only because `test_gate_reaches_json_as_structured_data` (`:163`) and `test_render_surfaces_gate_options_to_the_human` (`:208`) *did* fail under M16 — they use `self.scan()` with a pinned reference date, so `age_days` is 0 and no STALE flag appears. The GATE→`needs_human` behavior is still constrained, just not by the test that claims to constrain it.
- Suggested fix: give this fixture `journal="- %s | /flow-execute | phase 3 | GATE" % TODAY` so the only reason it needs a human is the gate. Same treatment for the `project()` default at `:146` if any other `main()`-driven case adopts it.

### [should-fix] Both `main()`-driven fleet tests read the developer's `~/.devflow/fleet.json` — a host file can fail them
- `tests/test_flow_fleet.py:219` and `:227` — `MODULE.main([str(self.base), "--json", "--depth", "2"])`
- `roots` and `depth` are passed explicitly but `--stale-days` is not, so `main()` falls back to `CONFIG_PATH = ~/.devflow/fleet.json` (`flow-fleet.py:429-435`). The staleness threshold — the exact knob this commit was fixing around — is taken from ambient host state.
- Failure scenario (demonstrated, not hypothetical): `HOME=<dir containing .devflow/fleet.json with {"stale_days": 0}> python3 -m unittest tests.test_flow_fleet` → **`FAILED (failures=1)`**, `test_exit_status_is_zero_when_everything_is_fine`, because `age_days 0 >= 0` flags STALE. This machine has no `~/.devflow/`, so it is latent here and would fire on any machine where an operator has configured the fleet scanner — including a self-hosted runner.
- Suggested fix: append `"--stale-days", "3"` to both `main()` argv lists. This is the same class of bug as the one just fixed (fixture outcome depends on state outside the fixture), on the same two lines.

### [should-fix] The `TODAY` fix is over-applied at `test_no_gate_is_null` and gives that fixture a future-dated journal entry
- `tests/test_flow_fleet.py:172-177` (changed line `:175`); constant + rationale at `:22-27`
- This test goes through `self.scan()` (`:159-161`), which pins the reference date to `datetime.date(2026, 8, 15)` — it never consulted the wall clock, so it was never a time bomb. Mutation-proved (M17): revert `TODAY` to the literal `"2026-08-15"` and **only** `test_exit_status_is_zero_when_everything_is_fine` fails; `test_no_gate_is_null` passes either way. The edit changes nothing it claims to change.
- It is mildly worse than a no-op: with the reference date pinned at 2026-08-15 and the journal at the real today (2026-08-18), `age_days` is now **-3** — a journal entry dated in the fixture's future. Harmless under current assertions, misleading to the next reader, and it would render as `-3d` in `render()`.
- The comment at `:22-27` states a general rule ("a hardcoded date silently converts any 'nothing needs a human' assertion into a time bomb") that is only true for the `main()`-driven tests. Net: the fix is **correct where it was needed (`:224`), incomplete (see the two findings above), and over-applied here**.
- Suggested fix: revert `:175` to the pinned `2026-08-15` to match `self.scan()`'s frozen clock, and narrow the comment to say `TODAY` is for fixtures that reach `main()`/`date.today()`.

### [should-fix] Multi-base resolution has no positive test — `_resolve` can be reduced to root-only and the suite stays green
- `tests/test_check_links.py:177-203`; `scripts/check-links.py:180-192`, `:220-225`
- `test_r5_is_per_base_...` pins `_bases_for` for the **skip** decision, but every reference in every fixture that is *expected to resolve* resolves against the root base. No fixture contains a link that resolves *only* relative to the referring file's own directory, and none resolves only under `plugins/devflow/` via the `{devflow_root}` base.
- Failure scenario (mutation-proved, M9): replace `for base in _bases_for(relfile)` with `for base in [""]` in `_resolve` (`:221`). **Full suite: `Ran 49 tests ... OK`.** Every sibling-relative reference in `plugins/devflow/**` and `docs/**` would start reporting `target does not exist`. This is the false-positive direction — CI goes spuriously red rather than silently green — which is why it is should-fix and not blocking, but a mass-false-positive checker gets disabled, and then it protects nothing.
- Suggested fix: extend the `test_r5` fixture (or `CleanFixtureTests`) with a link from `sub/a.md` to `helpers/present.py` and assert it produces no failure — a one-line addition to a fixture that already has `sub/helpers/present.py` on disk. Add the `{devflow_root}` positive too: `plugins/devflow/x.md` referencing `` `{devflow_root}/dummy.txt` `` resolving clean.

### [should-fix] `Failure.reason` is never asserted anywhere in the suite
- `tests/test_check_links.py:68-73`, `:79-84`, `:100-105`, `:113-119` — each asserts `.file`, `.line`, `.target`, never `.reason`
- `reason` is half the operator-facing output (`scripts/check-links.py:61` prints `file:line: target — reason`) and it is what distinguishes "target does not exist" (repoint the link) from "no such heading #x" (fix the anchor) — different remediations.
- Mutation-proved (M20): replace `"target does not exist"` with `"everything is fine, nothing to see"` and `f"no such heading #{frag}"` with `"ok"`. **Full suite: `Ran 49 tests ... OK`.**
- Suggested fix: add `self.assertIn("does not exist", failure.reason)` / `self.assertEqual("no such heading #no-such-heading", failure.reason)` to the four kind-failure cases.

### [nit] Anchor slugging is pinned only at its most trivial point
- `tests/test_check_links.py:86-91`; `scripts/check-links.py:279-330`
- `test_anchor_to_real_heading_passes` uses `# Doc Heading` → `#doc-heading`, which exercises lowercasing and space→dash only. Confirmed live: M15 (drop `.lower()`) **is** caught; but M8 (drop the `[^\w\s-]` punctuation strip), M10 (drop the duplicate-heading `-1` suffix), M12 (`_frontmatter_mask` → all `False`) all survive the full suite, and `_strip_inline_markdown` and the setext branch (`:298-307`) have no fixture at all.
- Explicitly accepted, not a gap: `VERIFICATION.md` frontmatter lists this under `unverified:` and the human check was answered 2026-08-18 (D-12) as an accepted abstention. Recording it here so the rank is on file; revisit when `docs/` gains a duplicate, inline-code, or setext heading.

### [nit] `_parse_link_target` and the external-URL skip are entirely untested
- `tests/test_check_links.py` (no case); `scripts/check-links.py:120-130`, `:134-135`
- M13 (`_parse_link_target` returns `raw` unmodified) and M11 (delete the `http://`/`https://`/`mailto:` early return) both survive the full suite. No fixture uses a titled link `[x](path "Title")`, an angle-bracket link `[x](<path with space>)`, or any URL. Breaking title stripping would make every titled link in the repo report `target does not exist`; breaking the URL skip would make the checker start resolving `https://...` as a repo path.
- Suggested fix: one fixture with `[a](sub/other.md "Title")`, `[b](<sub/other.md>)` and `[c](https://example.com)`, asserting `[]`.

### [nit] `tests/test_flow_fleet.py` does not sanitize git config the way `tests/test_check_links.py` does
- `tests/test_flow_fleet.py:152-156` vs `tests/test_check_links.py:25`, `:42-45`
- The new suite deliberately sets `GIT_CONFIG_GLOBAL=/dev/null` / `GIT_CONFIG_SYSTEM=/dev/null` "so behavior is identical on CI". The fleet fixtures inherit the developer's global gitconfig — a global `core.excludesFile` or hook could change what `git add -A` stages and therefore the `git status --porcelain` dirty count the scanner reads (`flow-fleet.py:278-280`). Low likelihood, zero cost to close, and the inconsistency between two suites in the same directory is itself the smell.
- Suggested fix: hoist `GIT_ENV` into a shared place or duplicate the two-line pattern into `project()`.

### [nit] Redundant local `import datetime` left behind by the fix
- `tests/test_flow_fleet.py:160`
- The commit added a module-level `import datetime` at `:8`; the method-local one inside `ScanTests.scan` is now dead. Delete it.

## Coverage gaps in `scripts/check-links.py`, ranked by risk
1. **Fence masking** (both directions) — blocking above. Silences whole files; the only lever in the script that can turn the guard green wholesale.
2. **R1** — blocking above. Named by a test that does not constrain it.
3. **Multi-base resolution, positive direction** — mass false positives; `_resolve` is reducible to root-only undetected.
4. **`_parse_link_target` + URL skip** — no coverage at all.
5. **Anchor slugging beyond lowercase/space** — accepted abstention (D-12).
6. **`main()` and the fail-closed `except` at `check-links.py:57-59`** — no test asserts that "could not check" exits non-zero. Deliberate per 01-02's plan ("never the CLI"), and it fails closed by construction, but `conventions.md` → Fail-closed guards makes this the highest-consequence branch in the file; a `check(root)`-level test that passes a non-repo root would cover it without touching the CLI.
7. **`Failure.reason`, `failures.sort()` ordering, "import has no side effect"** — asserted in `VERIFICATION.md` prose, asserted by no test.

## Test isolation
- `tests/test_check_links.py` — **clean**. `tempfile.mkdtemp` + `addCleanup(shutil.rmtree)`; every `subprocess.run` passes `cwd=` explicitly; `check(root)` takes an absolute root so nothing depends on the process cwd; git config sanitized; the real repo tree is never read or written. Module import via `spec_from_file_location` has no side effect (`check-links.py` guards all execution behind `if __name__ == "__main__"`). `git status --porcelain` was empty after all 20 mutation cycles.
- `tests/test_flow_fleet.py` — file isolation is fine (`TemporaryDirectory` per test, torn down in `tearDown`), but it leaks on two pieces of host state: `~/.devflow/fleet.json` (should-fix above, demonstrated failure) and the global gitconfig (nit above).
- No fixture anywhere mutates the repo under review.

## Mutations run
All against `scripts/check-links.py` unless noted; each applied, full `python3 -m unittest discover -s tests` run, then `git checkout -- scripts tests plugins`. Tree confirmed clean after every cycle and at the end (`git status --porcelain` → only the untracked `.planning/reviews/` output dir). Final suite state: `Ran 49 tests ... OK (skipped=2)`.

| # | Mutation | Caught? |
|---|---|---|
| M1 | `_check_reference`: missing target returns `None` instead of a `Failure` | **YES** — 4 tests (3 kind-failures + r5) |
| M2 | **R1 removed** (whitespace skip, `:166-167`) | **NO** — suite OK → blocking finding |
| M3 | R2 removed (`FAMILY_CHARS_RE`, `:168-169`) | YES — `test_r2_glob_token_is_skipped` |
| M4 | R3 removed (placeholder segment, `:170-172`) | YES — `test_r3_nn_slug_placeholder_is_skipped` |
| M5 | R4 removed (`.planning/`, `~/`, `:173-174`) | YES — `test_r4_planning_rooted_token_is_skipped` |
| M6 | `_r5_skip` forced to always `True` | YES — 4 tests |
| M7 | `_code_fence_mask` → all `False` (no masking) | **NO** — suite OK |
| M8 | `_slugify`: drop the `[^\w\s-]` punctuation strip | **NO** — suite OK (accepted, D-12) |
| M9 | `_resolve`: root base only, ignore `_bases_for` | **NO** — suite OK → should-fix |
| M10 | `_heading_slugs`: drop the duplicate `-1` suffix | **NO** — suite OK (accepted, D-12) |
| M11 | Delete the `http://`/`https://`/`mailto:` skip | **NO** — suite OK |
| M12 | `_frontmatter_mask` → all `False` | **NO** — suite OK (accepted, D-12) |
| M13 | `_parse_link_target` returns `raw` unchanged | **NO** — suite OK |
| M14 | Drop `EXCLUDE_PREFIXES` from `check()`'s file list | YES — both `ScopeExclusionTests` |
| M15 | `_slugify`: drop `.lower()` | YES — `test_anchor_to_real_heading_passes` |
| M16 | `flow-fleet.py:316`: drop `p["flow"] in ATTENTION` from `needs_human` | PARTIAL — `test_gate_reaches_json_...` + `test_render_surfaces_gate_options_...` fail; **`test_exit_status_is_one_when_any_project_needs_a_human` still passes** (staleness) |
| M17 | `test_flow_fleet.py`: `TODAY` → literal `"2026-08-15"` (pre-fix state) | PARTIAL — only `test_exit_status_is_zero_when_everything_is_fine` fails; `test_no_gate_is_null` passes either way → the `:175` edit was unnecessary |
| M18 | `_code_fence_mask` → all `True` (mask everything) | YES — 5 tests (the crude version is caught; M19's realistic one is not) |
| M19 | `_code_fence_mask`: closing-fence branch disabled — `in_fence` never clears | **NO** — suite OK; 672/2118 (31.7%) of scoped lines go unchecked on the real repo → blocking |
| M20 | Replace both `Failure.reason` strings with nonsense | **NO** — suite OK |

Non-mutation checks: `_r5_skip("cat docs/readme.md", ...)` → `True` (proves M2's mechanism); `scan()` under the real clock on the `test_exit_status_is_one` fixture → `flags ['ON-BASE','STALE:3d','NO-DECL']` (proves the staleness contamination); `HOME=<fake>/.devflow/fleet.json {"stale_days":0}` → `FAILED (failures=1)` (proves the host-config leak); fence blast radius measured by importing `_code_fence_mask` over all 50 scoped `.md` files.
