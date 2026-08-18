# Findings — reuse

## Summary
0 blocking, 2 should-fix, 4 nit

## Findings

### [should-fix] `{devflow_root}` resolution reimplemented with semantics that diverge from the existing checker
- `scripts/check-links.py:137-138` and `scripts/check-links.py:220-225` vs `scripts/validate-plugin.py:174-178`
- Two checkers now resolve `{devflow_root}/...` references and they disagree about directories. `validate-plugin.py` deliberately carves them out (`if "*" in ref or ref.endswith("/"): continue`, then `os.path.exists`, which also accepts a directory). `check-links.py` resolves through `_resolve`, which is `os.path.isfile` only, and has no directory carve-out. Confirmed empirically against a temp fixture: a link to `plugins/devflow/templates/` and to `{devflow_root}/templates/` both report `target does not exist` even when the directory exists and is tracked.
- To be explicit about what is *not* wrong here: neither checker is dead or superseded, so conventions.md → Dead code does not apply. Their coverage is genuinely complementary and I verified both halves. `validate-plugin.py` catches unbackticked prose refs (`plugins/devflow/references/hosts.md:40`, `plugins/devflow/skills/flow-status/SKILL.md:30`, `plugins/devflow/skills/flow-workstream/SKILL.md:15`) and the one ref inside a `.py` file, none of which `check-links.py` sees — it only inspects markdown links and backticked tokens ending `.md|.py|.json|.yml`. Conversely `check-links.py` catches `docs/status-contract.md`, which is outside `plugins/devflow/` and therefore outside `validate-plugin.py`'s glob entirely. Keep both.
- Failure scenario (latent, not live): today no tracked markdown outside `.planning/` and `templates/` contains a directory-target link — I grepped for `](path/)` and got zero hits — so CI is green. The first doc that writes a normal directory link, e.g. `see the [templates](plugins/devflow/templates/)`, fails the new `Check internal links` step in `.github/workflows/lint.yml` on a correct link. The author then has a lint gate contradicting the sibling gate in the same workflow, which permits exactly that reference.
- Suggested fix: in `_resolve`, accept `os.path.isdir(candidate)` as well as `os.path.isfile`, matching `validate-plugin.py`'s `os.path.exists`. One line, and it aligns the two gates rather than adding a shared module.

### [should-fix] `_frontmatter_mask` exists but only one of the two scanning paths uses it
- `scripts/check-links.py:268-276` (definition), `:281-282` (used by `_heading_slugs`), vs `:96-100` (`_check_file` builds only `_code_fence_mask`)
- The file has two passes over markdown lines. `_heading_slugs` masks both code fences and frontmatter; `_check_file` masks only code fences. So a path-shaped token inside YAML frontmatter is treated as prose and checked, in a block that is not markdown and where a `.md`-suffixed value is a data field, not a reference. The helper to fix this is already written and already imported into the other pass — this is an unused-at-the-second-call-site helper, not a missing capability.
- Currently latent: I scanned every tracked `.md` outside `.planning/` for backticked path tokens or link syntax inside frontmatter and found none, so this produces no failure today.
- Suggested fix: in `_check_file`, compute `front_mask = _frontmatter_mask(lines)` alongside `fence_mask` and skip lines where either is set — the same two-mask guard `_heading_slugs` already uses at `:288`.

### [nit] `_bases_for` re-deduplicates a list that cannot contain duplicates, and tests a condition that cannot hold
- `scripts/check-links.py:185-192`
- Two pieces of unreachable-effect code in one 12-line function. (a) The `ordered` loop at `:188-192` can never drop anything: `bases` starts `[""]`, `own_dir` is only appended when truthy so it never collides with `""`, and the `plugins/devflow` append at `:186` is already guarded by `not in bases`. I confirmed by probing `_bases_for` across representative paths — every result is already unique before the loop runs. (b) The `relfile == DEVFLOW_ROOT_TARGET.rstrip("/")` disjunct at `:185` compares a file path to the bare directory `plugins/devflow`; `relfile` always comes from `git ls-files`, which lists files, never directories, so the disjunct is never the reason the branch is taken — `startswith` already covers every reachable case.
- Suggested fix: delete `:188-192` and `return bases`; drop the `==` disjunct from `:185`.

### [nit] The two reference-kind loops in `_check_file` are near-identical copy-paste
- `scripts/check-links.py:101-107` and `:108-116`
- The blocks differ only in the regex, how the token is pulled out of the match, one extra filter on the backtick branch, and the `is_link` flag; the `_check_reference(...)` call and the `if failure: failures.append(failure)` tail are byte-identical. Small enough that the duplication is cheap today, but a third reference kind or any change to the call signature has to be made twice.
- Suggested fix (optional): drive both from a small local list of `(regex, extractor, is_link)` tuples, or leave it — at two branches this is a judgment call, not a defect.

