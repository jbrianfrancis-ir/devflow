# Findings — tests (round 3, final)

Baseline: `Ran 75 tests in ~2.0s ... OK (skipped=2)` (was 64, was 49). The two skips are
`test_flow_agent.BridgeSmokeTests.test_real_{claude,codex}_peer`, opt-in behind
`DEVFLOW_SMOKE=1` — correct, not a gap.
Real repo under the current checker: `0 failures, 162 references checked`.
CI (`.github/workflows/lint.yml:20,22`) runs the suite *and* `scripts/check-links.py`
against the real tree, so there are two independent gates; several findings below turn on
which of the two actually catches a given regression.
39 mutation cycles run this round; `git status --porcelain` verified clean after each and at
the end (only the untracked `.planning/reviews/` output dir). `git diff HEAD` is empty.

---

## Round 2 disposition

### [blocking] Frontmatter closing-branch mutation drops the repo 162 → 45 with CI green — **RESOLVED**
Fix at `scripts/check-links.py:127-133`, `:392-405`; tests at `tests/test_check_links.py:456-486`.
Re-run in both forms:

- **M-N10b** — round 2's exact scenario: `_frontmatter_mask` masks to EOF and returns
  `None` for `unterminated_at` (silent). Round 2: `Ran 64 ... OK`.
  **Round 3: `FAILED (failures=4)`** —
  `test_reference_after_a_closed_frontmatter_block_is_still_checked`,
  `test_unterminated_frontmatter_is_reported_as_a_failure`,
  `test_reference_after_an_unterminated_frontmatter_block_is_not_checked`,
  `RepoCoverageFloorTests.test_real_repo_checked_count_does_not_collapse`.
  Repo under the mutant: `0 failures, 45 checked` — the same 72% collapse, now red four ways.
- **M-N10a** — closing branch deleted but `unterminated_at` still returned:
  **`FAILED (failures=3)`**, repo `33 failures, 45 checked`.

Both halves of the pair are pinned, the unterminated case is a `Failure` rather than a silent
mask (mirroring B2b for fences), and the mask *contract* is separately pinned in three more
directions: **M-U1** (Failure suppressed in `_check_file`) → 2 failures; **M-U3** (wrong line
number reported) → 1 failure; **M-U4** (reported but not masked, so downstream refs leak out) →
1 failure; **M-U5** (reason string replaced with nonsense) → 2 failures. Fully closed.

### [should-fix] `test_exit_status_is_one_when_any_project_needs_a_human` passed via staleness, not GATE — **RESOLVED**
`tests/test_flow_fleet.py:216-226` now passes `journal="- %s | /flow-execute | phase 3 | GATE" % TODAY`.
- **M16** (drop `p["flow"] in ATTENTION` from `needs_human`, `plugins/devflow/scripts/flow-fleet.py:315`)
  — rounds 1 and 2: this test **passed**. **Round 3: it fails**, alongside the two that already
  failed. `FAILED (failures=3)`: `test_exit_status_is_one_when_any_project_needs_a_human`,
  `test_gate_reaches_json_as_structured_data`, `test_render_surfaces_gate_options_to_the_human`.
- With `--stale-days 3` pinned and the journal dated today, `age_days` is 0, so no `STALE` flag
  exists to carry the assertion. GATE is now the only reason the fixture needs a human, which is
  what the test's name claims.

### [should-fix] Both `main()`-driven fleet tests read `~/.devflow/fleet.json` — **RESOLVED**
`tests/test_flow_fleet.py:226` and `:236` both now pass `"--stale-days", "3"`.
- Round 2 repro re-run: `HOME=<dir with .devflow/fleet.json {"stale_days": 0}> python3 -m unittest tests.test_flow_fleet`
  → round 2 `FAILED (failures=1)`; **round 3 `Ran 21 tests ... OK`.**
- Also probed the opposite direction (`{"stale_days": 999}`) → `OK`, and the whole 75-test suite
  under the same hostile `HOME` → `OK (skipped=2)`. Hermetic in both directions.

