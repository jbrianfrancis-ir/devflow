# Findings — architecture (round 2)

Diff range `main...HEAD` (branch `flow/docs-restructure`); fixes under review: `1a2c384`,
`577ed13`, `2d5e5c1`. Those three commits touched exactly three files —
`scripts/check-links.py`, `tests/test_check_links.py`, `tests/test_flow_fleet.py`. No
planning or contract document was edited, as instructed.

Current state, run: `0 failures, 162 references checked`, exit 0, 0.068s;
`python3 -m unittest discover -s tests` → `Ran 64 tests ... OK (skipped=2)` (was 49).

## Round 1 disposition

### [blocking] Multi-base resolution applied to `[text](target)` links — **RESOLVED**
`scripts/check-links.py:259-263` now forks on `is_link`: a markdown link resolves against
`os.path.dirname(relfile)` only; backticked and `{devflow_root}` tokens keep `_bases_for`.
The three-line comment at `:260-262` states the reason (GitHub's rule vs. D-08/D-09
base-ambiguity), so the fork is legible rather than incidental.

Evidence — the exact round-1 table, re-run against a fixture repo laid out like this one:

```
from docs/README.md   [x](docs/execution-model.md)   -> docs/README.md:8: target does not exist   (was PASS)
from docs/README.md   [x](docs/status-contract.md)   -> docs/README.md:9: target does not exist   (was PASS)
from docs/README.md   [x](blitzos.md)                -> pass                                      (correct)
from docs/README.md   [x](status-contract.md)        -> pass                                      (correct)
```

Both real in-scope markdown links still pass, so the tightening changed no current result —
as round 1 predicted. Pinned in both directions by
`test_markdown_link_resolves_only_against_own_directory` and
`test_markdown_link_matching_only_the_root_base_is_reported_broken`
(`tests/test_check_links.py:220`, `:232`).

### [blocking] The checker cannot report that it went blind — **PARTIALLY**
Both halves of the suggested fix landed *for fences*:

- `check()` returns `CheckResult` (`:35-44`) carrying `.checked`; `main()` prints
  `0 failures, 162 references checked` (`:78`).
- An unterminated fence is a `Failure` (`:119-125`), not a silent mask.

Re-run of the round-1 demonstration fixture (fenced ASCII diagram + broken refs below it):

```
closing fence present  -> 2 failure(s), 3 references checked, exit 1
closing fence deleted  -> docs/execution-model.md:3: ``` — unterminated code fence — rest of file unchecked
                          1 failure(s), 0 references checked, exit 1     (was: 0 failures, exit 0)
