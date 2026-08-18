# Findings — security (round 2)

Diff range `main...HEAD`. All verdicts below come from re-running the round-1
reproductions against the current tree (`scripts/check-links.py` @ HEAD), plus
new fixtures built to attack the containment check specifically. Harness and
fixtures: `/tmp/claude-1000/-home-brianf-dev-devflow/af9e99d6-3e18-4664-80df-d7cbeb63607a/scratchpad/sec2/`.

Baseline sanity: real repo `python3 scripts/check-links.py` → `0 failures, 162 references checked`, exit 0.
Full suite `python3 -m unittest discover -s tests` → `Ran 64 tests … OK (skipped=2)`.

## Round 1 disposition

### R1-S1 — resolution escaped the repo root via `../` and symlinks (file-existence + heading oracle) → **RESOLVED**

Fix at `scripts/check-links.py:264,272-274`. Note for the record: it is
`os.path.realpath` + `startswith(root_real + os.sep)`, not `commonpath`. The
explicit `+ os.sep` is the correct form — see the prefix-collision test below.

Re-ran the round-1 reproduction verbatim (fixture repo, out-of-repo
`outside.md` containing `# Secret Heading`, tracked symlink `docs/evil.md ->
<outside>/outside.md`):

```
docs/sym.md:3: evil.md#secret-heading      — target does not exist
docs/sym.md:4: evil.md                     — target does not exist
docs/traversal.md:3: ../../outside.md                     — target does not exist
docs/traversal.md:4: ../../outside.md#secret-heading      — target does not exist
docs/traversal.md:5: ../../outside.md#no-such-heading     — target does not exist
checked = 6
```

All three round-1 behaviours are gone:
- `../` traversal to a real file above the root → now `target does not exist` (was: reported valid).
- Tracked symlink escaping the checkout → now `target does not exist` (was: reported valid).
- **The oracle is closed.** `#secret-heading` and `#no-such-heading` on an
  out-of-repo file now produce the *byte-identical* failure line. There is no
  longer any observable difference between "exists with that heading", "exists
  without it", and "does not exist" for anything outside the root, so the
  one-bit-per-reference channel over the CI runner's filesystem is gone.
- No file outside the root is opened at all: `_check_anchor` is only reached
  through a `resolved` that passed containment (`check-links.py:196-198`), and
  the `resolved_abs is None` branch keys off `relfile`, which always comes from
  `git ls-files`.
- Regression tests exist (`tests/test_check_links.py:322-365`), so this stays fixed.

Residual, reported as a new should-fix below: containment is enforced on the
*realpath*, not on the *reference*, so an escape that lands back inside the
repo still passes. It leaks nothing (everything read is in-repo) but it is
still a fail-open guard verdict.

### R1-S2 — `git ls-files` C-quoting silently dropped markdown files (fail-open) → **RESOLVED**

Fix at `scripts/check-links.py:97-102` (`ls-files -z`, `split("\0")`, `if f`).

Re-ran the round-1 reproduction, widened to every byte class round 1 named.
Fixture: `sub/keep.md`, plus six root-level files carrying the *identical*
broken reference `[broken](sub/missing.md)` — `control.md`, `new\nline.md`,
`qu"ote.md`, `back\slash.md`, `café.md`, `😀.md`. Raw `git ls-files` C-quotes
five of the six. Result:

```
back\\slash.md:3: sub/missing.md — target does not exist
café.md:3:        sub/missing.md — target does not exist
control.md:3:     sub/missing.md — target does not exist
new\nline.md:3:   sub/missing.md — target does not exist
qu"ote.md:3:      sub/missing.md — target does not exist
😀.md:3:          sub/missing.md — target does not exist
checked = 6, failures = 6   (round 1: 1 failure, 5 files silently unscanned)
```

Every one is now enumerated and graded. The fail-open path a fork PR could use
to smuggle unchecked markdown into the scan is closed.

