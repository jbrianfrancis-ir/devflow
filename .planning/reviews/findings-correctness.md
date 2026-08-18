# Findings — correctness (round 3, final)

Method, unchanged from rounds 1-2: every disposition and every new finding was reproduced by
driving `MODULE.check(root)` over throwaway `git init`'d fixtures, by running the CLI, or by
mutating `scripts/check-links.py` and running the suite. Nothing here is read-only reasoning.
Where a claim is "no defect found", it is a negative result I generated, not an absence of looking.

**Repo baseline, verified after every mutation cycle and at the end:**

```
$ python3 scripts/check-links.py
0 failures, 162 references checked          exit 0
$ python3 -m unittest discover -s tests
Ran 75 tests ... OK (skipped=2)
$ git status --porcelain
?? .planning/reviews/            (only this review output; tree otherwise clean)
```

**The count is honest.** I recounted independently, re-deriving every branch of
`_check_reference` outside the module's own loop: 352 references extracted post-mask, 162 graded,
190 skipped (174 backticked-token skips, 16 URLs). Exactly matches. `import`ing the module has no
side effect (verified in a fresh subprocess).

**The 162 breaks down in a way that matters for the rest of this report:**

| kind | count |
|---|---|
| backticked `{devflow_root}/...` tokens | 112 |
| backticked plain repo paths | 48 |
| markdown links | **2** |

The two graded links are `README.md:7 → docs/status-contract.md` and
`README.md:44 → docs/blitzos.md`. **Every link-related fix in this branch — B1's strict own-dir
resolution, round 2's `{devflow_root}` root-anchoring, round 2's R5-for-links exemption — is
exercised by two real references.** That is not an argument against the fixes (they are correct and
they are pinned by tests); it is context for weighing every "latent" label below. The gate's live
coverage today is a backtick-token checker.

> **Tooling caveat, third round running.** One Bash result in this session returned a reason string
> (`— all good here`) that does not exist anywhere in the source; two consecutive re-runs of the
> identical fixture produced the correct `— unterminated code fence — rest of file unchecked`. A
> second anomaly silently left `scripts/check-links.py` carrying a round-2 mutation (`isdir` →
> `isfile`) after a `cp`-based restore that should have been clean, which invalidated my first
> mutation batch; I caught it with `git diff` and redid the entire batch from `git checkout`, with a
> pre-flight cleanliness assert on every iteration. **Every mutation result reported below is from
> the redone, git-clean batch.** Treat any single unreproduced observation in these three reports
> with suspicion.

---

## Round 2 disposition

### Round 2's own new findings

- **[blocking] The new frontmatter mask silently swallows content to EOF** — **PARTIALLY RESOLVED.**

  Round 2 gave two reproductions. The first is fixed, the second is not, and the fix introduced a
  third failure mode.

  *Reproduction 1 (whole file silently unchecked) — FIXED, and now loud.* `_frontmatter_mask` at
  `scripts/check-links.py:365-379` now returns `(mask, unterminated_at)`, and `_check_file:126-133`
  emits a `Failure`. Verified:
  ```
  doc.md  "---\ntitle: X\n\nSee [g](docs/missing.md).\n"
  → checked=0 failures=1
    doc.md:1: --- — unterminated frontmatter block — rest of file unchecked
  ```
  Mutation-pinned: `return mask, 1` → `return mask, None` fails 2 named tests
  (`test_unterminated_frontmatter_is_reported_as_a_failure`,
  `test_reference_after_an_unterminated_frontmatter_block_is_not_checked`).

  *Reproduction 2 (partial silent mask) — UNCHANGED, still silent.* Re-reproduced verbatim:
  ```
  doc.md  "---\n\n# Title\n\nSee [a](docs/missing1.md).\n\nfiller\n\n---\n\nSee [b](docs/missing2.md).\n"
  → checked=1 failures=1     (only docs/missing2.md reported)
  ```
  `docs/missing1.md` on line 5 is still masked and still never counted, with no signal. This is the
  fail-open half — the half that made the finding blocking — and it is untouched: the
  implementation kept "mask everything from the opener" and only added a report for the no-closer
  case. Round 2's actual suggested fix ("if there is no closing `---`, treat the file as having no
  frontmatter rather than as being entirely frontmatter") was not implemented, and implementing it
  is what closes both this and New finding N1 below.