### [should-fix] No positive multi-base test — **NOT RESOLVED** (severity now lower)
- **M9** (`_resolve`: prose/backticked walk reduced to the root base only) → **suite still `OK`.**
- But measured against the real tree, the mutant produces **`10 failures, 162 checked`**, so
  CI's second step (`python3 scripts/check-links.py`) goes red. The regression is caught by CI,
  just not by the unit suite. Downgrade to **nit**: still worth the one-line fixture, no longer
  an undefended hole.

### [should-fix] `Failure.reason` never asserted — **PARTIALLY RESOLVED** (unchanged from round 2)
- **M20b** (replace only `f"no such heading #{frag}"` at `scripts/check-links.py:296` with `"ok"`)
  → **suite still `OK`.** `test_anchor_to_no_such_heading_fails` (`tests/test_check_links.py:75-84`)
  still asserts `.file`/`.line`/`.target` and not `.reason`. One `assertEqual` closes it.
- The two unterminated-block reasons *are* now pinned: **M-U5** (frontmatter) → 2 failures,
  **M-U6** (fence) → 1 failure. So the gap is now exactly one reason string.

### [nit] `_parse_link_target` and the external-URL skip untested — **NOT RESOLVED** (now higher-consequence, see gaps)
- **M13** (`_parse_link_target` returns `raw` unchanged) → suite `OK`, repo `0 failures, 162 checked` —
  caught by nothing at all, in either gate.
- **M11** (external-URL early return deleted) → suite `OK`.

### [nit] `test_flow_fleet.py` does not sanitize git config — **NOT RESOLVED, and upgraded to should-fix on new evidence**
Rounds 1 and 2 called this hypothetical. It is not. `tests/test_flow_fleet.py:146-156` has no
`env=`; `grep -n "GIT_CONFIG\|env=" tests/test_flow_fleet.py` returns nothing. Reproduced twice:

| global config | `python3 -m unittest tests.test_flow_fleet` | `tests.test_check_links` |
|---|---|---|
| `commit.gpgsign = true` (+ a signingkey) | **`FAILED (errors=9)`** | `Ran 39 ... OK` |
| `core.excludesFile` ignoring `*.md` | **`FAILED (errors=9)`** | `Ran 39 ... OK` |

`commit.gpgsign = true` is an ordinary developer setting. On such a machine 9 of the 21 fleet
tests error out — not a subtle skew, a hard `subprocess.CalledProcessError` from `project()`'s
`check=True` commit. `tests/test_check_links.py:25` already has the two-line `GIT_ENV` fix, in
the same directory. Copy it into `project()`.

### [nit] Anchor slugging pinned only at its most trivial point — **UNCHANGED** (see gaps; D-12's premise is expiring)
### [nit] `TODAY` over-applied / redundant `import datetime` — **RESOLVED** (verified round 2, unchanged)
### [nit] `check(root)` against a non-repo root untested — **NOT RESOLVED**, still fail-closed by
construction: `check(tempfile.mkdtemp())` → `RuntimeError: git ls-files failed: fatal: not a git repository`.

---

## Mutation table for tests added this round

Every one of the seven test classes/cases added this round bites. **No test added this round
survived mutation of the behavior it names.**

### Reference-level escape rejection — `EscapeAndReturnContainmentTests` (`tests/test_check_links.py:541-588`)
| # | Mutation (`scripts/check-links.py:299-301`) | Caught? |
|---|---|---|
| M-E1 | escape check removed entirely (revert to realpath-only containment — the round-2 S-1 bug) | **YES** — `test_escape_and_return_is_rejected...`, both subTests |
| M-E2 | weakened to `joined == os.pardir` only (drops the `startswith` half) | **YES** — both subTests |
| M-E3 | over-strict: reject any `path_part` containing `..` | **YES** — `test_legitimate_parent_reference_from_a_subdirectory_still_resolves` |

Both directions pinned; the control case is load-bearing, not decoration.

### R5 `is_link` exemption — `LinkR5ExemptionTests` (`:489-513`)
| # | Mutation (`scripts/check-links.py:222-235`) | Caught? |
|---|---|---|
| M-R5a | `if is_link: return False` reverted (R5 applies to links again) | **YES** — `test_markdown_link_with_unmatched_first_segment_is_reported_broken_not_skipped` |
| M-R5b | exemption inverted to `if not is_link` (exempts prose instead of links) | **YES** — 3 tests, incl. `test_backticked_token_..._still_skipped` |
| M-R5c | `_r5_skip` never skips at all | **YES** — 2 tests; repo → `13 failures, 175 checked` |