```

Not resolved, for two reasons:

1. **The same blindness now exists through the frontmatter door, and that one is still
   silent** — see new finding N1. `577ed13`'s S5 introduced a second whole-file mask with
   no unterminated-case failure. Two thirds of the corpus (33 of 50 in-scope `.md` files
   begin with `---`) is one deleted delimiter away from going entirely unchecked at exit 0.
2. **The reference count has no baseline, so a coverage collapse is still not detectable
   from a single run.** Demonstrated on a clone of this repo: deleting the closing `---`
   of `plugins/devflow/skills/flow-status/SKILL.md` moved the line from
   `0 failures, 162 references checked` to `0 failures, 159 references checked` — both
   exit 0, both "green". Nobody diffs `162` against `159` across a PR. Round 1's optional
   suggestion ("assert a floor in `tests/test_check_links.py` against the real repo") was
   not taken; `grep -n "_repo_root\|rev-parse" tests/test_check_links.py` returns nothing,
   and `test_zero_failures_still_reports_a_nonzero_checked_count` (`:259`) asserts `2`
   against a fixture, which cannot notice the real corpus shrinking.

The counter is worth having and the fence half is properly done. The finding stays open
because the property it was protecting — *the tool cannot go blind without saying so* —
is still false.

### [should-fix] Resolution escapes the repo root — **RESOLVED**
`:264`, `:272-274`: `root_real = os.path.realpath(root)`, and a candidate is accepted only
if `candidate_real == root_real or candidate_real.startswith(root_real + os.sep)`. Using
`realpath` on both sides closes the symlink escape as well as `../`, which is stronger
than the `commonpath` fix round 1 suggested.

```
docs/traversal.md:3: ../../outside.md                  — target does not exist   (was PASS)
docs/traversal.md:4: `../../outside.md`                — target does not exist   (was PASS)
docs/traversal.md:5: ../../../../../../etc/passwd      — target does not exist   (was PASS)
```

Pinned at `tests/test_check_links.py:344` and `:356`. The verdict no longer depends on what
sits above the checkout.

### [should-fix] `main()` derives the root from cwd and `argv` is inert — **PARTIALLY**
The misleading half is fixed and the substantive half is not.

- `argv` is gone (`:68` — `def main():`), and `test_main_does_not_silently_accept_an_argv_list`
  (`:412`) pins that a caller mirroring `flow-fleet.py`'s `main([root, "--json"])` gets a
  `TypeError` instead of a silent full run. That is a defensible reading of "stop
  advertising an option that does not exist".
- **The cwd coupling is untouched.** `_repo_root()` (`:84-90`) still runs
  `git rev-parse --show-toplevel` with no `-C` and no `__file__` anchor. Re-verified: a
  throwaway git repo with no relation to DevFlow, then
  `python3 /home/brianf/dev/devflow/scripts/check-links.py` from inside it →
  `2 failure(s), 2 references checked`, exit 1. A repo-specific tool — `EXCLUDE_PREFIXES`
  and `DEVFLOW_ROOT_TARGET` at `:17-19` are hardcoded to this repo — still scans whatever
  repo it is launched from and applies DevFlow's exclusions and `{devflow_root}` rewrite to
  it.

Net effect on the seam: `check(root)` remains the only way to reach an explicit root, and
`main()` now has *no* parameter at all, so the gap between the two is wider than in round 1,
not narrower. Round 1 offered two fixes (`__file__`-derived root, or wire `--root`); neither
was taken. Low blast radius inside CI, which always runs from the checkout — but the
finding as written is not closed.

### [should-fix] Fence-skipping is a sixth rule in no constraint document — **NOT RESOLVED (correctly — reported, not fixed)**
No contract file was edited, which is what the executor was told to do. The drift is
therefore unchanged in kind and **larger in extent** — the fixes added three more behaviors
that `## Link checking` does not describe. Full accounting in the next section.

Round 1's two supporting measurements re-verified as still true: 0 otherwise-checkable
backticked refs sit inside fences; the 2 live in-fence `{devflow_root}` refs
(`docs/status-contract.md:90`, `plugins/devflow/references/hosts.md:40`) are still bare
rather than backticked and still uncovered. The limit is still recorded only in
agent-written files (`.planning/LEARNINGS.md:4`, `.planning/codebase/MAP.md:57`).

### [should-fix] Directory link targets reported broken — **RESOLVED**
`:267` accepts `os.path.isdir(candidate)` alongside `isfile`; `:192-195` returns
"not heading-graded" for a fragment against a directory. Verified:

```
[Documentation](docs/)   -> pass
[Documentation](docs)    -> pass
0 failures, 3 references checked
```

Pinned at `tests/test_check_links.py:376`, `:383`. Note the fix is *not* gated on `is_link`
(round 1 said "ideally only for `is_link=True`"); an ungated `isdir` means a backticked
token like `` `plugins/devflow/references` `` also resolves. That is harmless — it does not
create a false pass for anything that could 404 — and it keeps the two kinds sharing one
existence predicate, which I prefer to a third fork.

