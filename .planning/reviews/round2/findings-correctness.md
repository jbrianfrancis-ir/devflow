# Findings — correctness (round 2)

Method: every disposition and every new finding below was reproduced by driving
`MODULE.check(root)` over throwaway `git init`'d fixtures, or by running the CLI / the
suite. Guard-liveness claims are mutation-proved. Nothing here is read-only reasoning.

Repo baseline after the three fix commits, verified three ways in one process
(`check(_repo_root())`, `check(abspath("."))`, subprocess CLI):

```
0 failures, 162 references checked      exit 0
```

The count is **non-vacuous and unchanged**: I reran the pre-fix checker
(`git show 31e858b:scripts/check-links.py`) over the same tree with the same skip rules
and it also grades **162** references. So the fixes cost no coverage and introduced no
false rejection on the real tree. 352 references are extracted post-mask; 162 are graded;
190 are skipped by rule (R4 `.planning/` 136, url 16, R2 13, R5 13, R3 10, R1 2).

> **Tooling caveat, same as round 1.** Two Bash results in this session returned values
> the code does not produce (`0 references checked` for the repo baseline; `336 checked`
> from an instrumented run; `failures=0` for a fixture that does report an unterminated
> fence). Every one was contradicted on re-run. Everything below was re-verified at least
> once; where a first result disagreed with a second, the second (reproducible) one is
> what I report.

## Round 1 disposition

- **[blocking] Links resolved against repo root, not the referring file's dir** — **RESOLVED.**
  `scripts/check-links.py:263` now uses `[os.path.dirname(relfile)]` for `is_link`.
  Scenario A (`sub/a.md` → `docs/guide.md#beta`, own-dir copy has the heading) → `0 failures`,
  own-dir base wins. Scenario B (wrong-depth link, root copy only) → `sub/a.md:3: docs/guide.md
  — target does not exist`. Both directions fixed. Mutation M3 (revert to `_bases_for`) → 2 test
  failures, so it is pinned.