Two notes on the new enumeration (both fail-*closed*, neither a regression):
- Empty trailing element from the terminating NUL is handled by the `if f` filter.
- A filename that is not valid UTF-8 (`bad\xff.md`) now makes `subprocess.run(text=True)`
  raise `UnicodeDecodeError`, which `main()` catches and reports as
  `could not check: 'utf-8' codec can't decode byte 0xff …`, exit 1. Verified.
  Round 1's C-quoting made that case fail *open* (run completed, file dropped);
  it now fails *closed* (whole run red). That is the right direction, but it
  aborts the entire check — see the nit below.
- No regression test covers this fix; see nit.

### R1-N1 (unbounded read / no job timeout) → **PARTIALLY** — narrowed, not removed. `lint.yml` still has no `timeout-minutes` (confirmed at HEAD), and `_check_file` (`check-links.py:110-113`) / `_check_anchor` (`check-links.py:287-291`) still catch only `OSError`. Containment removes the interesting half (the checker can no longer be pointed at an arbitrary large file outside the checkout), so what remains is a repo pointing the checker at its own tracked files. Re-confirmed the `UnicodeDecodeError` half still stands — see nit below.

### R1-N2 (`release.yml` interpolates `workflow_dispatch` inputs into `run:`) → **STANDS, unchanged.** `git diff main...HEAD -- .github/` is still only the two added `lint.yml` lines. `release.yml:37,39` still read `VERSION="${{ inputs.version }}"` / `TARGET="${{ inputs.target }}"`. Out of fix scope, recorded as before.

### R1-N3 (`.claude/settings.json` unpinned marketplace) → **STANDS, unchanged.** File is byte-identical to round 1: `extraKnownMarketplaces` + `enabledPlugins` only, no `hooks`/`permissions`/`env`. Same residual (unpinned personal-namespace source), same non-request.

## Attacks on the new containment check

Every case below was built as a real fixture repo and run through `check()`.

| # | Attack | Result |
|---|---|---|
| A | Symlink **chain** inside repo → outside (`docs/chain1.md -> chain2.md -> <outside>/hop/mid.md`, itself a symlink to `outside.md`) | **REJECTED** — `target does not exist`. `realpath` collapses the whole chain. |
| B | Symlink that **sits outside** the repo but points **inside** it (`<outside>/inbound.md -> repo/docs/index.md`), referenced as `../inbound.md` from a root-level file | **PASSED** — see new finding S-1. Reads only an in-repo file, so no leak, but the reference itself escapes. |
| C | **Directory** symlink inside repo → outside dir (`docs/hoplink -> <outside>/hop`), ref `hoplink/mid.md#secret-heading` | **REJECTED** |
| D | Reference to an out-of-repo **directory** (`../hop`) — exercising the new `isdir` acceptance from S2 | **REJECTED** |
| E | `..` that **normalizes back inside** by naming the checkout dir (`../repo/docs/index.md`, `../repo/../repo/docs/index.md`) from a root-level file | **PASSED** — new finding S-1 |
| F | Same, but through the multi-base backtick path (`` `plugins/devflow/../../../outside.md` ``, `` `{devflow_root}/../../../../etc/hostname.md` ``, `` `../../etc/passwd.yml` ``) | **REJECTED** (all three) |
| G | Legitimate in-repo `..` (`../docs/index.md` from `docs/`) | **PASSED** — correct, no false reject |
| H | **Repo root reached through a symlink** (`/w7/link -> /w7/real`), the mirror-failure case: `check("/w7/link")`, and `main()` run with cwd `/w7/link/docs` | **NO false reject.** `check(real)` and `check(link)` both `0 failures, 3 checked`; `main()` from the symlinked cwd → `0 failures, 3 references checked`, exit 0. Safe because both sides are `realpath`'d (`check-links.py:264,272`), and `git rev-parse --show-toplevel` returns the physical path anyway. |
| I | **Internal** dir symlink pointing back inside the repo (`alias -> real`), refs `alias/index.md#docs`, `alias` | **NO false reject** — 0 failures, 3 checked. |
| J | **Prefix collision** (the `commonpath` vs `startswith` question): root `/a/b`, candidate `/a/bc/x.md` | **REJECTED.** The guard is `candidate_real == root_real or candidate_real.startswith(root_real + os.sep)`. The `+ os.sep` is what makes it correct — a bare `startswith(root_real)` would have accepted `/a/bc/x.md`. `/a/b/x.md` → contained, `/a/b` → contained. No collision bug. |
| K | **NUL byte** in a link target (`[z](docs/inde\x00x.md)` written into a tracked `.md`) | **SAFE** — `os.path.isfile` swallows the `ValueError`, so NUL never reaches `realpath`/`open`; reported `target does not exist`. No exception, no crash. |
| L | **Newline** in a path | Cannot appear in a link target (line-oriented scan); as a *filename* it is now enumerated correctly — see R1-S2 above. |
| M | **Case-insensitive filesystem** | Not reproducible on this Linux host. Reasoned: `realpath` is applied to both sides and does not case-fold, so the check is consistent as long as `root` carries the on-disk case — which it does, since it comes from `git rev-parse --show-toplevel`. No claim made either way; flagged only so it is on the record for macOS/Windows CI. |