### [should-fix] "Docs are pointers, never copies" violated inside this diff — **NOT RESOLVED**
Out of the executor's remit (all four instances are in human-owned or planning files). Still
present verbatim: `ARCHITECTURE.md:30` restates REQ-09d's scope; the three-step smoke command
appears at `ARCHITECTURE.md:24`, `.planning/codebase/MAP.md:43`, and `.github/workflows/lint.yml`
with `MAP.md:42` citing ARCHITECTURE.md as the source before copying it anyway;
`phases/01-link-safety-net/CONTEXT.md` "## Locked" still restates D-07/D-08/D-09 with rationale;
the fence limitation is still stated in three agent-written places and no normative one.

### [nit] Anchors validated against non-markdown targets — **NOT RESOLVED**
`[x](scripts/check-links.py#L10)` → `README.md:3: scripts/check-links.py#L10 — no such heading #L10`.
Unchanged.

### [nit] Query strings and percent-encoding not stripped — **NOT RESOLVED**
`[x](docs/blitzos.md?plain=1)` and `[x](docs/my%20page.md)` (against a real `docs/my page.md`)
both → `target does not exist`. Unchanged.

### [nit] The safety net covers no non-`.md` file — **NOT RESOLVED (in-contract)**
Unchanged and still in-contract per REQ-09d.

---

## Did the fixes preserve the design's coherence?

Round 1's praise was that R1–R5 had **not** accreted special cases. That is **still true of
the rule set** — `_skip` at `:204-216` is byte-for-byte the same five predicates, in the same
order, with the same one-line comments. Nothing was bolted onto R1–R5.

Of the three additions:

- **The containment check** is not a special case at all. It is a three-line invariant on one
  function ("a resolved path must be inside the repo"), it fires uniformly on every reference
  kind and every base, and it makes the tool's verdict a function of the checkout alone.
  Clean.
- **Unterminated-fence-as-failure** introduces a new *category* — a `Failure` that is not
  about a reference — but it is the honest expression of fail-closed and it is one branch,
  not a rule. Clean, and it should have a sibling for frontmatter (N1).
- **The `is_link` fork in `_resolve`** is the interesting one, and my read is: **a clean
  distinction, correctly drawn, but only half-applied — and the unapplied half is where
  phase 04 will get hurt.**

The distinction itself is real, not invented. `[text](target)` has a single normative
resolution defined by GitHub; a backticked path in prose is a human pointer with no defined
base, which is exactly what D-08/D-09 exist to handle. Two kinds of reference with two
different meanings genuinely deserve two resolvers. Phase 04 will not be confused by *that*
sentence.

What will confuse phase 04 is that the pipeline forked at stage 3 of 3 and not at stage 2:

```
stage 1  parse         forked   (LINK_RE vs BACKTICK_RE + extension gate)
stage 2  _skip R1-R5   NOT forked  <-- the seam
stage 3  _resolve      forked   (own dir only  vs  _bases_for multi-base)
```

R5 — "the first path segment names nothing under any resolution base, therefore this is not
a repo reference" — is a *heuristic for base-ambiguous prose tokens*. Applied to a markdown
link it is simply wrong: a link's base is known, so "nothing matches under any base" means
*broken*, never *not a reference*. Measured on `docs/README.md`:

```
execution-modle.md        R5_skip=True    <- misspelled sibling, silently skipped
blizos.md                 R5_skip=True    <- misspelled sibling, silently skipped
docs/execution-modle.md   R5_skip=False   <- caught, only because "docs" happens to exist at root
```

So today's resolver has two modes that agree on the *hard* case (wrong prefix) and disagree
on the *easy* one (typo). That asymmetry is not GitHub semantics; it is the fork stopping one
stage short. Full write-up as N2 — and it is the residual half of round 1's central finding.

Two smaller coherence costs, both from `577ed13`:

- `_frontmatter_mask` became a **whole-file scope rule for source files** (`:116`, `:127`)
  without joining the R1–R5 numbering, without a contract clause, and without the
  unterminated-case failure its sibling `_code_fence_mask` just got. That *is* accretion —
  a sixth skip behavior living outside the place where skip behaviors live. See N1.
