# Findings — architecture

## Summary
2 blocking, 5 should-fix, 3 nit

Overall shape is sound. ~330 lines, stdlib-only, `check(root)` returns data and prints nothing,
`main()` is the only I/O. The R1–R5 rule set has **not** accreted special cases — it is five
predicates and three resolution bases, all readable in one screen, and D-07's decision to check
backticked paths (619 refs vs 2 markdown links) is the right call and is what makes the tool
worth having. Runtime is 0.14s over 50 files; scale is a non-issue through phase 04.
The defects below are in **resolution semantics and self-observability**, not in the rule set.

## Findings

### [blocking] Multi-base resolution is applied to `[text](target)` links, so the checker green-lights links github.com 404s
- `scripts/check-links.py:220-225` (`_resolve`), `:180-192` (`_bases_for`), `:133-134` (`is_link` is threaded in but only used for the `http://` guard)
- `_resolve` tries every base — repo root first, then the referring file's own directory, then
  `plugins/devflow/` — for **all** reference kinds. That is correct for backticked *textual*
  pointers, which are base-ambiguous by nature (D-08/D-09 are about exactly that). It is wrong for
  `[text](target)`: GitHub resolves a markdown link relative to the **referring file only**. Because
  root is tried *first*, a root-relative link target resolves against the wrong base and passes.
  Measured, from the real repo:

  ```
  from docs/README.md                          [x](docs/status-contract.md)  -> checker PASS, GitHub 404
  from docs/README.md                          [x](docs/blitzos.md)          -> checker PASS, GitHub 404
  from docs/blitzos.md                         [x](README.md)                -> checker PASS, GitHub 404
  from plugins/devflow/references/autonomy.md  [x](docs/status-contract.md)  -> checker PASS, GitHub 404
  ```

  This contradicts two human-owned constraints at once: ARCHITECTURE.md:47 "Public prose
  (`README.md`, `docs/*.md`) must render on github.com with no build step" and ARCHITECTURE.md:20
  "Every internal reference resolves. A path that 404s is a defect, not a nit."
- **failure scenario**: Phase 03 writes `docs/README.md`, the index REQ-04 requires, whose accept
  criterion is *"link count = `docs/*.md` − 1; all resolve"*. The natural way to write that index —
  copying the paths straight out of the roadmap/requirements, which spell them `docs/execution-model.md`
  — produces `[Execution model](docs/execution-model.md)` inside `docs/README.md`. Every row resolves
  to `docs/docs/…` for a real reader and 404s. `check-links.py` prints `0 failures`, `lint` is green,
  SC-02 ("zero unresolvable internal references — the checker exits 0") is satisfied, and REQ-04 is
  recorded as met. The single artifact phase 03 exists to produce is the one the safety net cannot see.
  The same hole covers phase 04's repointing: a repointed link written root-relative is accepted.