- **[should-fix] Strict resolution also applies to `{devflow_root}` links** — **RESOLVED.**
  `root_anchored` is set at `:186` and forces `bases = [""]` at `:293-294`. I tried every
  combination the lead asked about and found no wrong base:

  | referring file | form | result |
  |---|---|---|
  | `docs/autonomy.md` | link | resolves ✓ |
  | `docs/autonomy.md` | backtick | resolves ✓ |
  | `README.md` (root) | link | resolves ✓ |
  | `plugins/devflow/skills/x.md` | link | resolves ✓ |
  | `docs/autonomy.md` | link + `#git-workflow` | anchor graded against the right file ✓ |
  | `docs/autonomy.md` | link, target missing | correctly reported ✓ |
  | `docs/autonomy.md` | link with `/../../` inside | normalises, resolves ✓ |

  Mutation-pinned: `if root_anchored:` → `if False:` fails
  `test_devflow_root_link_from_a_nested_file_resolves_against_repo_root`.

- **[should-fix] Containment rejects a git-tracked symlink pointing outside the checkout** —
  **NOT RESOLVED.** Re-reproduced: `docs/ext.md` is a tracked symlink to a file outside the repo;
  `[e](docs/ext.md)` → `doc.md:3: docs/ext.md — target does not exist`. The realpath check at
  `:314-315` is unchanged and the tracked-set membership test round 2 asked for was not added.

- **[should-fix] R5 silently skips a single-segment link target** — **RESOLVED.** `_skip:228-240`
  now returns `False` before `_r5_skip` when `is_link`. Re-reproduced round 2's exact fixture:
  ```
  docs/a.md  "# A\n\nSee [b](missing.md) and [c](./missing2.md).\n"
  → checked=2 failures=2     (both reported; previously only ./missing2.md)
  ```
  Backtick control still R5-skips (`` `nothingdir/x.md` `` → `checked=0 failures=0`), so the
  exemption is scoped to links as intended. Mutation-pinned: removing the early `return False`
  fails `test_markdown_link_with_unmatched_first_segment_is_reported_broken_not_skipped`.
  See New finding N3 for the one thing this exemption over-caught.

- **[should-fix] A fragment against a binary target aborts the entire run** — **NOT RESOLVED.**
  Re-reproduced: a tracked PNG plus `[img](assets/logo.png#foo)` → `check(root)` raises
  `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x89 in position 0`. `_check_anchor:329`
  still opens whatever `_resolve` returned and `:332` still catches `OSError` only. The related
  round-1 item is also unchanged: `[seam](scripts/thing.py#L10)` → `no such heading #L10`.

- **[nit] "N references checked" reads like full coverage** — **NOT RESOLVED.** Output is still
  `0 failures, 162 references checked` with no denominator; 190 of 352 extracted references are
  dropped by rule and invisible.

- **[nit] The unterminated-fence failure is not counted** — **NOT RESOLVED**, and now doubled: the
  new frontmatter failure has the identical shape. Both reproduce a self-contradicting summary line,
  e.g. `1 failure(s), 0 references checked`.

### Round 1 carryovers that round 2 tracked

- **[blocking] `_slugify` collapses runs of whitespace; GitHub does not** — **STILL NOT RESOLVED.**
  `:432` is still `re.sub(r"\s+", "-", text)`. Re-reproduced with a control in the same fixture:
  ```
  docs/conv.md  "## Credential modes & push canary"
  [x](docs/conv.md#credential-modes--push-canary)   → no such heading   ← the CORRECT GitHub anchor
  [y](docs/conv.md#credential-modes-push-canary)    → passes            ← the anchor that 404s
  ```
  `MODULE._slugify("Credential modes & push canary")` returns `credential-modes-push-canary`;
  github-slugger returns `credential-modes--push-canary` (punctuation removal leaves two spaces,
  and the final step is a per-character `.replace(/ /g, '-')`). Wrong in **both** directions, and
  round 2 counted 22 headings in the current tree whose slug diverges. Still latent only because
  there are **0** `](...#...)`-into-those-headings references in scope. I am not re-grading this;
  round 2's severity stands and it is now a human decision.