- `is_link` now silently overrides D-08's root anchoring for `{devflow_root}` refs written
  as links, because the rewrite at `:173-174` happens before the fork at `:263`. See N3.

Verdict: the rule set is intact; the *pipeline* around it now has one fork too few and one
undeclared mask too many.

---

## ARCHITECTURE.md contract drift

**Not edited — this section is input to a human decision.**

`.planning/ARCHITECTURE.md` `## Link checking` (lines 27-33) currently makes five claims. All
five are still true:

1. stdlib only, no network — true (`os/re/subprocess/sys/typing`; only `git` is spawned).
2. Validates `[text](target)` links and `#anchor` fragments, backticked repo-relative paths,
   and `{devflow_root}/…` resolved to `plugins/devflow/…` — true.
3. Scope = tracked `.md` except `plugins/devflow/templates/**` and `.planning/**` — true
   (`:17`, `:55`).
4. Non-repo refs skipped **by rule, never an allowlist file** — true; no exception file exists.
5. External URLs out of scope — true (`:170`).

The gap is entirely in what it **omits**. To match the implementation as it stands at HEAD,
the section would need to add the following. I have written them as the clauses I would put
in the file, so the human can accept, reject, or edit each on its own:

**(a) Kind-dependent resolution — the largest omission, and the one phase 03/04 must know.**
> A `[text](target)` link resolves against the referring file's own directory only, matching
> github.com. A backticked path or `{devflow_root}/…` token resolves against any of: the repo
> root, the referring file's directory, and `plugins/devflow/` for files under it.

Nothing in ARCHITECTURE.md, REQUIREMENTS.md, or PROJECT.md states this today. REQ-09a says only
"`[text](target)` **relative** paths"; REQ-09e's per-base language is scoped to *skip* rules.
An author writing `docs/README.md` cannot learn from any human-owned file that
`[x](docs/foo.md)` is wrong there.

**(b) Skip rules apply to links too.**
> The skip rules apply to every reference kind, including `[text](target)`. A link whose first
> path segment names nothing under any resolution base is skipped, not reported.