### [nit] `_top_level_entries` is recomputed from scratch for every token, while headings are cached
- `scripts/check-links.py:195-207`, called from `_r5_skip` at `:214-216`
- `_check_file` threads a `heading_cache` through precisely to avoid re-reading target files, but `_top_level_entries` walks the whole `all_files` list on every skip-rule evaluation, once per base per token. The derived structure is a pure function of `(base, all_files)` and is a natural cache peer to `heading_cache`.
- Not a performance problem at this repo's size — 105 tracked files, full run measured at 0.10s — so this is about the inconsistency with the caching the file already does, not about speed.
- Suggested fix (optional): memoize per base in a dict threaded alongside `heading_cache`, or accept it as fine at this scale.

### [nit] Redundant local `import datetime` left behind by this change
- `tests/test_flow_fleet.py:160`, shadowing the module-level import this diff added at `:8`
- The diff added `import datetime` at module scope to compute `TODAY`. The pre-existing function-local `import datetime` inside `ScanTests.scan` is now redundant. conventions.md → Dead code asks for the superseded path to go in the same change; there is no named contract keeping this one.
- Suggested fix: delete `tests/test_flow_fleet.py:160`.

## Explicit non-findings

**Do not extract a shared module.** I checked each candidate the brief named and none of them justifies one:
- *Git invocation helpers*: `check-links.py:68-83` runs `git rev-parse --show-toplevel` and `git ls-files` with bespoke fail-closed `RuntimeError`s that `main` converts into `could not check:` + exit 1. `flow-fleet.py:45` has a `git(repo, *args)` helper whose contract is the opposite — it swallows errors and returns a `GIT-UNKNOWN` sentinel for display. Same subprocess call, deliberately different failure semantics, both correct for their caller. Merging them would force one of the two to adopt the other's error contract.
- *Repo-root resolution*: `validate-plugin.py:10` uses `__file__`-relative pathing; `check-links.py:68` shells out to git. Six lines total, and the git form is the right one for a checker that must fail closed when run outside a repo.
- *File enumeration*: `validate-plugin.py:81-82,160` globs a fixed subtree; `check-links.py:77` reads the git index. Different sets by design.
- *Frontmatter parsing*: `validate-plugin.py:32-45` returns a key→value dict; `check-links.py:268` returns a boolean line mask. Same delimiter, unrelated outputs.
- The structural argument dominates all of the above: these scripts are standalone hyphenated files (`check-links.py`, `validate-plugin.py`, `flow-agent.py`, `flow-fleet.py`), not importable as modules without `importlib.util.spec_from_file_location` — which is exactly the ceremony the tests already pay three times. There is no package, no `__init__.py`, no `src/`, and two of the four live inside the distributed plugin payload while two live in the repo's own tooling. A shared module would either be un-importable by name or would couple the plugin payload to repo-root tooling. Duplication is the cheaper side of that trade here.

**Per-file test independence is the right call.** `tests/test_check_links.py:19-21`, `tests/test_flow_agent.py:14-16` and `tests/test_flow_fleet.py:27-29` each repeat the same 3-line `spec_from_file_location` / `module_from_spec` / `exec_module` loader. The fixture builders are *not* duplicated in any meaningful sense: `test_check_links.CheckLinksTestCase.make_repo` takes a `{path: content}` dict, inits and stages without committing (because `check()` reads the index), and cleans up via `addCleanup`; `test_flow_fleet.ScanTests.project` writes a fixed `.planning/STATE.md` + `JOURNAL.md` shape and must commit; `test_flow_agent` builds fake executables on `PATH` and never inits a repo at all. Three different fixture shapes sharing one three-line import idiom is not worth a `tests/_harness.py` in a stdlib `unittest discover` suite where each file is independently runnable. Whole suite: 49 tests, OK (2 skipped).

One divergence inside that idiom is worth naming, though it is below nit: `test_check_links.py:25` isolates git config (`GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_SYSTEM=/dev/null`) for its fixtures, and `test_flow_fleet.py:152-157` does not. The fleet fixtures pass `-b main` and inline `-c user.email`/`-c user.name`, which covers the two settings that actually bite, so this is not currently a bug — but the newer file established the stronger idiom and the older one was edited in this same diff.

**No dead code introduced by the new module.** Every function in `check-links.py` has a live caller: `check` ← `main` and all 12 tests; `_repo_root`/`_all_tracked` ← `check`/`main`; `_check_file`, `_parse_link_target`, `_check_reference`, `_skip`, `_bases_for`, `_top_level_entries`, `_r5_skip`, `_resolve`, `_check_anchor`, `_code_fence_mask`, `_frontmatter_mask`, `_heading_slugs`, `_strip_inline_markdown`, `_slugify` all reachable from `check`. The CLI is wired in `.github/workflows/lint.yml:20-21`. No pre-existing code path was superseded, so nothing was owed a deletion.