- All other round-1 carryovers (reference-style links, `BACKTICK_EXT_RE` allowlist, case-insensitive
  fragments, `[top](#)`, `(`-truncation and `%`-escapes, indented code blocks, inline code spans,
  `_strip_inline_markdown` deleting `_`, BOM, indented ATX, the dead `_bases_for` branch at `:246`)
  — **UNCHANGED.** Spot-re-reproduced `[top](#)` → `# — no such heading #` and
  `docs/g.md?raw=1 — target does not exist`; the rest are unchanged by inspection of untouched lines.

---

## New findings

### [should-fix] N1 — A markdown document that opens with a thematic break is reported as an unterminated frontmatter block, goes entirely unchecked, and poisons every inbound anchor
- `scripts/check-links.py:372` (`if not lines or lines[0].strip() != "---": return mask, None`),
  `:375-379` (mask everything, then `return mask, 1`), `:126-133` (the new `Failure`)
- **Introduced this round**, by 7efcc64. Pre-7efcc64 this shape was silent; it is now CI-red.

**What is wrong.** `_frontmatter_mask` opens on *any* file whose first line strips to `---` and, if
no later `---` is found, masks every line to EOF **and** reports an unterminated frontmatter block.
`---` on line 1 is not necessarily frontmatter — it is also a perfectly ordinary CommonMark thematic
break, which GitHub renders as `<hr>` with the rest of the document intact. The checker cannot tell
the difference and now resolves the ambiguity by failing.

**Reproduced — false CI-red on valid markdown:**
```
doc.md         "---\n\n# Release Notes\n\nSee [g](docs/guide.md).\n"
docs/guide.md  "# Guide\n"
→ checked=0 failures=1
  doc.md:1: --- — unterminated frontmatter block — rest of file unchecked
```
The document is correct. Every reference in it is correct. The gate is red, the count for the file
is zero, and the message names a construct (frontmatter) the file does not contain — so the author
is told to fix something that isn't there.

**Reproduced — it is contagious, not confined to the offending file.** `_heading_slugs:385` runs the
same mask over *target* files, so a document that opens with a thematic break has all of its
headings erased for anchor-grading purposes:
```
index.md        "# Index\n\nSee [g](docs/guide.md#usage) and [h](docs/guide.md#setup).\n"
docs/guide.md   "---\n\n# Guide\n\n## Usage\n\n## Setup\n"
→ checked=2 failures=3
  docs/guide.md:1: --- — unterminated frontmatter block — rest of file unchecked
  index.md:3: docs/guide.md#usage — no such heading #usage
  index.md:3: docs/guide.md#setup — no such heading #setup
```
Control (identical files, leading `---` removed) → `checked=2 failures=0`. One character in one file
produces three failures across two files, two of which are unexplained.

**Reproduced — and the fail-open half is still there.** Add a second `---` anywhere and the failure
disappears while the coverage loss stays, now with *no* diagnostic at all:
```
docs/guide.md   "---\n\n# Guide\n\n## Usage\n\n---\n\n## Setup\n"
→ checked=2 failures=1
  index.md:3: docs/guide.md#usage — no such heading #usage
```
`## Usage` is visibly present in the file and the checker says it does not exist, with nothing
pointing at the mask. This is the round-2 "reproduction 2" case above; it is undiagnosable from the
output.

**Why should-fix and not blocking.** Latent today: I swept all 50 scoped files — 33 open with `---`,
**all 33 are genuine, properly terminated frontmatter**, 0 are unterminated, and 0 non-frontmatter
file contains a bare `---` line. And the dominant failure mode is loud, which is strictly better
than what it replaced. Against that: 33 of 50 files already carry frontmatter, phases 02-04 split
documents, and splitting a frontmattered file at a `---` is the one edit that manufactures this
exact shape.