This is the current behavior and, in my view, a defect (N2). It must be either written down or
fixed; it must not stay unstated. If N2 is fixed, this clause becomes its inverse
("skip rules R1-R5 govern backticked and `{devflow_root}` tokens; a markdown link is always
graded").

**(c) Fenced code blocks are out of scope.** (round 1's finding, still open)
> References inside fenced code blocks are not checked.

**(d) YAML frontmatter is out of scope.** (new with `577ed13`)
> References inside a leading `---` … `---` block are not checked.

**(e) Malformed-block behavior — currently asymmetric.**
> An unterminated code fence is reported as a failure. *(true today, `:119-125`)*

and, for frontmatter, either the same sentence once N1 is fixed, or — if the human accepts the
current behavior — the honest version:
> An unterminated frontmatter block silently masks the rest of the file.

**(f) Containment.**
> A reference that resolves outside the repository — via `../` or a symlink — is reported as
> not existing, never followed.

**(g) Directory targets.**
> A link to a directory is valid; a fragment against a directory is not heading-graded.

**(h) The backticked-path gate is narrower than the phrase "backticked repo-relative paths".**
> A backticked token is checked only if it contains `/` **and** ends in `.md`, `.py`, `.json`,
> or `.yml`. Bare (non-backticked) paths are never checked, anywhere.

This one is not new, but it is why the two live `{devflow_root}` refs in fences at
`docs/status-contract.md:90` and `plugins/devflow/references/hosts.md:40` are uncovered twice
over, and phase 04 should know it before treating a green `lint` as proof REQ-08 is done.

**(i) The reference counter, if it is to mean anything.**
> The checker reports how many references it graded. A drop in that number without a
> corresponding content change is a coverage regression.

`## Smoke` (line 24-25) also drifts slightly: "Pass looks like … checker prints no failure
lines" is still satisfied, but the checker's output line changed shape to
`0 failures, N references checked`, and the count is now part of what a reviewer should read.

**Two further notes for the human, not clauses:**
- `## Principles` line 20 ("Every internal reference resolves. A path that 404s is a defect")
  remains strictly broader than what CI enforces — by (c), (d), (h), and the `.md`-only scope.
  Round 1 said this; it is more true now, since (d) is new.
- If `## Link checking` is instead cut down to genuine constraints and pointed at REQ-09a-e
  (round 1's "docs are pointers" suggestion), then (a), (b), (c), (d), (e) belong in
  REQUIREMENTS.md as REQ-09f/g rather than here. Either home is fine; the current state — where
  they have **no** home in any human-owned file — is not.

---

## Phase 02-04 fitness

Round 1's central finding: *"the single artifact phase 03 exists to produce is the one the
safety net cannot see."* **Half closed.**

`docs/README.md` does not exist yet (`docs/` holds `blitzos.md` and `status-contract.md`), so I
built the REQ-04 index in a fixture repo laid out like this one, with the index links written
the four ways an author actually writes them:

`docs/README.md`
```markdown
## Correctly written (sibling-relative — what GitHub resolves)
- [Blitzos](blitzos.md) — what it answers
- [Status contract](status-contract.md) — what it answers

## Incorrectly written (root-relative, copied out of the roadmap)
- [Execution model](docs/execution-model.md) — what it answers
- [Status contract again](docs/status-contract.md) — what it answers

## Incorrectly written (typo in a sibling filename)
- [Execution model typo](execution-modle.md) — what it answers
- [Blitzos typo](blizos.md) — what it answers

## Incorrectly written (root-relative typo)
- [Both wrong](docs/execution-modle.md) — what it answers
```

What the checker says, verbatim:

```
docs/README.md:8: docs/execution-model.md — target does not exist
docs/README.md:9: docs/status-contract.md — target does not exist
docs/README.md:16: docs/execution-modle.md — target does not exist
3 failure(s), 6 references checked
exit=1
```

Read the counts: **8 links in the fixture, 6 graded.** The two silently dropped are lines 12
and 13 — the misspelled siblings. Confirmed by instrumentation that R5 is the cause
(`_skip("execution-modle.md", "docs/README.md", …) == True`, and `_r5_skip` is the predicate
that returns it).

So, against REQ-04's accept criterion — *"link count = `docs/*.md` − 1; all resolve"*:

- The failure mode round 1 demonstrated (paths copied out of the roadmap, which spells them
  `docs/execution-model.md`) is now **caught**, loudly, at exit 1. That was the blocking half
  and it is genuinely fixed.
- The failure mode that is *more* likely in a hand-written index of sibling pages — a
  misspelled filename — is **silently skipped**. `check-links.py` exits 0, `lint` is green,
  SC-02 is satisfied, REQ-04 is recorded as met, and the row 404s for a real reader.

Phase 04 has the same residual shape. A prose reference repointed to a sibling that does not
exist (`[Autonomy](autonomy.md)` from a `docs/` page, where the file actually landed in
`plugins/devflow/references/`) is skipped by R5, not failed. The wrong-prefix version of the
same mistake is caught. The checker is now a real net for phase 03/04 rather than a decorative
one, but it has a hole exactly at the shape of a typo, and typos are what a 6-row index
produces.

Phase 02 (carving README's fenced blocks into `docs/` pages) is **better** protected than in
round 1 for fences and **worse** for frontmatter: a dropped closing ``` now fails loudly
(round-1 fix), while a dropped closing `---` now silently blinds the whole file (N1). Since
phase 02's output is new `docs/*.md` pages and phase 04 edits `SKILL.md` files that all carry
frontmatter, the newly-exposed surface is squarely inside phases 02-04's work.

Also unchanged and worth restating for phase 04: `.github/ISSUE_TEMPLATE/config.yml` — named in
REQ-08 — is out of scope twice over (`.yml`, and its ref is an external URL), and
`plugins/devflow/skills/flow-status/SKILL.md`'s prose section names are uncheckable by
construction. A green `lint` is still not evidence that REQ-08 is done.

---

## New findings

### [blocking] N1 — an unterminated frontmatter block silently masks the whole file: B2's failure mode, reintroduced through a different door
- `scripts/check-links.py:323-331` (`_frontmatter_mask`), newly applied to source files at
  `:116` and `:127` by `577ed13` (S5). Contrast `:115`, `:119-125`, where the fence mask *does*
  report its unterminated case.
- **What is wrong.** `_frontmatter_mask` masks from line 1 until the next line whose strip is
  `---`. If there is no such line, every line to EOF is masked, and — unlike the fence path —
  nothing is reported. This is precisely the property round 1 blocked on ("one stray line
  silently disables checking for the rest of a file"), fixed for fences in the same review
  cycle and reintroduced for frontmatter in the next commit. The mask also fires on a leading
  `---` used as a markdown thematic break, which is valid prose, not frontmatter.
- **Scenario, demonstrated on a clone of this repo at HEAD** — not a fixture:

  ```
  baseline                                                     0 failures, 162 references checked   exit 0
  delete the closing `---` of
    plugins/devflow/skills/flow-status/SKILL.md                 0 failures, 159 references checked   exit 0
  then append to that same file:
    - [gone](../../references/nope-does-not-exist.md)
    - `plugins/devflow/references/nope2.md`                     0 failures, 159 references checked   exit 0
  ```

  Two references that do not exist, in a tracked in-scope file, and the checker reports zero
  failures and exits 0. The file chosen is not arbitrary: `flow-status/SKILL.md` is one of the
  two files REQ-08 names by hand as a phase-04 repoint target, so this is the file most likely
  to be edited while blind.
- **Blast radius.** 33 of the 50 in-scope `.md` files begin with `---` (every `SKILL.md`, every
  `agents/*.md`). Two thirds of the corpus is one deleted delimiter from total, silent
  invisibility. A secondary form is partial: a page opening with a thematic break and
  containing a later `---` silently masks everything between — verified, two broken refs in the
  masked span went unreported while a third below it failed.
- **Fix.** Give `_frontmatter_mask` the same `(mask, unterminated_at)` signature
  `_code_fence_mask` now has, and emit the same class of `Failure`
  ("unterminated frontmatter block — rest of file unchecked"). Additionally, only treat a
  leading `---` as frontmatter when the block actually closes — an unclosed one should mask
  line 1 only, since it is a thematic break. Keep `_heading_slugs`' use of the mask as-is.
  Test both directions, mirroring `tests/test_check_links.py:276` / `:286`.
- **Not a checkpoint decision.** This is a defect, symmetric with the fence fix already
  accepted at `1a2c384`; no contract changes meaning.

### [blocking] N2 — R5 skips broken markdown links, so the phase-03 index's most likely defect is invisible
- `scripts/check-links.py:185` (`_skip` called for every kind), `:249-256` (`_r5_skip`),
  against the `is_link` fork at `:263`.
- **What is wrong.** `_resolve` was forked on `is_link`; `_skip` was not. R5's premise — "the
  first segment names nothing under any resolution base, so this token is not a repo reference"
  — is sound for a base-ambiguous backticked token and unsound for a markdown link, whose base
  is known and single. The result is that a link is graded only when its first segment
  coincidentally names something *somewhere else in the repo*: `[x](docs/typo.md)` is caught
  because `docs/` exists at root, while `[x](typo.md)` from that same file is not caught at all.
  The tool's coverage of links is now a function of an unrelated base's directory listing.
- **Scenario** — the REQ-04 index above, run: 8 links, `3 failure(s), 6 references checked`,
  two misspelled sibling rows silently skipped. Instrumented confirmation:

  ```
  _skip("execution-modle.md", "docs/README.md", root, all_files) -> True    (R5)
  _skip("blizos.md",          "docs/README.md", root, all_files) -> True    (R5)
  _skip("docs/execution-modle.md", ...)                          -> False   (graded, fails)
  ```

  Phase 03 ships `docs/README.md` with a typo'd row; CI is green; REQ-04's accept criterion
  ("all resolve") is recorded as met; the row 404s. Phase 04's repoints have the same shape.
  Invisible today only because the repo contains exactly 2 markdown links, both correct
  (measured: `in-scope non-URL markdown links: 2, graded: 2, skipped by rule: 0`) — phase 03
  multiplies that by the size of the index.
- **Fix.** Move the fork one stage earlier: for `is_link=True`, apply R1-R4 (whitespace, family
  punctuation, `NNN` placeholders, `.planning/`/`~/`) and **not** R5. R1-R4 are properties of
  the token that hold regardless of kind; R5 is the only base-relative one and the only one
  that can turn a broken link into a non-event.
- **This is a checkpoint decision.** REQ-09e reads "A skip rule is evaluated against **every**
  resolution base of the token", and D-09's recorded rationale is about *under*-checking from
  root-only evaluation (10 real refs). Exempting links from R5 does not contradict D-09's
  intent — the 10 refs it protected were backticked tokens — but it does narrow REQ-09e's
  literal wording, and REQUIREMENTS.md is human-owned. The human should confirm the reading:
  *skip rules govern base-ambiguous tokens; a markdown link, having exactly one base, is always
  graded.* Pair the decision with clause (b) of the contract-drift section.

### [should-fix] N3 — `is_link` silently overrides D-08's root anchoring for `{devflow_root}` links
- `scripts/check-links.py:173-174` (rewrite) executes before `:263` (fork).
- **What is wrong.** `{devflow_root}/…` is by D-08 an anchored token: it means
  `plugins/devflow/…` from the repo root, full stop. The rewrite turns it into a
  root-relative path and then the `is_link` fork resolves that root-relative path against the
  referring file's directory, which is guaranteed wrong for any file not at the repo root.
  The failure message also prints the rewritten path rather than what the author typed, so the
  diagnostic points at a string that appears nowhere in the file.
- **Scenario** (fixture; `plugins/devflow/scripts/flow-fleet.py` exists):

  ```
  docs/page.md                          [fleet]({devflow_root}/scripts/flow-fleet.py)
    -> docs/page.md:3: plugins/devflow/scripts/flow-fleet.py — target does not exist
  plugins/devflow/references/hosts.md   [fleet]({devflow_root}/scripts/flow-fleet.py)
    -> plugins/devflow/references/hosts.md:3: plugins/devflow/scripts/flow-fleet.py — target does not exist
  the backticked form of the identical token, in both files -> passes
  ```

  Zero such links exist today (`git grep -nE '\]\(\{devflow_root\}' -- '*.md'` is empty), but
  phase 02 is moving `references/` content into `docs/` pages and `{devflow_root}` is the
  repo's ~80-instance idiom for pointing at plugin content. The hazard is round 1's: a
  self-announcing false positive under time pressure invites widening a skip rule, and a
  weakened rule is permanent.
- **Fix.** Carry a flag through `_check_reference` — if the target was `{devflow_root}`-rewritten,
  resolve from the repo root regardless of `is_link`. Report the author's original token in the
  `Failure`, not the rewritten path.

### [should-fix] N4 — the reference counter has no baseline, so it cannot actually detect the blindness it was added for
- `scripts/check-links.py:78`; `tests/test_check_links.py:250`, `:259` (both fixture-scoped;
  no test consults the real repo — `grep -n "_repo_root\|rev-parse" tests/test_check_links.py`
  is empty).
- **What is wrong.** `0 failures, 162 references checked` is only information if something
  compares it to a previous run. Nothing does: not CI (`lint.yml` checks exit status), not the
  test suite, not a human reading a PR. Demonstrated in N1 — `162 → 159` with two live broken
  references in the tree and exit 0 throughout.
- **Fix.** Add one test that runs `check()` against the repo root and asserts
  `result.checked >= <floor>` (say 150), with a comment that the floor is a coverage ratchet
  and lowering it requires explaining what stopped being checked. That is the cheapest thing
  that converts the counter from a number into a guard, and it is what round 1 suggested
  optionally.

### [should-fix] N5 — frontmatter became a scope rule with no home in any document, agent-written or human-owned
- `scripts/check-links.py:116`, `:127`; contrast the fence limit, which at least appears in
  `.planning/LEARNINGS.md:4` and `.planning/codebase/MAP.md:57`.
- **What is wrong.** Round 1's finding was "fence-skipping is a sixth rule that appears in no
  constraint document". `577ed13` added a seventh — frontmatter — and this one appears in no
  document *at all*: not ARCHITECTURE.md, not REQUIREMENTS.md, not LEARNINGS.md, not MAP.md.
  Its only description is a commit message and a test docstring. Phase 02-04 planners reading
  the planning corpus will not know it exists.
- **Fix.** Report it alongside the fence limit for the human's ARCHITECTURE.md decision —
  clause (d) above — and add the one-line note to `.planning/LEARNINGS.md` next to the fence
  bullet, which is agent-owned and therefore in remit.

### [nit] N6 — `CheckResult` loses `.checked` under any list operation, and `check()`'s docstring no longer describes what it returns
- `scripts/check-links.py:35-44`, `:48-52`.
- Subclassing `list` was the right call for backward compatibility — every existing caller and
  all 64 tests keep working, verified. But `sorted(check(root))`, `check(a) + check(b)`, or
  `list(check(root))` all silently yield a plain `list` with no `.checked`, and the docstring
  at `:48` still says "return the list of failures" with no mention of the count. A one-line
  docstring amendment costs nothing and removes the trap.

### [nit] N7 — `.planning/codebase/MAP.md:44` says "49 tests"; the suite now has 64
- Stale as of `1a2c384`. `MAP.md` was refreshed at `72616a4`, before the fixes landed. Agent-owned,
  so in remit for a follow-up librarian pass rather than a code change.

---

## Summary

**2 blocking, 3 should-fix, 2 nit (new only).**

Blocking, both with demonstrated failure scenarios:
- **N1** — unterminated frontmatter silently blinds the whole file; shown on a clone of this
  repo at HEAD with two broken references and exit 0; 33 of 50 in-scope files exposed. *Not* a
  checkpoint decision — it is the fence fix's missing sibling.
- **N2** — R5 skips broken markdown links; shown on the actual REQ-04 `docs/README.md` index,
  where 2 of 8 rows are silently unchecked. **This one is a checkpoint decision** — it narrows
  REQ-09e's literal wording, and REQUIREMENTS.md is human-owned.

Round 1 disposition: 1 of 2 blocking RESOLVED, 1 PARTIALLY; 2 of 5 should-fix RESOLVED, 1
PARTIALLY, 2 NOT RESOLVED (both out of the executor's remit by design); 3 nits unchanged.

The fixes are good work and the design held. R1-R5 did not accrete a single special case; the
containment check and the strict link resolver are both principled, and the round-1 blocking
scenarios reproduce as failures now. The two blockers above are not a reversal of that — they
are the same fork and the same fail-closed principle, applied one stage too late and to one
mask too few. The contract drift is now the largest open item and the only one no agent can
close: nine distinct behaviors of `scripts/check-links.py` have no home in any human-owned
file, and phases 02-04 are about to write against them.