### `root_anchored` — `DevflowRootLinkAnchoringTests` (`:516-538`)
| # | Mutation (`scripts/check-links.py:167-172`, `:277-281`) | Caught? |
|---|---|---|
| M-RA1 | `root_anchored` no longer forces the root base (`is_link` own-dir wins) | **YES** — `test_devflow_root_link_from_a_nested_file_resolves_against_repo_root` |
| M-RA2 | `root_anchored` resolves against the referring file's own dir | **YES** — same test |
| M-RA3 | `root_anchored` references skipped outright, never graded | **YES** — 3 tests incl. the coverage floor; repo → `0 failures, 50 checked` |
| M-RA4 | the `{devflow_root}/` → `plugins/devflow/` rewrite removed (token keeps `{`, R2 skips it) | **YES** — 3 tests; repo → `0 failures, 50 checked` |

Note for the record: under **M-RA4** the *positive* case (`..._resolves_against_repo_root`)
stays green — it asserts `[]`, and a silently-skipped reference also yields `[]`. It is the
sibling negative case that kills M-RA4. The pair is sound; neither half is sufficient alone.

### Unterminated frontmatter as a failure — `FrontmatterMaskingTests` (`:438-486`)
| # | Mutation | Caught? |
|---|---|---|
| M-N10a / M-N10b | closing branch deleted (masks to EOF), loud / silent variants | **YES** — 3 / 4 tests |
| M-U1 | `front_unterminated_at` `Failure` suppressed in `_check_file` (`:127`) | **YES** — 2 tests |
| M-U2 | `_frontmatter_mask` never reports unterminated (`:405` → `None`) | **YES** — 2 tests |
| M-U3 | unterminated reported at line 2 instead of line 1 | **YES** — `test_unterminated_frontmatter_is_reported_as_a_failure` |
| M-U4 | reported but *not* masked, so downstream refs leak out as extra findings | **YES** — `test_reference_after_an_unterminated_frontmatter_block_is_not_checked` |
| M-U5 | reason string replaced with `"all good here"` | **YES** — 2 tests |
| M-U6 | the *fence* unterminated reason string replaced (control) | **YES** — `test_unterminated_fence_is_reported_as_a_failure` |

### `.checked` semantics — `ReferenceCountTests` (`:246-289`)
Round 2's two survivors are dead:
| # | Mutation (`scripts/check-links.py:63`, `:189-190`) | Round 2 | Round 3 |
|---|---|---|---|
| M-N4a | `CheckResult(failures, 0)` | YES | **YES** — 4 tests |
| M-N4b | `CheckResult(failures, 2)` — hardcoded to the old fixtures' value | **NO** | **YES** — `test_checked_count_excludes_rule_skipped_references_not_just_failures` + the floor |
| M-N4b3 | `CheckResult(failures, 3)` — hardcoded to the *new* fixture's value | n/a | **YES** — 3 tests |
| M-N4b162 | `CheckResult(failures, 162)` — hardcoded to the real-repo value | n/a | **YES** — 3 tests |
| M-N4c | rule-skipped references counted as checked (`None, True`) | **NO** | **YES** — the new test; repo → `checked 336` |
| M-N4d | the **external-URL** skip counted as checked | n/a | **NO** — suite `OK`; repo → `checked 178` (see nit N2) |

The asymmetric fixture (3 graded + 1 R2-skipped, `checked == 3`) does exactly the job round 2
asked of it, and it is the only fixture in the file whose count is not 2 — so a constant can no
longer satisfy the set.

### Coverage floor — `RepoCoverageFloorTests` (`:591-621`)
**It is not a number that can never move.** It failed under M-N10a (162→45), M-N10b (45),
M-RA3 (50), M-RA4 (50), M-N4a (0), M-N4b (2) and W8 (130) — seven independent mutations. It is
also the *only* test that caught M-N4b. It is a real tripwire. Its calibration is the subject of
finding S1 below.

### Fleet suite
| # | Mutation | Caught? |
|---|---|---|
| M16 | `needs_human` drops `p["flow"] in ATTENTION` | **YES** — 3 tests (was 2) |

---

## New findings

