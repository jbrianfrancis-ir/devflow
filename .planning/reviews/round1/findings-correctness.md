# Findings — correctness

## Summary
2 blocking, 6 should-fix, 7 nit

Method: every finding below was reproduced by building a throwaway `git init`'d fixture
and calling `MODULE.check(root)` (the 01-01 seam), or by running the CLI. Nothing here is
read-only reasoning. The repo's own baseline is genuinely clean —
`python3 scripts/check-links.py` → `0 failures`, exit 0 — so all of these are latent:
they mis-grade inputs the repo does not contain *today*, which matters because 01-03 just
made this a standing CI gate and phases 02-04 are document-splitting work.

## Findings

### [blocking] Markdown links are resolved against the repo root, not the referring file's directory
- `scripts/check-links.py:220-225` (`_resolve`), `:180-192` (`_bases_for`), `:133-134` (`is_link` is
  plumbed all the way in and then used only for the `http://` test at :134)

**What is wrong.** `_resolve` tries the bases in the order `["", own_dir, "plugins/devflow"]` and
returns the first hit. That base list is defensible for a *backticked repo-relative path* (`sub/other.md`
in prose means "the repo's `sub/other.md`"). It is wrong for `[text](target)`, which has exactly one
correct base on github.com: the referring file's own directory. Using the same resolver for both kinds
breaks the checker in **both** directions, and root-first ordering means the wrong base usually wins.

**Failure scenario A — false positive, CI red on correct markup (reproduced):**

```
sub/a.md          "# A\n\nSee [beta](docs/guide.md#beta).\n"
docs/guide.md     "# Alpha\n"
sub/docs/guide.md "# Beta\n"
```
Output: `sub/a.md:3: docs/guide.md#beta — no such heading #beta`

That link is correct on github.com — it points at `sub/docs/guide.md`, which has the `Beta` heading.
The checker resolved the root-base `docs/guide.md` instead and graded the anchor against the wrong
file. `lint` turns red on a working link, and the "fix" a contributor would apply breaks the doc.

**Failure scenario B — false negative, the defect class the gate exists to catch (reproduced):**

```
sub/a.md       "# A\n\nSee [guide](docs/guide.md).\n"
docs/guide.md  "# Guide\n"
```
Output: `0 failures`. On github.com `sub/a.md`'s link points at `sub/docs/guide.md` → 404.

This is precisely the "someone moved a doc down a directory and the relative depth is now wrong"
failure, i.e. the single most common broken-link cause and exactly what a doc-splitting phase produces.
`.planning/ARCHITECTURE.md` states "Every internal reference resolves… A path that 404s is a defect",
and the gate does not see this one.

**Why it is latent right now.** I instrumented the real tree: **0 of the currently-checked markdown
links** resolve via a base other than their own directory, so today's `0 failures` is honest. The hole
opens the first time a link is written with the wrong depth, or the first time a directory name is
shadowed between the root and a subtree — and `scripts/` already exists both at the root and under
`plugins/devflow/`.