- **suggested fix**: resolve on `is_link`. For `is_link=True`, resolve strictly against
  `os.path.dirname(relfile)` (one base, GitHub's rule); keep the multi-base walk for backticked
  tokens and `{devflow_root}/…`. **This is not a checkpoint decision** — D-09 constrains *skip* rules
  ("evaluated per resolution base, never root alone"), not link resolution, and REQ-09a already says
  "`[text](target)` **relative** paths". It is also free today: both existing in-scope markdown links
  (`README.md:7`, `README.md:44`) resolve identically under the strict rule, so tightening changes no
  current result. Add one test per direction, mirroring how 01-02 pinned R5.

### [blocking] The checker cannot report that it went blind — one stray fence line silently disables checking for the rest of a file
- `scripts/check-links.py:247-265` (`_code_fence_mask`), `:96-99` (applied per referring file); `:62` (the only output on success)
- An unterminated fence sets `in_fence` and never clears it, so every line to EOF is masked. Nothing
  distinguishes that from a clean file: the tool prints `0 failures` and exits 0 whether it examined
  295 references or 3. There is no reference count, no coverage floor, no unterminated-fence error.
  The VERIFICATION team hit this gap already and had to hand-instrument the script to prove the green
  run was non-vacuous ("162 path refs actually resolved"); that instrumentation lives in a throwaway
  probe, not in the tool, so phases 02–04 re-run it many times with no such evidence.
- **failure scenario**: demonstrated, not hypothesized. Fixture with a `docs/execution-model.md`
  containing a fenced ASCII diagram (REQUIREMENTS assumes exactly this diagram survives the move) plus
  two broken refs below it:

  ```
  closing fence present  -> 2 failure(s), exit 1
  closing fence deleted  -> 0 failures,   exit 0     # same two broken refs, still there
  ```

  Phase 02 carves README's fenced blocks into `docs/` pages; a dropped or mis-indented closing fence
  during that move is an ordinary editing slip. From that point the file is unchecked forever, phases
  03–04 repoint references into the dead zone, and CI stays green. The failure conceals itself and
  gets *more* likely as the phases proceed, which is the opposite of what a safety net must do.
- **suggested fix**: two small additions, no redesign. (1) In `check()`/`main()`, return and print the
  number of references actually resolved — `0 failures, 295 references checked` — so a collapse in
  coverage is visible in the CI log and diffable across runs. (2) Make an unterminated fence a
  `Failure`, not a silent mask; a markdown file with an odd fence is malformed regardless of links.
  Optionally assert a floor in `tests/test_check_links.py` against the real repo.

### [should-fix] Resolution escapes the repo root, so results depend on what sits outside the checkout
- `scripts/check-links.py:222` — `os.path.normpath(os.path.join(root, base, path_part))` with no
  containment check
- `../../../../etc/passwd` from `docs/blitzos.md` resolves to `/etc/passwd` and **passes**. With three
  bases a `../` token gets three independent chances to climb out. The verdict for such a reference is
  a function of the machine's filesystem above the checkout, so a developer laptop and an
  `actions/checkout` runner can legitimately disagree.
- This is not theoretical for this repo: the **one** real defect phase 01 found (84e6eb7) was exactly
  this shape — `../docs/status-contract.md` in `plugins/devflow/references/autonomy.md`. It was caught
  only because `/home/brianf/dev/docs/status-contract.md` happens not to exist. A sibling checkout, a
  monorepo parent, or a differently-laid-out CI workspace flips that to a pass, or flips a good ref to
  a failure.
- **suggested fix**: after `normpath`, require `os.path.commonpath([candidate, root]) == root`;
  otherwise treat as not-resolved (a ref that leaves the repo cannot render on GitHub either).

### [should-fix] `main()` derives the root from cwd and `argv` is inert — `check(root)` is the only real seam
- `scripts/check-links.py:53` (`def main(argv=None)`, `argv` never referenced), `:68-74` (`_repo_root`
  runs `git rev-parse --show-toplevel` with no `-C`)
- The `check(root)`/`main()` split is otherwise clean — `check()` prints nothing, takes an explicit
  root, and importing the module has no side effect (all verified). But `main()` gives a caller no way
  to reach that parameter: the one place a `--root` would naturally go is accepted and discarded, which
  advertises an option that does not exist.
- The cwd coupling has a sharper edge than "smoke happens to run from the repo root". `EXCLUDE_PREFIXES`
  and `DEVFLOW_ROOT_TARGET` (`:17-19`) are hardcoded to **this** repo, but nothing binds the script to
  it. Confirmed: `python3 /home/brianf/dev/devflow/scripts/check-links.py` run from an unrelated git
  repo cheerfully scanned that repo and reported `2 failure(s)`, applying DevFlow's `.planning/`
  exclusions and `{devflow_root}` rewrite to a project that has neither. A repo-specific tool that
  silently accepts any repo produces confident, meaningless output.
- **suggested fix**: resolve the root from `__file__` (`os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`),
  or at minimum wire `argv` to an optional `--root` and default to the script's own repo. Either makes
  the invocation location irrelevant.

### [should-fix] Fence-skipping is a sixth rule that appears in no constraint document — real drift from the human-owned contract
- design-level; `scripts/check-links.py:96-99` vs `.planning/ARCHITECTURE.md:27-33`, `.planning/REQUIREMENTS.md` REQ-09e
- ARCHITECTURE.md `## Link checking` states what is checked and states that non-repo refs are skipped
  **by rule**; REQ-09e defines "rule" as a property of the *token* (not repo-relative). A reference
  inside a fence is fully repo-relative — skipping it is authorized by neither document. The limit is
  recorded only in `LEARNINGS.md`, `MAP.md:57` and `VERIFICATION.md`, all agent-written; the
  human-owned constraint still promises coverage the code does not deliver.
- The stated measurement is also narrower than it reads. "0 otherwise-checkable backticked refs sit
  inside fences" is true, but there are **2 live in-fence references today** —
  `docs/status-contract.md:90` and `plugins/devflow/references/hosts.md:40`, both
  `{devflow_root}/scripts/*.py`, the D-08 class the checker was built for. They escape because they are
  bare rather than backticked, which is in-contract, but the net effect is that renaming
  `flow-fleet.py` breaks two documented invocations with no CI signal. Worth stating plainly rather
  than leaving "0" on the record.
- I would **not** extend coverage into fences (a fenced example is often deliberately illustrative).
  The fix is to make the limit part of the contract, not to change behavior.
- **suggested fix**: add one clause to ARCHITECTURE.md `## Link checking` — "references inside fenced
  code blocks, and bare (non-backticked) paths anywhere, are out of scope" — so phases 02–04 plan
  around a stated boundary instead of rediscovering it. Pair with the unterminated-fence error above.

### [should-fix] Directory link targets are reported broken; phase 03's README "Documentation" section is the likely trigger
- `scripts/check-links.py:223` — `_resolve` accepts only `os.path.isfile`
- `[Documentation](docs/)` and `[Documentation](docs)` both produce `target does not exist`. GitHub
  renders a directory link as a folder listing; it is a normal, correct thing to write.
- **failure scenario** (false positive, self-announcing rather than silent): phase 03 writes REQ-01's
  Documentation section, links `docs/`, CI goes red on a link that is fine. The hazard is the fix —
  under time pressure the cheap repair is to widen a skip rule, and a weakened rule is permanent.
- **suggested fix**: accept a directory target when `os.path.isdir(candidate)`, ideally only for
  `is_link=True`.

### [should-fix] "Docs are pointers, never copies" is violated inside this diff
- design-level. ARCHITECTURE.md:18 makes single-sourcing binding; four facts are now multi-homed:
  - **Checker scope.** ARCHITECTURE.md:30 ("tracked `.md` except `plugins/devflow/templates/**` and
    `.planning/**`") restates REQ-09d verbatim in substance. Two human-owned files must change together
    if phase 02–04 adjusts scope. REQUIREMENTS.md already models the right pattern for this — its
    header says "Rationale lives in PROJECT.md's D-NN table, not here" — but ARCHITECTURE.md does not
    take the same discipline toward REQ-09.
  - **Smoke command.** The full three-step string appears at ARCHITECTURE.md:24, `MAP.md:43`, and as
    three steps in `.github/workflows/lint.yml`. `MAP.md:42` cites ARCHITECTURE.md as the source and
    then copies the command anyway — a pointer and a copy in the same sentence.
  - **D-07/D-08/D-09.** `phases/01-link-safety-net/CONTEXT.md` "## Locked" restates all three decisions
    *with their rationale*, which is PROJECT.md's decision table's job. Phase CONTEXT is a reasonable
    place to name which decisions bind; restating the "why" is the copy.
  - **The fence limitation.** Stated three times (`LEARNINGS.md` bullet 1, `MAP.md:57`,
    `VERIFICATION.md` Learnings) and, per the finding above, in none of the places that are normative.
- CLAUDE.md and AGENTS.md being byte-identical is **not** a finding — `references/conventions.md:93`
  mandates it, and both are pointer tables with no restated content.
- **suggested fix**: cut ARCHITECTURE.md `## Link checking` to the parts that are genuinely *constraints*
  (stdlib-only, no network, no allowlist file, external URLs out of scope, fences out of scope) and let
  it point at REQ-09a–e for the reference kinds and scope. Have `MAP.md` point at ARCHITECTURE.md
  `## Smoke` instead of copying the string. This matters beyond tidiness: phases 02–04 are a
  *deduplication* project, and the guard phase should not model the behavior those phases exist to undo.

### [nit] Anchors are validated against non-markdown targets
- `scripts/check-links.py:230-244` — `_check_anchor` runs whenever a fragment is present, regardless of
  target type
- `[x](scripts/check-links.py#L10)` → `no such heading #L10`. GitHub line anchors on source files are a
  standard idiom and phase 02–04 pages may well cite one.
- **suggested fix**: only harvest headings when the resolved target ends in `.md`; treat fragments on
  other file types as unchecked.

### [nit] Query strings and percent-encoding are not stripped from link targets
- `scripts/check-links.py:120-130` (`_parse_link_target`), `:140-143`
- `[x](docs/blitzos.md?plain=1)` → `target does not exist`; `%20` in a path is likewise not decoded.
  Low likelihood in this repo's register, but it is a false positive, which carries the same
  weaken-the-rule risk as the directory case.

### [nit] The safety net covers no non-`.md` file, including one of REQ-08's two named repoint targets
- design-level; scope is `.md` by REQ-09d, so this is in-contract, and D-05 already routes prose
  mentions to a manual sweep
- Worth stating on the record anyway: ARCHITECTURE.md:20's principle ("every internal reference
  resolves") is strictly broader than what CI enforces. `.github/ISSUE_TEMPLATE/config.yml` — named in
  REQ-08 — carries an external `#readme` URL that is out of scope twice over, and
  `plugins/devflow/skills/flow-status/SKILL.md`'s prose section names are uncheckable by construction.
  Phase 04 should not treat a green `lint` as evidence that REQ-08 is done.

---

## What I assessed
Read `.planning/ARCHITECTURE.md`, `REQUIREMENTS.md`, `PROJECT.md` (D-01–D-12), `ROADMAP.md`,
`LEARNINGS.md`, `DECISIONS.md`, all of `.planning/phases/01-link-safety-net/`,
`.planning/codebase/MAP.md`, `CLAUDE.md`/`AGENTS.md`, `.github/workflows/lint.yml`,
`.claude/settings.json`, `references/conventions.md`, and `scripts/check-links.py` in full.

Verified by running, not by reading: current repo → `0 failures`, exit 0, 0.14s. Instrumented the
module to count 295 in-scope references actually checked and 0 checkable-but-fenced backticked refs
(confirming VERIFICATION's claim) while finding 2 bare in-fence `{devflow_root}` refs it did not
count. Probed ~30 reference shapes through `_check_reference` against the live repo. Built three
throwaway git fixtures to demonstrate the unclosed-fence blindness, the cwd leak, and the
root-relative-link acceptance. Enumerated both in-scope markdown links and confirmed the proposed
strict-resolution fix changes neither.

Checked and found **clean**: no new dependency (imports are `os/re/subprocess/sys/typing`; the only
external process is `git`, already implicit in the repo's own workflow); no `src/`, no build step, no
package manifest; `lint.yml` still has exactly one `uses:` (`actions/checkout@v4`) and no
`pip`/`setup-python`; manifest versions untouched; `check()` is import-safe and side-effect-free;
`.claude/settings.json` matches `conventions.md`'s prescribed self-bootstrap block byte for byte.
The R5 per-base rule is correctly implemented and correctly tested in both directions — D-09 landed as
specified. Nothing here forecloses a future option: the rule set is small enough to extend, and every
finding above is a localized change rather than a redesign.