### [should-fix] The coverage floor's unique catch-zone is narrower than its docstring claims, and `assertGreaterEqual` passes at exactly the floor — a whole tree can go dark at 151 and only a fixture *accident* notices
- `tests/test_check_links.py:591-621` (docstring `:591-606`, assertion `:615-621`)
- The docstring says the test's job is to notice "a skip rule quietly widened, or a mask quietly
  grown". I measured nine such widenings against the real tree. Six of them land **at or above**
  the 140 floor and the floor does not fire:

  | widening | repo `checked` | floor fires? | anything else fires? |
  |---|---|---|---|
  | `BACKTICK_EXT_RE` drops `.py` | 161 | no | no |
  | `EXCLUDE_PREFIXES += ".github/"` | 158 | no | **no — fully silent** |
  | R4 widened to skip `docs/` | 154 | no | **no — fully silent** |
  | `EXCLUDE_PREFIXES += "docs/"` (entire tree unscanned) | 151 | no | yes, *incidentally* |
  | `BACKTICK_EXT_RE` narrowed to `.md` only | 142 | no | yes |
  | R2 widened (`FAMILY_CHARS_RE` += `-`) | **exactly 140** | **no** | yes, *incidentally* |
  | backtick token requires 2+ slashes | 130 | **yes** | yes |
  | `{devflow_root}` rewrite removed | 50 | yes | yes |
  | frontmatter masks to EOF | 45 | yes | yes |

- Two of the "caught" rows are caught by coincidence, not by design, and would stop being caught
  under an unrelated edit: the `docs/`-exclusion row fails only because
  `DevflowRootLinkAnchoringTests`'s fixture happens to be named `docs/autonomy.md`; the R2 row
  fails only because `EscapeAndReturnContainmentTests`'s second subTest directory happens to be
  named `devflow-fork` and so contains a `-`. Rename either fixture and both widenings become
  silent in both CI gates.
- The R2 row also demonstrates an off-by-one: it lands on **exactly 140**, and
  `assertGreaterEqual(result.checked, 140)` **passes** at the floor. The boundary the test names
  is not itself excluded.