**Fix (one edit, closes this *and* the unresolved half of round-2 N1).** Implement round 2's actual
suggestion: in `_frontmatter_mask`, scan for the closing `---` **first**, and mask nothing unless one
is found.
```python
def _frontmatter_mask(lines):
    mask = [False] * len(lines)
    if not lines or lines[0].strip() != "---":
        return mask, None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            for j in range(i + 1):
                mask[j] = True
            return mask, None
    return mask, None      # no closer → not frontmatter, mask nothing
```
Then drop the `Failure` at `:126-133`. I checked the obvious objection: with no mask, a genuinely
unterminated YAML block is scanned as prose, and YAML scalars are neither `[text](target)` nor
backticked-with-an-extension, so nothing new is extracted — verified against all 33 frontmatter
blocks in the tree. The partial-mask case then also disappears, because the greedy
"first `---` to next `---`" span stops being a mask at all when the opener is a thematic break.
(This does mean genuinely-unterminated real frontmatter is no longer reported. That is the right
trade: it is a YAML defect, not a reference defect, and this tool's contract is references.)

---

### [should-fix] N2 — An unbalanced code-fence line *inside* YAML frontmatter is reported as an unterminated code fence, darkening the whole file
- `scripts/check-links.py:339-362` (`_code_fence_mask` scans every line, frontmatter included),
  `:115-125` (`_check_file` reports `fence_unterminated_at` without consulting `front_mask`)
- Not introduced this round, but **new to this review**: round 2's negative-results section
  explicitly cleared this ("a fence line inside YAML frontmatter does not trip it"). That result is
  wrong — it holds only for *balanced* fences and for fence characters not at the start of the
  stripped line.

**What is wrong.** `_code_fence_mask` and `_frontmatter_mask` are computed independently over the
same line list (`:115-116`) and neither knows about the other. A frontmatter line whose stripped form
starts with three or more backticks — routine inside a YAML literal block such as `description: |`
or `usage: |`, which is exactly how this repo's `SKILL.md` frontmatter is written — opens a fence in
the fence scanner. Nothing later closes it, so the file is masked to EOF and a `Failure` is raised
against a line that is not markdown at all.

**Reproduced — false CI-red:**
```
doc.md  "---\nname: x\nusage: |\n  ```bash\n  cmd\n---\n\nSee [g](docs/g.md).\n"
→ checked=0 failures=1
  doc.md:4: ```bash — unterminated code fence — rest of file unchecked
```
Line 4 is inside frontmatter. `front_mask[3]` is `True`. The document is valid; GitHub renders it
fine; the link on line 8 is correct and never gets graded.

**Reproduced — same cascade as N1:**
```
index.md              "# Index\n\nSee [u](plugins/x/SKILL.md#usage).\n"
plugins/x/SKILL.md    "---\nname: x\nusage: |\n  ```bash\n  cmd\n---\n\n# X\n\n## Usage\n"
→ checked=1 failures=2
  index.md:3: plugins/x/SKILL.md#usage — no such heading #usage
  plugins/x/SKILL.md:4: ```bash — unterminated code fence — rest of file unchecked
```

**Controls that stay clean** (so the finding is precisely scoped, not a blanket claim): a *balanced*
fence inside frontmatter, a quoted `usage: "```"`, a quoted `sep: "---"`, and a fence character
appearing mid-line (`Use ```bash blocks here`) all behave correctly.

**Why should-fix and not blocking.** Latent: no file in the tree trips it today (baseline is 0
failures). But 33 of 50 scoped files have frontmatter, and a `description:`/`usage:` block showing a
fenced command is the single most natural thing to put there in a repo whose product *is* skill
documentation.

**Fix.** Either suppress the fence failure when its line is inside the frontmatter region —
```python
if fence_unterminated_at is not None and not front_mask[fence_unterminated_at - 1]:
```
— or, better, have `_code_fence_mask` take the frontmatter region and skip it, so the mask itself is
right rather than just the report. Note N1's fix does **not** subsume this: with terminated
frontmatter, `front_mask` is correct and the fence scanner is still wrong.

---

### [should-fix] N3 — The R5 link exemption turns non-`http` URI schemes and scheme-less URLs into "target does not exist"
- `scripts/check-links.py:178` (the exemption list is exactly `http://`, `https://`, `mailto:`),
  `:228-240` (R5 no longer rescues links)
- **Introduced this round**, by 7efcc64.

**What is wrong.** R5 was the only thing that kept a link target that is not a repo path from
reaching `_resolve`. The exemption is correct in principle — a `[text](target)` link's base is not
ambiguous — but the http/https/mailto prefix test is now the *sole* guard, and it does not cover the
other things a `(...)` target can legitimately be.

**Reproduced (current) vs. the same fixture at `7efcc64^`:**
```
doc.md
  [a](ftp://example.com/f.md)
  [b](tel:+15551234)
  [c](//cdn.example.com/x.png)
  [d](www.example.com)
  [e](slack://channel?id=1)

CURRENT      → checked=5 failures=5   (all five: "target does not exist")
7efcc64^     → checked=0 failures=0
```
All five render as working external links on github.com. Protocol-relative (`//cdn...`) and
scheme-less (`www.example.com`) are the ones most likely to appear in real prose; an uppercase
`HTTPS://` also falls through, since `:178` is case-sensitive.

**Deliberately NOT reported as part of this finding — the other half of the widening is correct.**
I checked the adjacent class and it is intended behaviour, not a defect:
```
[path/to/your/file.md](path/to/your/file.md)   → now reported (was R5-skipped)
[the summary](phase-NN/SUMMARY.md)             → now reported (was R5-skipped)
[.env.example](.env.example)                   → now reported (was R5-skipped)
```
Those genuinely 404 on github.com — an illustrative path belongs in backticks, and backticks still
R5-skip. Reporting them is the fix working. I flag it only so the phase-02-04 executors know the
gate got stricter about illustrative paths written as links.

**Fix.** Widen the exemption at `:178` from a three-prefix list to a scheme test —
`re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target)` (RFC 3986 scheme grammar) — plus an explicit
`target.startswith("//")` for protocol-relative. Leave bare `www.example.com` reported; that one is
genuinely ambiguous and GitHub does *not* linkify it inside `(...)`, so calling it broken is
defensible.

---

### [nit] N4 — The 140 coverage floor is a sane collapse tripwire, will not trip on ordinary phase 02-04 edits, and is blind to any regression under ~23 references
- `tests/test_check_links.py:613-620`

The lead asked two questions. Measured answers:

**"Will ordinary phase 02-04 doc edits trip it?" — No.** Headroom is 22 (162 → 140, 13.6%). Moving
prose between in-scope files conserves the count, because source and destination are both scanned.
Losing 23+ requires references to *leave scope* or be deleted. The realistic ways that happens:
relocating prose into `.planning/` or `plugins/devflow/templates/` (both excluded at `:17`);
deleting or merging 2-4 `SKILL.md` files; or a prose-polish pass that un-backticks ~23 paths.
Because 133 of the 162 live under `plugins/` and only 29 outside it, a docs-restructuring phase
would have to be very destructive to trip this. Verdict: **140 is a sane floor.**

**"Is it a good tripwire?" — Only for total collapse.** Measured by simulating scoped coverage
regressions:

| simulated silent regression | count | floor fires? |
|---|---|---|
| global frontmatter mask always masks to EOF (round 2's demo) | 45 | **yes** |
| all non-`plugins/` files go dark | 133 | yes (barely) |
| whole `docs/` tree goes dark | 151 | **no** |
| the two largest `SKILL.md` files go dark | 141 | **no** |

Both blind rows print `0 failures` and pass the floor. So the test catches the shape round 2
demonstrated and nothing smaller. Worth noting the specific collapse it was written for is now also
caught *loudly* by N1's `Failure` (the mask regression above produces 33 explicit failures), so the
floor's marginal value is mostly against future, different mask/skip widenings.

Secondary effect worth stating plainly: this test couples the unit suite to the working tree, so an
executor who legitimately trims documentation gets a red unit test whose message says "a skip rule
or mask may have widened" — a misleading diagnosis for a content change.

**Suggestion (not required).** Assert per-tree floors (`docs/`, `plugins/devflow/skills/`,
`plugins/devflow/references/`, root) rather than one global number, or assert the graded/extracted
*ratio* (162/352 = 46%) which is invariant to content volume. Either detects a scoped regression the
single global floor cannot.

---

### [nit] N5 — A `{devflow_root}` failure reports the rewritten path, not the token the author wrote
- `scripts/check-links.py:186-188` (rewrite) precedes every `Failure` construction

```
docs/autonomy.md  "See [x]({devflow_root}/references/nope.md)."
→ docs/autonomy.md:3: plugins/devflow/references/nope.md — target does not exist
```
The reported string does not appear anywhere in the file, so it is not greppable and, in a doc that
mixes both forms, the author cannot tell which token was flagged. Carry the original text through to
the `Failure` and keep the rewritten path for resolution only. Pre-existing, surfaced here because
round 2's `{devflow_root}` fix made this path newly reachable for links.

---

## Guards mutation-tested this round (all pinned — no finding)

Batch redone from `git checkout` with a cleanliness assert before each iteration, after the tooling
anomaly noted at the top. Full suite per mutation; tree verified clean afterwards.

| # | Mutation | Result |
|---|---|---|
| A | `_frontmatter_mask` unterminated → `return mask, None` | FAILED (2) — both named frontmatter tests |
| B | R5 link exemption removed | FAILED (1) — `test_markdown_link_with_unmatched_first_segment_is_reported_broken_not_skipped` |
| C | `if root_anchored:` → `if False:` | FAILED (1) — `test_devflow_root_link_from_a_nested_file_resolves_against_repo_root` |
| D | reference-level escape rejection deleted | FAILED (2) — `test_escape_and_return_is_rejected_regardless_of_checkout_directory_name` (both parametrised dirnames) |

Every behaviour added this round is load-bearing, and each is pinned by a test whose name describes
the behaviour rather than the implementation.

---

## Probed and clean (negative results — the reference-level escape check specifically)

The lead's top priority was whether the new reference-level rejection at `:305-306` false-rejects a
legitimate reference. **I could not make it.** Every shape below resolves correctly:

- `../` from a nested dir back into the repo (`sub/doc.md → ../docs/guide.md`) ✓
- depth-3 relatives, all four at once: `../../../docs/g.md`, `../../b2/t.md`, `./sib.md`, `../up.md`
  from `a/b/c/doc.md` → `checked=4 failures=0` ✓
- repo-root file where `dirname == ""`: `docs/g.md`, `./docs/g.md`, `CHANGELOG.md`, `./CHANGELOG.md`
  → `checked=4 failures=0` ✓
- **dip-out-and-back**: `../sub/../docs/g.md` and `./../docs/g.md` from `sub/doc.md` → both resolve.
  `normpath` collapses before the `..`-prefix test, so the check does not fire on a path that only
  transiently leaves ✓
- backticked `../docs/g.md` under the multi-base walk → resolves via the own-dir base ✓
- directory targets, trailing slash, directory + fragment → all still pass, no heading-grading ✓
- genuine escapes still rejected: `../outside.md` from a root file, `../../etc/hostname` from `sub/` ✓

Also clean: the R5 exemption does **not** mis-handle `mailto:` (exempt) or anchor-only links
(`path_part == ""` is handled at `:195-197`, before `_skip` is ever reached — `[top](#)` and
`[b](#top)` fail for the pre-existing round-1 reasons, not because of this change). `root_anchored`
and `is_link` produce the correct base in all seven combinations I could construct. Nested `---`
inside frontmatter, a top-of-file fence containing `---`, and a quoted `"---"` in YAML are all
handled correctly.

---

## Summary

**0 blocking, 3 should-fix, 2 nit (new only).**

Carried unresolved from earlier rounds, unchanged by 7efcc64/73d4aa4: the round-1 `_slugify`
whitespace-run divergence (round 2 graded blocking; 22 in-tree headings affected; still latent at 0
in-scope anchor references), the `UnicodeDecodeError` crash on a binary anchor target, anchors into
non-markdown files, the tracked-symlink rejection, reference-style links, and the `BACKTICK_EXT_RE`
allowlist.

Nothing new this round is fail-open. All three new should-fixes are false-positive classes: valid
markdown that this gate would turn CI red on. Each is latent on today's tree and each has a fix of
one to five lines.

## Recommendation

**Safe to open as a PR** — the gate is green and its 162 is honest, all four guards added this round
are mutation-pinned, and no new fail-open path was introduced. The human decision before merge is
whether to ship a standing CI gate carrying three known latent false-positive classes (N1, N2, N3 —
each ~1-5 lines, and N1's fix also closes the unresolved fail-open half of round-2's blocking
finding) plus the still-unfixed `_slugify` divergence that will red-flag the first correct anchor
link written into any of 22 existing headings.