- **[blocking] Anchor slugging collapses runs of whitespace** — **NOT RESOLVED.** `_slugify`
  at `:384` is still `re.sub(r"\s+", "-", text)`; the commit series never touched it.
  Re-reproduced verbatim: `[x](docs/conv.md#credential-modes--push-canary)` against
  `## Credential modes & push canary` → `no such heading`, while the single-hyphen form
  github.com 404s → `0 failures`. I swept the real tree: **22 headings currently in scope
  have a slug that diverges from github-slugger**, e.g. `docs/status-contract.md:1`
  (`devflow-status-contract--the-agent-facing-interface` vs the tool's single hyphen),
  `plugins/devflow/references/conventions.md:14`
  (`git-workflow--branch--origin--pr-upstream` vs `git-workflow-branch-origin-pr-upstream`),
  `plugins/devflow/references/aspire.md:55` (`failure--fix`). Still latent only because there
  are **0** `](#` references in scope.
- **[should-fix] `_resolve` tests the filesystem instead of the tracked list** — **PARTIALLY.**
  Sub-item 2 (escaping the repo) is fixed by the containment check at `:272-273`:
  `[x](../SECRETS.md)` and `[y](../../../../etc/hostname)` now both report
  `target does not exist`. Sub-items 1 and 3 are untouched — `:267` still calls
  `os.path.isfile`/`os.path.isdir` on disk. Re-reproduced: a `.gitignore`d, untracked
  `docs/local.md` present on disk still satisfies `[x](docs/local.md)` → `0 failures`, and
  the same run in a fresh CI checkout fails. Case-folding on macOS/Windows checkouts is
  unchanged by construction.
- **[should-fix] A link to a directory is reported missing** — **RESOLVED.** `[refs](docs)`,
  `[a](docs/)`, and `[b](docs#frag)` all pass; the fragment-against-a-directory case returns
  without heading-grading (`:193-195`). Mutation M4 (drop `isdir`) → 2 test failures.
- **[should-fix] Anchors into non-markdown files graded as heading slugs** — **NOT RESOLVED.**
  Re-reproduced: `[seam](scripts/thing.py#L10)` → `no such heading #L10`. `_check_anchor`
  at `:280` still opens whatever `_resolve` returned. See new finding N4 — the same code
  path now also crashes the run on a binary target.
- **[should-fix] Reference-style links never extracted** — **NOT RESOLVED.** `LINK_RE` at `:21`
  is unchanged. Re-reproduced: `See [guide][g].` + `[g]: docs/missing.md` → `0 failures`,
  `checked=0`.
- **[should-fix] Backticked-path extension allowlist too narrow** — **NOT RESOLVED.**
  `BACKTICK_EXT_RE` at `:23` is still `\.(md|py|json|yml)$`. Re-reproduced: `` `ci/nope.yml` ``
  is reported, `` `ci/deploy.yaml` `` and `` `ci/run.sh` `` are silently unchecked.
- **[should-fix] "Skipped" and "checked" indistinguishable in output** — **PARTIALLY.**
  `main` at `:77-78` now prints `0 failures, 162 references checked`, which is the half that
  matters most, and the counter is accurate (see New finding N6 for the two ways it still
  misleads). The skipped count asked for is not printed: the line reads like full coverage
  while 190 of 352 extracted references were never graded.
- **[nit] `main()` silently checks whichever repo the cwd is in** — **PARTIALLY.** The dead
  `argv` parameter is gone (`:68`) and no caller passes one (`.github/workflows/lint.yml:21`
  is the only invocation). The cwd behaviour itself is unchanged: `_repo_root()` still shells
  `git rev-parse --show-toplevel` in the ambient cwd.
- **[nit] Fragment matching is case-insensitive** — **NOT RESOLVED.** `[x](#Doc-Heading)`
  against `# Doc Heading` → `0 failures`; github.com 404s it.
- **[nit] `[top](#)` reported broken** — **NOT RESOLVED.** Re-reproduced: `# — no such heading #`.
- **[nit] `(` truncation and `%`-escapes** — **NOT RESOLVED.** Re-reproduced both:
  `docs/note(1 — target does not exist` and `docs/my%20note.md — target does not exist`,
  with both real files present and tracked.
- **[nit] Indented code blocks / inline code spans not masked; unterminated fence silent** —
  **PARTIALLY.** The unterminated-fence half is fixed and is now a `Failure` (`:119-125`),
  mutation-pinned (M2 → 1 test failure). Indented code blocks and inline code spans are
  unchanged. But the same silent-mask bug was **re-introduced next door** in the frontmatter
  mask added by the same commit series — see New finding N1.
- **[nit] `_strip_inline_markdown` deletes `_`** — **NOT RESOLVED** (`:377`); still symmetric,
  `#snake_case_thing` passes.
- **[nit] Minor slugger/parse divergences** — **NOT RESOLVED.** Re-reproduced the BOM case
  (`docs/bom.md#title` → `no such heading #title`) and the indented-ATX case
  (`   ### Indented` → `no such heading #indented`). The dead `_bases_for` branch is still
  at `:224`.

## New findings

### [blocking] The new frontmatter mask silently swallows content to EOF — the exact fail-closed bug the same commit fixed for fences
- `scripts/check-links.py:116` and `:127` (mask applied in `_check_file`), `:323-331` (`_frontmatter_mask`)

**What is wrong.** 577ed13 (S5) started applying `_frontmatter_mask` in `_check_file`. That mask
opens on *any* file whose first line is `---` and, if no closing `---` is ever found, marks
**every line to EOF** — with no failure, no warning, and no contribution to the coverage count.
1a2c384 (B2) had just established the opposite rule one screen up: an unterminated fence must be
reported because "an unclosed fence masks every line to EOF — that must be visible as a failure,
not a silent drop in coverage (conventions.md → fail-closed)". The sibling mask added in the same
round has no such guard.

**Reproduced — whole file silently unchecked:**
```
doc.md        "---\n\nSee [x](docs/missing.md).\n\nAnd [y](docs/also-missing.md).\n"
docs/real.md  "# R\n"
```
→ `checked=0 failures=0`. Removing only the leading `---` (control) → `checked=2 failures=2`,
both broken links correctly reported. So two genuinely broken links are hidden by one leading
`---`, and the output is indistinguishable from a clean file.

**Reproduced — partial, and more likely: a doc that opens with a thematic break.**
```
doc.md   "---\n\n# Title\n\nSee [a](docs/missing1.md).\n\nfiller...\n---\n\nSee [b](docs/missing2.md).\n"
```
→ only `doc.md:14: docs/missing2.md` is reported. `_frontmatter_mask` returns
`[True]*12 + [False, False]` — lines 1-12, including the broken `[a](docs/missing1.md)`, are
masked because the checker treated a horizontal rule as a frontmatter opener and the *next*
`---` separator as its terminator.

**Why it matters now.** It is latent on today's tree — I swept all 50 scoped files: 33 have
frontmatter, **0** references sit inside a frontmatter region, and **0** files are fully masked.
But phases 02-04 are document-splitting work, and splitting a file that has frontmatter is the
single easiest way to produce a fragment whose first line is `---` with no closer. CI then stays
green while an arbitrary share of a document goes ungraded, which is precisely the
"guard reporting success it did not establish" failure `conventions.md` names.

**Suggested fix.** Mirror the fence treatment exactly: have `_frontmatter_mask` return
`(mask, unterminated_at)` and emit a `Failure` when a `---` opener never closes. Separately,
require the opener to be line 1 *and* a closer to exist before masking anything — if there is no
closing `---`, treat the file as having no frontmatter rather than as being entirely frontmatter.
That single change makes the failure mode fail-open-loud instead of fail-closed-silent.

### [should-fix] Strict resolution also applies to `{devflow_root}` links, contradicting the code's own comment
- `scripts/check-links.py:263` (`bases = [os.path.dirname(relfile)] if is_link else _bases_for(relfile)`),
  `:173-174` (the rewrite), `:260-262` (the comment)

**What is wrong.** The comment directly above `:263` says "Backticked/`{devflow_root}` tokens are
base-ambiguous by design (D-08/D-09) and keep the multi-base walk." The code does not implement
that: the branch keys on `is_link`, not on whether the token was a `{devflow_root}` one. The
rewrite at `:173-174` happens *before* the branch, so by the time `_resolve` runs, a
`{devflow_root}` reference written as a markdown link is indistinguishable from an ordinary
relative link and gets single-base, own-dir resolution.

**Reproduced:**
```
docs/autonomy.md                             "# A\n\nSee [conv]({devflow_root}/references/conventions.md).\n"
plugins/devflow/references/conventions.md    "# C\n"
```
→ `docs/autonomy.md:3: plugins/devflow/references/conventions.md — target does not exist`
(it looked for `docs/plugins/devflow/references/conventions.md`).

Two controls confirm the mechanism: the identical token **backticked** → `0 failures`; the
identical **link** written from a root-level `README.md` → `0 failures`. So the failure appears
and disappears purely with the referring file's depth, which is the opposite of what a
root-anchored placeholder means.

**Why should-fix, not blocking.** The repo has 134 `{devflow_root}` references and **0** of them
are in link form today (all backticked), so nothing is red. Unlike the round-1 blocking case, this
is a niche construct rather than ordinary markdown. But a `{devflow_root}` token is a root-anchored
placeholder by definition — resolving it relative to the referring file is never right — and any
non-root doc that writes one as a link turns CI red on a correct reference.

**Suggested fix.** Set a flag when the `DEVFLOW_ROOT_PREFIX` rewrite fires at `:173-174` and pass
it through to `_resolve`; rewritten tokens should resolve against the repo root only (not the
own-dir base and not the multi-base walk), regardless of `is_link`.

### [should-fix] The containment check rejects a git-tracked symlink that points outside the checkout
- `scripts/check-links.py:272-273`

The check compares `os.path.realpath(candidate)` against `os.path.realpath(root)`. That correctly
kills `../` traversal and symlink escapes — but git tracks symlinks as blobs, and github.com serves
the symlink's own URL without 404ing. A tracked in-repo symlink whose target lives outside the
checkout is therefore a legitimate reference that the checker now rejects.

**Reproduced:** `docs/ext.md` is a symlink to a file in a sibling temp dir; `git ls-files` confirms
it is tracked (`['doc.md', 'docs/ext.md', 'docs/keep.md']`); `[e](docs/ext.md)` from `doc.md`
→ `doc.md:3: docs/ext.md — target does not exist`.

**I could not make it false-reject anything else.** Probed and clean: repo root reached through a
symlinked path (the macOS `/tmp` → `/private/tmp` shape) → resolves; an in-repo symlinked directory
pointing at another in-repo directory → resolves; `../` from a subdirectory back into the repo
(`sub/doc.md` → `../docs/guide.md`) → resolves; nested `../../` and `./` at depth 3 → all resolve.
Repo baseline unchanged at 0 failures.

**Suggested fix.** Before rejecting, check membership of the repo-relative normalised path in the
tracked set — a path git tracks is by definition inside the repo, however its realpath lands. That
is the same fix round 1 asked for on the untracked-file half, and it subsumes both.

### [should-fix] R5 silently skips a single-segment link target that does not exist — the commonest broken-link shape after a doc split
- `scripts/check-links.py:249-256` (`_r5_skip`), reached from `:185`

For a target with no `/`, the "first segment" is the whole filename. R5 asks whether that name is a
top-level entry under any base; for a *broken* link the answer is always no, so it is skipped —
never graded, never counted, never reported. The rule's premise ("names nothing under any base, so
it probably isn't a repo path") is sound for a backticked token but false for `[text](target)`,
where a bare `something.md` is unambiguously a repo path.

**Reproduced:**
```
docs/a.md     "# A\n\nSee [b](missing.md) and [c](./missing2.md).\n"
docs/real.md  "# R\n"
```
→ `checked=1 failures=1`, reporting only `./missing2.md`. `[b](missing.md)` — same file, same
directory, equally broken — is silently dropped, because `./` makes R5 bail early at `:251` while
the bare form does not. The multi-segment control (`[b](docs/missing.md)`) is correctly reported.

This is **pre-existing, not introduced by the fixes** — I am raising it because round 1 did not,
and because it now sits directly against the grain of B1: the fix made multi-segment links strict
while sibling-file links stay fail-open. Latent on today's tree (0 links are R5-skipped), but a
sibling link to a file that was just moved is exactly what phases 02-04 generate.

**Suggested fix.** Do not apply R5 when `is_link` is true and the target has no whitespace — a
markdown link target is always a path. At minimum, exempt single-segment targets carrying a known
document extension.

### [should-fix] A fragment against a binary target aborts the entire run with a location-less error
- `scripts/check-links.py:287` (`open(..., encoding="utf-8")`), `:290-291` (`except OSError` only)

`_check_anchor` catches `OSError` but not `UnicodeDecodeError`. S2 added an `isdir` guard at `:193`
so a directory target is no longer heading-graded — the non-markdown *file* case in the same branch
was left as-is, and it does not merely misgrade, it crashes.

**Reproduced:** `[img](assets/logo.png#foo)` against a tracked PNG →
`check(root)` raises `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x89 in position 0`.
Through the CLI the blanket `except Exception` at `:72` catches it, so it is fail-closed:
`could not check: 'utf-8' codec can't decode byte 0x89 in position 0: invalid start byte`, exit 1 —
but with no file, no line, no target, and **every other file in the repo left unchecked**. One
image reference kills the whole gate and gives the author nothing to act on. `check(root)` is the
documented programmatic seam (01-01) and it raises outright.

**Suggested fix.** Gate `_check_anchor` on the resolved target ending in `.md` (which also fixes
the still-open round-1 `#L10` finding), and widen the `except` to `(OSError, UnicodeDecodeError)`
as a backstop so one unreadable file degrades to one `Failure`, not a dead run.

### [nit] "N references checked" reads like full coverage while 54% of extracted references were skipped
- `scripts/check-links.py:77-78`

`0 failures, 162 references checked` is accurate for what it counts — I verified the counter's
semantics against every branch of `_check_reference`: `http/https/mailto` links are excluded,
`_skip`ped tokens are excluded, and resolved-pass, resolved-fail, bare-`#frag` and backticked
references are all counted once each (fixture with one good link, one broken link, one URL and one
backticked path → `checked=3, failures=1`). And it is a real signal: I confirmed the number matches
an independent recount of the same tree. The problem is what it omits — 352 references are
extracted post-mask and 190 are dropped by rule, so a reader sees "162 checked" with no denominator
and no way to notice if a skip rule widens. Round 1 asked for `N checked, M skipped`; the skipped
half is the half that detects a coverage regression.

### [nit] The unterminated-fence failure is not counted, so output can read "1 failure(s), 0 references checked"
- `scripts/check-links.py:119-125`

The `Failure` appended for an unclosed fence never increments `checked`. Reproduced: a file that is
nothing but a fence opener and one link → `1 failure(s), 0 references checked`. Harmless today
because the failure line is printed above it, but the summary line contradicts itself.

## Guards I mutation-tested (all pinned — no finding)

Each mutation applied to `scripts/check-links.py`, full suite run, file restored; tree verified
clean afterwards. Baseline suite: `Ran 64 tests ... OK (skipped=2)`.

| # | Mutation | Result |
|---|---|---|
| M1 | containment check → `if True:` | FAILED (2) |
| M2 | unterminated-fence failure → `if False:` | FAILED (1) |
| M3 | strict link resolution → `_bases_for(relfile)` | FAILED (2) |
| M4 | directory acceptance → `isfile` only | FAILED (2) |
| M5 | frontmatter mask dropped from `_check_file` | FAILED (1) |
| M6 | `checked` counter never incremented for links | FAILED (2) |

Every behaviour the three fix commits added is genuinely load-bearing in the suite.

## Probed and clean (negative results)

- **`git ls-files -z` (S3).** No off-by-one, no empty trailing entry: `-z` split yields 105 paths,
  plain `ls-files` yields 105, the sets are identical, and zero empty strings survive the filter at
  `:102`. (Non-UTF-8 filenames raise `UnicodeDecodeError` under `text=True` and are caught
  fail-closed by `main`'s blanket `except` — acceptable, and strictly better than the old silent
  C-quoted drop.)
- **`isdir` acceptance.** Directory target, directory with trailing slash, and directory with a
  fragment all behave sanely — no crash, no heading-grading of a directory. An *ignored/untracked*
  top-level directory (`node_modules`, `build/`) does **not** slip through, because R5 rejects it
  first (`checked=0, failures=0` on that fixture).
- **Unterminated-fence false positives.** None found. A fence inside a blockquote is never entered
  (so it cannot report unterminated); tilde fences open and close correctly; a 4-backtick fence
  wrapping a 3-backtick line closes correctly; a fence line inside YAML frontmatter does not trip
  it. Genuine unterminated cases *are* reported: a bare ` ```python ` opener → `doc.md:3: ```python
  — unterminated code fence`, and a ` ``` ` opener "closed" by `~~~` correctly stays open.
- **Strict resolution across shapes.** `./x.md`, `x.md`, `sub/deep.md` from a repo-root file
  (`dirname == ""`) all resolve; `../../other/t.md`, `./sib.md`, `../up.md` from `a/b/c/doc.md` all
  resolve. No depth-related false positive.
- **`main()` argv removal (S4).** `.github/workflows/lint.yml:21` is the only invocation and passes
  no arguments; nothing in the repo calls `main(...)` programmatically.
- **Coverage parity.** Pre-fix (`31e858b`) and post-fix both grade 162 references with 0 failures
  on the real tree — the fixes neither lost coverage nor rejected a legitimate reference.
- **Working tree.** `git status --porcelain` shows only the untracked `.planning/reviews/` output
  directory after all fixtures and all six mutation cycles.

## Summary

2 blocking, 3 should-fix, 2 nit (new only)

Blocking = 1 new (the frontmatter mask, N1) + 1 carried unresolved from round 1 (the `_slugify`
whitespace-run bug, which the "blocking findings" commit did not touch and which 22 headings in the
current tree already trip).