- **Judgment on 140 as a value: it will not false-red for phases 02-04, and I would not raise it
  blindly.** Measured distribution of the 162: `plugins/devflow/skills` 110 (68%),
  `plugins/devflow/references` 16, repo root 14 (README = 10), `docs/` 11,
  `plugins/devflow/agents` 7, `.github` 4. Largest single file is 11
  (`flow-execute/SKILL.md`). Phases 02-04 touch only the 25 references in the repo root +
  `docs/` — and they *move* prose rather than delete it (02: README → `docs/`; 03: README
  rewrite that adds a docs index; 04: repointing, with an explicit "no substantive content was
  lost" audit). Losing 23 references to a legitimate edit would require deleting 23 path
  mentions outright from a 25-reference working set, which phase 04's own goal forbids. The
  direction of travel is upward. A false red is unlikely.
- The problem is the other side: 68% of the corpus sits in a tree phases 02-04 never touch, and
  a single global floor spends all its headroom protecting that stable 110 instead of the 25
  that are actually in motion.
- Fix (small, and it is the calibration that earns the test its keep): keep 140 as the global
  backstop but add a second, tight per-subtree floor over the part phases 02-04 do not touch —
  `plugins/devflow/**` is 133 references today, so a floor of 128 there has real teeth and zero
  false-red risk from this PR's remaining phases. Optionally add a matching floor over
  `docs/` + repo root once phase 03 lands and that number stabilizes. While editing, use
  `assertGreater(result.checked, 139)` (or floor 141) so the boundary case is excluded, and put
  the measured 162 into the failure message so a drift is diagnosable from the CI log alone.

### [nit] The module docstring now makes a false claim about the suite — the same docstring-vs-behavior mismatch round 1 called blocking for R1
- `tests/test_check_links.py:1-7`: *"Every test drives 01-01's pinned seam, check(root), against
  a fixture it builds and tears down — never the CLI, **never this repo's own tree**."*
- `RepoCoverageFloorTests` (`:591`) reads this repo's own tree. Its own docstring is scrupulous
  about the exception ("This is the one test in this suite that deliberately runs against the
  real repo tree"), but the file header was not updated to match, so the file now opens with a
  statement a reader will take at face value and act on. Round 1 escalated exactly this pattern
  (the `SkipRuleTests` docstring asserting a property R1's fixture did not have).
- Fix: one clause — "…never the CLI, and never this repo's own tree except `RepoCoverageFloorTests`,
  which exists precisely to measure it."

### [nit] Counting the external-URL skip as `checked` inflates the count undetected — and inflation is what blunts the floor
- `scripts/check-links.py:161-162`; `tests/test_check_links.py:246-289`, `:591-621`
- **M-N4d**: `return None, False` → `return None, True` on the URL early-return. Suite `OK`; real
  repo goes from `162 checked` to **`178 checked`**. Nothing in either CI gate notices.
- On its own that is the same class as round 2's M-N4c, just through the one skip path the new
  fixture does not cover (it covers the R1-R5 path). It matters slightly more than a cosmetic
  miscount because the floor is a *lower* bound: any inflation raises the operating point away
  from the floor and buys a future mask-widening that much more room before the tripwire fires.
- Fix: add an `https://` link to the `ReferenceCountTests` asymmetric fixture and keep the
  expected count unchanged. That closes M-N4d and round 1's untested-URL-skip nit (M11) in the
  same line.

### [nit] `EscapeAndReturnContainmentTests`'s two subTests exercise the same path
- `tests/test_check_links.py:567-578`
- Each subTest writes a link naming *its own* directory (`../devflow/...` inside `devflow`,
  `../devflow-fork/...` inside `devflow-fork`), so both reproduce the identical escape-and-return
  shape; every mutation I ran either failed both or failed neither (the sole exception, W6, is an
  artifact of the `-` character, not of the property under test). The round-2 S-1 scenario was
  *fixed* link text yielding different verdicts under different directory names — which this does
  not pin. That is fine: the test pins the strictly stronger invariant (reject at the reference
  level, before the filesystem is consulted), which is the right property. Recording it only so
  nobody reads the parametrization as coverage it is not.

---

## Remaining coverage gaps (whole suite, ranked)

1. **`main()`'s exit-code contract — the CI gate itself.** `.github/workflows/lint.yml:22` runs
   `python3 scripts/check-links.py` and reads only its exit code. **M22** (`main()` returns 0
   unconditionally) → suite `OK`. The link check can be turned into a no-op and nothing notices.
   `MainSignatureTests` (`:428-435`) pins arity only. Round 1 deferred this as "never the CLI",
   but `RepoCoverageFloorTests` has already crossed that line for a weaker reason, so the
   rationale no longer holds. Two cases (`check()` returning failures → 1; returning none → 0)
   close the highest-consequence branch in the file.
2. **`_parse_link_target` + the external-URL skip.** **M13** and **M11** both leave the suite
   green *and* the real-repo check clean. This is now the gap most exposed to what is coming:
   only **2 of the repo's 162 references are markdown links** (160 are backticked prose tokens),
   and phase 03's deliverable is explicitly a **docs index** — the first substantial body of
   markdown links in this repo. Title-stripped links `[x](p "T")`, angle-bracket links
   `[x](<p>)` and `https://` targets have no fixture at all. One fixture covers all three.
3. **Anchor slugging beyond lowercase + space.** **M8** (punctuation strip), **M10**
   (duplicate-heading `-1` suffix), **M14** (setext headings), **M15** (`_strip_inline_markdown`),
   **M23** (trailing-`#` ATX stripping), **M24** (`_heading_slugs` ignoring the frontmatter mask)
   — all six leave the suite green. D-12 accepted this abstention on the premise that `docs/` had
   no duplicate, inline-code or setext headings. Phases 02-03 create new `docs/` pages and an
   index that links into their `#anchors`; that premise expires with this PR. This is the gap I
   would fund second after `main()`.
4. **`Failure.reason` for `no such heading`.** **M20b** still green. One `assertEqual` at
   `tests/test_check_links.py:75-84`.
5. **The fleet suite's unsanitized git config.** Not a coverage gap but a runnability defect —
   9 of 21 tests error under `commit.gpgsign = true`. Reproduced above; two-line fix.
6. **`_check_file`'s unreadable-file path.** **M21** (`OSError` branch returns `[], 0` instead of
   a `Failure`) → suite `OK`. A file the checker cannot read reports clean — the fail-closed
   violation this whole file exists to prevent, in the one branch nothing covers.
7. **Multi-base resolution, positive direction (M9).** Suite green, but the real-repo CI step
   goes red with 10 failures, so it is defended. One-line fixture addition.
8. **`failures.sort()` ordering.** **M-S1** (sort removed) → suite `OK`. Asserted in
   `VERIFICATION.md` prose only.
9. **`check(root)` on a non-repo root.** Fail-closed by construction (`RuntimeError` confirmed);
   one case would pin it.

---

## Test isolation

- **No test mutates the real repo.** Verified by full-tree `(path, mtime, size)` snapshot before
  and after a clean suite run, excluding `__pycache__`: byte-identical hash both sides.
  `scripts/check-links.py` md5 matches `git show HEAD:scripts/check-links.py`. `git diff HEAD`
  is empty; `git status --porcelain` shows only the untracked `.planning/reviews/`.
  `RepoCoverageFloorTests` touches the real tree read-only (`git ls-files -z`, `open(...)`).
  The only files written are gitignored `.pyc` (`.gitignore:5-6`).
- **cwd-independent.** `python3 /home/brianf/dev/devflow/tests/test_check_links.py` from `/tmp`
  → `Ran 39 ... OK`; `tests/test_flow_fleet.py` from `/tmp` → `Ran 21 ... OK`.
- **`tests/test_check_links.py` — clean and now host-independent.** `tempfile.mkdtemp` +
  `addCleanup(shutil.rmtree)` throughout, including the new `EscapeAndReturnContainmentTests`
  (which builds a named subdirectory inside its own tempdir parent) and `GIT_ENV` on every git
  invocation. Immune to both hostile global configs I tried.
  The one deliberate exception is `RepoCoverageFloorTests`, which is intentional and documented
  in its own docstring (but see nit above about the file header). Its consequences, stated
  plainly and not raised as findings: the suite now fails outside a git checkout
  (`RuntimeError`, not a skip), it reads the git *index* so a partially-staged doc restructure
  shifts the number, and it does not pass `GIT_ENV` to its `git ls-files` (harmless — global
  config does not change tracked-file enumeration).
- **`tests/test_flow_fleet.py` — hermetic w.r.t. `~/.devflow/fleet.json` as of this round
  (verified in both directions), still leaking on the global gitconfig** (should-fix above).
  `tempfile.TemporaryDirectory` + `tearDown` cleanup; no writes outside it.

---

## Summary
**0 blocking, 1 should-fix, 3 nit (new only).**

Plus one carry-over re-ranked on new evidence: the fleet suite's unsanitized git config moves
**nit → should-fix** (reproduced: `FAILED (errors=9)` under an ordinary `commit.gpgsign = true`).

Round-2 disposition: 1 blocking **RESOLVED**, 2 should-fix **RESOLVED**, 1 should-fix
**NOT RESOLVED but downgraded to nit** (CI's second gate covers it), 1 should-fix **PARTIALLY**
(one reason string left), 3 nits NOT RESOLVED (one upgraded), 1 nit unchanged/accepted.

**Every test added this round bites under mutation.** 39 mutation cycles, 30 caught, 9 survivors
— and all 9 survivors are pre-existing gaps listed above, not defects in the new tests.

Candidates for the PR's open-items list, in the order I would fund them: `main()`'s exit code;
`_parse_link_target` + the URL skip (elevated — phase 03 ships the repo's first real body of
markdown links); anchor slugging beyond lowercase+space (D-12's premise expires with phases
02-03); the fleet suite's git-config sanitation; the per-subtree coverage floor; the
`no such heading` reason string; `_check_file`'s `OSError` branch; the positive multi-base
fixture; `failures.sort()`; `check()` on a non-repo root.

## Recommendation
Yes — the suite is a trustworthy gate for phases 02-04 on the failure modes those phases can
actually cause (masks widening, skip rules widening, coverage collapsing, links resolving
against the wrong base), and it is the first round where nothing added regressed; the one thing
I would fix before phase 03 rather than after is the untested `_parse_link_target`/URL path,
because phase 03's docs index is the first work in this repo that leans on it.