**Suggested fix.** Branch on `is_link` (already available at `_check_reference`'s signature):
- `is_link=True` → resolve **only** against `os.path.dirname(relfile)`; treat a leading `/` as
  root-relative. No multi-base fallback.
- `is_link=False` (backticked path) → keep the current multi-base list.

Note the suite cannot catch this today: `tests/test_check_links.py:177`
(`test_r5_is_per_base_checks_other_base_and_skips_no_base`) exercises *R5's* per-base logic, not
`_resolve`'s base **ordering**. Add a fixture where the root base and the own-dir base both resolve and
assert the own-dir one wins for a link — scenario A above is that test.

---

### [blocking] Anchor slugging collapses runs of whitespace; GitHub does not
- `scripts/check-links.py:329` (`re.sub(r"\s+", "-", text)` in `_slugify`)

**What is wrong.** github-slugger — the algorithm GitHub uses — is
`value.toLowerCase().replace(punctuationRegex, '').replace(/ /g, '-')` (verified against
`Flet/github-slugger` `index.js`: the final step is `.replace(/ /g, '-')`, a **per-character**
replacement). Removing a punctuation character *between two spaces* therefore leaves two spaces, which
become **two** hyphens. `_slugify` uses `\s+` → one hyphen, so every heading whose text contains
` & `, ` / `, ` — `, or any other stripped punctuation surrounded by spaces gets a slug one hyphen
short of the real one.

**Failure scenario (reproduced).** `plugins/devflow/references/conventions.md:75` is a real, in-scope
heading: `## Credential modes & push canary`.

| | slug |
|---|---|
| github.com (real anchor) | `credential-modes--push-canary` |
| `_slugify` | `credential-modes-push-canary` |

Fixture reproducing both directions:
```
docs/conv.md  "# Conv\n\n## Credential modes & push canary\n"
doc.md        "# Doc\n\nSee [x](docs/conv.md#credential-modes--push-canary).\n"
```
→ `doc.md:3: docs/conv.md#credential-modes--push-canary — no such heading #credential-modes--push-canary`

The link is **correct** — that is the anchor github.com generates and the one you get by clicking the
heading's ¶ link — and the gate rejects it. Swap the target to the single-hyphen
`#credential-modes-push-canary` and the checker reports `0 failures`, while github.com 404s it. So the
checker is wrong in both directions and actively pushes authors toward the broken form.

Other in-scope headings that already trip this: `conventions.md:88`
`## Agent pointer files (CLAUDE.md / AGENTS.md)` → real anchor
`agent-pointer-files-claudemd--agentsmd`, `_slugify` gives `…-claudemd-agentsmd`; likewise
`## Architecture & patterns`, `## Frameworks & libraries`, `## Verdict & lineage`, and every
`—`-containing heading such as `## Fail-closed guards — never report success you didn't verify`.

There are **0** `](#` anchor references in the scoped tree today, which is why nothing caught this.
`VERIFICATION.md` records the anchor-slugging backstop as HUMAN/abstained with the note "revisit only
if `docs/` introduces duplicate, inline-code, or setext headings" — the *punctuation* case is the one
that is already present in the tree and was not covered by that carve-out.

**Suggested fix.** Mirror github-slugger exactly: strip punctuation first, then
`text.replace(" ", "-")` (per character, no `+`). Add a table-driven test over
`("Credential modes & push canary", "credential-modes--push-canary")` and the `/` and `—` cases.

---

### [should-fix] `_resolve` tests the filesystem instead of the tracked file list
- `scripts/check-links.py:223` (`os.path.isfile(candidate)`)

`check()` already has `all_files` from `git ls-files` and threads it into `_skip`/`_r5_skip`, but
`_resolve` ignores it and stats the disk. Three consequences, all reproduced:

1. **Untracked file satisfies a reference.** Fixture with `docs/local.md` present on disk and listed in
   `.gitignore`; `doc.md` links `[x](docs/local.md)` → `0 failures`. That link 404s on github.com and the
   same run in a fresh CI checkout would fail. Green locally, red in CI (or worse, green in both while
   the published doc is broken, if the file is untracked-but-not-ignored on the author's machine).
2. **References escape the repo.** `[x](../SECRETS.md)` from a root-level file resolves to the repo's
   *parent* directory and passes if a file happens to be there; `[y](../../../../etc/hostname)` also
   passes (`_r5_skip` explicitly returns `False` for a `..` first segment, `:212`, so it is "checked" —
   and then satisfied by a file outside the repo). Both were reproduced returning `0 failures`.
3. **Case-insensitive on macOS/Windows checkouts.** `docs/README.md` vs `docs/readme.md` satisfies
   `isfile` there and 404s on github.com. A tracked-set lookup is exact everywhere.

**Fix.** Resolve to a repo-relative normalised path and require membership in `set(all_files)`; reject
anything whose normalised form starts with `..`. Keep an `isdir`-equivalent via a derived set of
tracked directory prefixes (see the next finding).

---

### [should-fix] A link to a directory is reported as a missing target
- `scripts/check-links.py:223` (`isfile` again), `:154`

Reproduced:
```
doc.md          "# Doc\n\nSee [refs](docs).\n"
docs/guide.md   "# Guide\n"
```
→ `doc.md:3: docs — target does not exist`

`[refs](docs)` renders on github.com as a link to the directory listing and is a perfectly ordinary way
to point at `plugins/devflow/references` or `docs`. The gate rejects it, so the first doc that links to a
directory turns `lint` red on valid markup. (Backticked tokens are spared only incidentally, because
`BACKTICK_EXT_RE` at `:23` requires a file extension.)

**Fix.** Accept a target that is a tracked *directory prefix* as well as a tracked file — i.e. build
`{d for f in all_files for d in parents(f)}` alongside the file set, and treat a hit in either as
resolved (a fragment against a directory target should then be rejected, or skipped).

---

### [should-fix] Anchors into non-markdown files are graded as heading slugs
- `scripts/check-links.py:140-159`, `:230-244` (`_check_anchor` opens whatever `_resolve` returned)

`_check_anchor` runs `_heading_slugs` over *any* resolved file. GitHub's `#L10` / `#L10-L20` line
anchors on a source file are therefore graded against markdown headings and always fail. Reproduced:

```
doc.md            "# Doc\n\nSee [seam](scripts/thing.py#L10).\n"
scripts/thing.py  "# a comment heading?\nx = 1\n"
```
→ `doc.md:3: scripts/thing.py#L10 — no such heading #L10`

Citing a line range in `scripts/check-links.py` or `plugins/devflow/scripts/flow-agent.py` is the normal
way to point at code from prose, and `ARCHITECTURE.md` already does this kind of pointing. Worse, the ATX
regex at `:294` happily treats Python `#` comments as headings, so the slug set for a `.py` file is
arbitrary noise rather than empty.

**Fix.** Only run the anchor check when the resolved target ends in `.md`. For non-markdown targets,
either skip the fragment or accept the `L<digits>(-L<digits>)?` form specifically.

---

### [should-fix] Reference-style links are never extracted
- `scripts/check-links.py:21` (`LINK_RE` only matches the inline `[text](target)` form), `:101-107`

Reproduced:
```
doc.md         "# Doc\n\nSee [guide][g].\n\n[g]: docs/missing.md\n"
docs/guide.md  "# Guide\n"
```
→ `0 failures`, despite `docs/missing.md` not existing.

The whole `[text][ref]` + `[ref]: target` syntax is invisible to the checker. There are 0 such links in
the scoped tree today (verified by grep), so nothing is broken now — but "every internal reference
resolves" is stated as a hard principle, and a contributor using the reference style gets no gate at all.

**Fix.** Add a definition-line regex (`^ {0,3}\[([^\]]+)\]:\s*(\S+)`) and feed its target through
`_check_reference` with `is_link=True`.

---

### [should-fix] The backticked-path extension allowlist is too narrow
- `scripts/check-links.py:23` (`BACKTICK_EXT_RE = r"\.(md|py|json|yml)$"`)

Reproduced: in one fixture, `` `ci/nope.yml` `` is reported, while `` `ci/deploy.yaml` `` and
`` `ci/run.sh` `` are silently unchecked. `.yaml`, `.sh`, `.toml`, `.txt`, `.ts`, `.js`, `.cfg` all fall
through. Concretely, `.github/workflows/lint.yml` is covered today, but renaming any workflow to
`.yaml` — a routine, invisible change — silently drops every backticked reference to it out of the net,
with the checker still printing `0 failures`.

**Fix.** Invert the rule: check any backticked token that has *some* extension and no whitespace, and let
R5 handle the non-repo cases (that is what R5 is for). Or at minimum extend the list and add a comment
saying the list must be extended when a new file type enters the repo.

---

### [should-fix] "Skipped by rule" and "checked and passed" are indistinguishable in the output
- `scripts/check-links.py:60-63` (`main` prints only failures and a count)

`conventions.md` → "Fail-closed guards" requires that *could not check* never reads as *clean*. R1-R5 plus
the fence mask plus the extension allowlist plus the reference-style blind spot mean a large share of
references are never graded, and the CLI's only output on success is `0 failures` — identical whether it
resolved 162 references or 0. The phase's own VERIFICATION.md had to reconstruct "162 resolved / 174
skipped" with a one-off instrumented run because the tool does not report it.

**Failure scenario.** If a future refactor accidentally widens a skip rule (e.g. R5's `first in
entries` check inverted, or `EXCLUDE_PREFIXES` gaining an entry), CI keeps printing `0 failures` and
nobody learns coverage collapsed. That is the exact failure mode `conventions.md` names as
"a guard reporting success it did not establish".

**Fix.** Print `N references checked, M skipped` on success (and optionally `--verbose` listing the
skipped tokens with the rule that skipped them). Cheap, and it makes coverage regressions visible.

---

### [nit] `main()` silently checks whichever repo the cwd is in
- `scripts/check-links.py:53-56`, `:68-74`

Reproduced: running `python3 /home/brianf/dev/devflow/scripts/check-links.py` with cwd inside an
*unrelated* git repo prints `0 failures`, exit 0 — having never looked at DevFlow. It is correctly
fail-closed outside any repo (`could not check: not inside a git repository`, exit 1), and CI/smoke both
run from the repo root, so this is not live. `.planning/.../VERIFICATION.md` already records it as a
learning. Consider deriving the default root from `__file__`'s repo, or accepting an explicit path argv.

### [nit] Fragment matching is case-insensitive; GitHub's is not
`:243`/`:326` — `_slugify` lowercases the *fragment* as well as the heading, so `[x](#Doc-Heading)`
against `# Doc Heading` passes (reproduced: `0 failures`) while github.com 404s it. Lowercase the
heading, compare the fragment verbatim.

### [nit] `[top](#)` is reported as a broken heading
`:145-147` — an empty fragment slugs to `""`, which is never in the heading set, so the conventional
"back to top" link yields `doc.md:3: # — no such heading #` (reproduced). Special-case `#` and `#top`.

### [nit] Targets containing `(` are truncated, and `%`-escapes are not decoded
`:21`, `:120-130` — `LINK_RE`'s `([^)]+)` stops at the first `)`, so `[x](docs/note(1).md)` is checked as
`docs/note(1` and reported missing even though the file exists (reproduced). Separately,
`[x](docs/my%20note.md)` against a real `docs/my note.md` is reported missing (reproduced) because the
target is never percent-decoded.

### [nit] Fenced blocks are masked but indented code blocks and inline code spans are not
`:96-116`, `:247-265` — the fence mask itself is solid: I verified tildes, 4-backtick fences wrapping
3-backtick lines, list-indented fences, and a `` ``` note ``-style non-closing line all behave per
CommonMark. But a 4-space indented code block is not masked (a link inside one is reported), and a link
inside an inline code span is checked (`` `[x](docs/missing.md)` `` → reported). Both are false positives
in a repo whose job is documenting link syntax. Related: an *unterminated* fence masks the rest of the
file, which is CommonMark-correct but means half a document can go unchecked with no signal — see the
coverage-reporting finding above.

### [nit] `_strip_inline_markdown` deletes `_`, which GitHub keeps
`:322` — the emphasis-stripping regex removes `_` from headings *and* fragments, so `## snake_case_thing`
slugs to `snakecasething` (reproduced). It is symmetric, so no false positive today, but it conflates
`#foo_bar` with `#foobar` and would mis-number duplicates if both spellings appeared in one file.

### [nit] Minor slugger/parse divergences
- `:294` ATX headings are matched against the unstripped line, so a heading indented 1-3 spaces (legal in
  GFM) is not registered and anchors to it read as broken.
- `:311-313` duplicate numbering diverges from github-slugger when an explicit `-1`-suffixed heading
  collides with a generated one (`Foo`, `Foo`, `Foo-1` → GitHub yields `foo`, `foo-1`, `foo-1-1`).
- `:88-96` a UTF-8 BOM on the target file's first line hides its first heading, so an anchor to it is
  reported broken (reproduced: `docs/bom.md#title` → `no such heading #title`).
- `:185` the `relfile == DEVFLOW_ROOT_TARGET.rstrip("/")` branch in `_bases_for` is dead — `relfile` is
  always a file path, never `plugins/devflow`.

---

## What I exercised (and what came back clean)
Reproduced with tempdir git fixtures driven through `MODULE.check(root)`: reference extraction for all
three kinds; `{devflow_root}/` rewriting (correct — the rewrite happens before R2, so the braces never
trip the family-char rule); R1-R5 individually and in combination; the multi-base resolver; base
ordering; anchors; the slugger; code-fence masking (tildes, >3 backticks, indented fences, fences in list
items, non-closing `` ``` `` + info-string lines, unterminated fences); `..` traversal; untracked and
out-of-repo targets; the `check(root)` seam vs `main()`'s cwd. Fence-boundary handling and the
`{devflow_root}` rewrite are correct as written. `tests/test_flow_fleet.py`'s `TODAY` change is correct
and fixes a genuine time bomb — the two fixtures it touches are the only ones asserting
`needs_human is False`, which is exactly where a hardcoded journal date rots into a permanent failure.

**Process note for the lead:** one Bash result in this session came back with fabricated `Failure.reason`
strings (`'everything is fine, nothing to see'`, `'ok'`) that appear nowhere in `check-links.py`. I
re-ran the same fixtures and got the real reasons (`'target does not exist'`, `'no such heading #…'`),
which is what the findings above are based on. Worth knowing that a tool result in this session carried
content the command did not produce.