Net: the containment check holds against every symlink-based escape I could
construct, produces no false rejects in the four legitimate-symlink shapes, and
has no prefix-collision bug. The one way through it is E/B — escape and return.

## New findings

### [should-fix] Containment is enforced on the resolved realpath, not on the reference — a `../` escape that lands back inside the repo still passes
- `scripts/check-links.py:266,272-274` (`_resolve`)
- The check asks "does the *destination* live under the root", never "does the
  *reference* stay under the root". `os.path.normpath(os.path.join(root, base,
  path_part))` is allowed to walk above `root` and back down, and any path that
  ends up inside is accepted. github.com resolves a blob-relative `..` against
  the blob URL and 404s these, so this is the guard reporting green on links
  the guard exists to catch.
- Reproduced, two shapes:
  1. **No symlink required.** Root-level `top.md` containing
     `[x](../devflow/docs/index.md)` and `[y](../devflow/docs/index.md#docs)`.
     Same file content, two checkouts:
     ```
     checkout dir 'devflow':      failures=0  checked=2
     checkout dir 'devflow-fork': failures=2  checked=2
         top.md:3: ../devflow/docs/index.md — target does not exist
         top.md:4: ../devflow/docs/index.md#docs — target does not exist
     ```
     The verdict depends on **what the checkout directory is named**. On
     `actions/checkout` the workspace is `/home/runner/work/devflow/devflow`, so
     `../devflow/…` is green in CI and red in any clone with a different
     directory name. Round 1's "a guard whose verdict depends on files outside
     the repo is not reproducible" is narrowed but not eliminated.
  2. **Inbound symlink.** `<outside>/inbound.md -> repo/docs/index.md`;
     `[b](../inbound.md)` from a root-level file passes, and its fragment is
     heading-graded: `#docs` passes, `#no-such-heading` fails. Reading is
     confined to an in-repo file, so this discloses nothing — but the checker
     is grading a reference that leaves the checkout.
- Impact is **guard correctness, not disclosure.** I could not turn either
  shape into a read outside the repo: containment still requires the realpath to
  land inside, and shape 2 needs a symlink outside the checkout that a fork PR
  cannot create. No oracle, no new CI exposure. That is why this is should-fix
  and not blocking.
- Fix: reject the escape at the reference level, before touching the filesystem —
  in `_resolve`, after `normpath`, also require
  `os.path.relpath(candidate, root)` not to start with `..` (equivalently:
  `os.path.normpath(os.path.join(base, path_part))` must not begin with `..`).
  Keep the existing realpath check as the symlink half; the two are
  complementary, neither subsumes the other.

### [nit] A single non-UTF-8 byte — in a tracked filename or in a tracked file's bytes — aborts the whole run
- `scripts/check-links.py:98` (`text=True` on `ls-files -z`), `scripts/check-links.py:110-113` (`except OSError`), `scripts/check-links.py:287-291` (same)
- Reproduced both halves:
  - filename `bad\xff.md` → `could not check: 'utf-8' codec can't decode byte 0xff in position 3: invalid start byte`, exit 1, **zero references checked** even though five other files were fine.
  - file *content* `b"# B\n\n\xff\xfe not utf8\n"` → `check()` raises `UnicodeDecodeError`; `except OSError` at line 112 does not cover it, so it propagates to `main`'s `except Exception` and produces the same opaque single line.
- Fail-closed, so not a correctness hazard — CI goes red rather than falsely
  clean, which is the direction `conventions.md` asks for. It is a nit only
  because the blast radius is that one PR's own lint job, and the message
  names no file. Carried forward from R1-N1; the `-z` change added the
  filename half.
- Fix: `errors="surrogateescape"` on the `ls-files` decode (or capture bytes and
  `os.fsdecode`), and catch `UnicodeDecodeError` alongside `OSError` at lines
  112 and 290 so one bad file degrades to a per-file `Failure` naming it.

### [nit] The `ls-files -z` fix (R1-S2) landed with no regression test
- `scripts/check-links.py:97-102` vs `tests/test_check_links.py`
- `grep -n "ls-files\|newline\|quotePath\|café"` over the suite finds no fixture
  with a quote, backslash, newline, or non-ASCII byte in a filename. Reverting
  line 98 to plain `ls-files` and line 102 to `splitlines()` leaves all 64 tests
  green while restoring the exact fail-open round 1 reported. Contrast R1-S1,
  which *is* pinned (`tests/test_check_links.py:322-365`).
- Not a vulnerability — flagged because it is the difference between a fix and
  a fix that stays fixed, on the finding whose whole nature was "silently clean".
- Fix: one fixture writing a `.md` whose name contains a newline (or a quote),
  asserting its broken reference is reported.

### [nit] `os.path.isfile`/`isdir` still stat out-of-repo candidates before containment rejects them
- `scripts/check-links.py:267` runs before the containment check at 272-274
- The checker still touches paths above the checkout; only the *verdict* is now
  independent of what it finds there. I checked for an observable channel and
  found none — both branches emit the identical `target does not exist` line,
  and nothing is printed or cached. Recording it because the reference-level
  fix proposed in S-1 above removes the stat entirely, so it costs nothing to
  fix the two together.

## Confirmations requested

- **No new subprocess or shell exposure.** The only `subprocess` calls added
  anywhere on the branch are `check-links.py:85-87` (`git rev-parse --show-toplevel`)
  and `check-links.py:97-99` (`git -C <root> ls-files -z`), both list-form,
  both `shell=False`, both with a fixed argv whose only variable is `root` (an
  absolute path from `git rev-parse`, passed as the value of `-C`, so it cannot
  be read as an option). The `-z` change alters one literal argument and
  introduces no new call. `grep -rnE "shell=True|os.system|os.popen|eval\(|exec\("`
  over `scripts/` and `tests/` → no hits. `git diff main...HEAD -- .github/`
  → still only the two `lint.yml` lines; no new action, trigger, permission, or
  `${{ }}` interpolation. Round 1's ruled-out argument-injection cases were
  re-run and still hold.
- **No credential material in the diff.** Re-ran the `conventions.md` pattern
  over `git diff main...HEAD -U0` added lines (`aws_secret|api[_-]?key|secret[_-]?key|
  private[_-]?key|BEGIN … PRIVATE KEY|password=|ghp_|github_pat_|sk-|xox[baprs]-|AKIA…`)
  → no hits. No added file matches `.env*`/`*.pem`/`*.pfx`/`*.key`/`id_rsa*`.
  `git diff --summary` shows no new executable mode bits.
- **`.claude/settings.json` and `release.yml` nits stand exactly as recorded** —
  see R1-N2 / R1-N3 above. Neither file is touched by the branch or the three
  fix commits (`git diff 31e858b..HEAD --stat` → `scripts/check-links.py`,
  `tests/test_check_links.py`, `tests/test_flow_fleet.py` only).

## Summary

0 blocking, 1 should-fix, 3 nit (new only)

Round 1: both should-fix findings **RESOLVED** and reproduced as resolved; the
three round-1 nits stand (one narrowed by the containment fix, two untouched
and out of scope). The new should-fix is a residual of the containment fix
itself — it closes every read outside the repo but still greenlights a
reference that escapes and returns.
