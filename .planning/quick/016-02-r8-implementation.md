<!-- .planning/quick/016-02-r8-implementation.md -->
---
phase: quick-016
plan: 02
wave: 2
depends_on: []
files_modified:
  - plugins/devflow/templates/hooks/secret-scan-guard.py
  - tests/test_flow_hooks.py
  - plugins/devflow/skills/flow-hooks/SKILL.md
  - plugins/devflow/references/conventions.md
autonomous: true
requirements: [R8]
must_haves:
  truths:
    - "a literal matching a regex declared on an ARCHITECTURE.md Forbidden entry is blocked at commit by the same fail-closed path as a credential"
    - "the block reports file, line and pattern class and never the matched value"
    - "a Forbidden entry with no regex is not enforced, and nothing claims otherwise"
    - "an unreadable or malformed ARCHITECTURE.md is reported as could-not-check, never silently skipped"
    - "a declared regex is treated as data, never interpolated into a shell command"
  artifacts: [plugins/devflow/templates/hooks/secret-scan-guard.py, tests/test_flow_hooks.py]
  key_links: ["flow-hooks/SKILL.md describes only what the shipped script actually does"]
---

<objective>
R8's acceptance was never met: conventions.md, templates/architecture.md and flow-hooks/SKILL.md
all describe a Forbidden-regex scan the shipped hook does not perform. Implement it.
</objective>

<context>
- /home/brianf/Work/devflow/.planning/ARCHITECTURE.md — law. STDLIB ONLY. Note its own `## Forbidden` section for the shape you are parsing.
- /home/brianf/Work/devflow/plugins/devflow/templates/architecture.md — documents the `— pattern: \b…\b` syntax on a Forbidden bullet (already landed).
- /home/brianf/Work/devflow/plugins/devflow/references/conventions.md — `## Secret scan (fail-closed)` and `## Fail-closed guards`.
- /home/brianf/Work/devflow/plugins/devflow/templates/hooks/secret-scan-guard.py — the guard, freshly hardened; read GIT_DIFF_FORMAT_ARGS and the COULD_NOT_PARSE handling first.
- /home/brianf/Work/devflow/tests/test_flow_hooks.py — house test style; `GitFixture`, `run_hook`.

THE FINDING, from two independent review lenses (security and architecture), verified:
`grep -rn Forbidden plugins/devflow/templates/hooks/*.py` returns nothing. flow-hooks/SKILL.md
states the guard "reads .planning/ARCHITECTURE.md's Forbidden entries and applies any regex they
declare" and treats an unreadable ARCHITECTURE.md as could-not-check. It does none of this. A
user adds `— pattern: \bTEAMID1234\b` to a Forbidden bullet, runs /flow-hooks, and commits that
literal with no block and no warning — a guard documented as machine-checked that is not, which
is the exact defect class the same commit claimed to close.

A THIRD finding, same feature: conventions.md tells an agent to run a repo-controlled regex but,
unlike the canonical secret pattern two lines above it (which says "write this pattern to a temp
file … and `grep -inEf <pattern-file>`"), states no safe-invocation rule — so the natural reading
is interpolation into a shell `grep -E "<regex>"`.
</context>

<tasks>

<task type="auto">
  <name>Task 1: implement the Forbidden-regex scan in the guard</name>
  <files>plugins/devflow/templates/hooks/secret-scan-guard.py</files>
  <action>
Add a pass that reads `.planning/ARCHITECTURE.md` from the payload's `cwd`, extracts the regexes
declared on `## Forbidden` bullets, and applies them to the same added lines the secret pattern
already scans. Reuse the existing diff plumbing and the existing hit-reporting path — one guard
doing one more check, not a parallel implementation.

Rules that matter:
- **Compile with `re.compile`, never shell.** The regex is repo-controlled text. It is data.
- A malformed regex (`re.error`) is **could-not-check**: report it naming the entry, and BLOCK.
  Do not skip it and do not let it pass as clean.
- A missing `.planning/ARCHITECTURE.md` is not an error — most repos have none. That is "no
  patterns declared", which is different from "could not read the ones that exist". An
  ARCHITECTURE.md that EXISTS but cannot be read or parsed is could-not-check → BLOCK.
- A Forbidden bullet with no `pattern:` is not enforced. Silently. That is correct and documented.
- Report file, line and **pattern class** — the Forbidden entry's prose text, not the matched
  value. Never echo what matched. Follow exactly what the credential path already does.
- Scope: the same outgoing diff the guard already computes (commit and push paths both).

Keep it stdlib-only and proportionate — this is one function plus a call site.
  </action>
  <verify>
Throwaway repo OUTSIDE this repo with `.planning/ARCHITECTURE.md` containing a `## Forbidden`
section with a bullet ending `— pattern: \bFORBIDDENLITERAL\b`. Stage a file containing that
literal, run the guard on a `git commit` payload: exit 2, stderr names the file and the entry's
prose, and does NOT contain `FORBIDDENLITERAL`. Then: same repo, staged file WITHOUT the literal →
exit 0. Then: a malformed regex (`— pattern: [unclosed`) → exit 2 naming could-not-check.
Then: no ARCHITECTURE.md at all → exit 0 (not an error).
  </verify>
  <falsify>
Before accepting, run the literal fixture against the CURRENT guard (`git show HEAD:plugins/devflow/templates/hooks/secret-scan-guard.py`
to a temp path). It MUST exit 0 — that is the reported bug. If it already blocks, the feature was
somehow present and the finding is wrong; say so rather than "fixing" what works.
Then remove only your `re.error` handling and confirm the malformed-regex fixture stops exiting 2.
  </falsify>
  <done>Forbidden literals blocked, matched value never echoed, malformed regex is could-not-check, missing ARCHITECTURE.md is benign, and the pre-fix guard was shown to allow the literal.</done>
</task>

<task type="auto">
  <name>Task 2: regression tests</name>
  <files>tests/test_flow_hooks.py</files>
  <action>
Add tests to `SecretScanGuardTests` in the file's existing idiom (`GitFixture`, `run_hook`,
runtime-built fixture strings so this file is never itself a scan hit). Cover: a forbidden literal
is blocked; the matched value never appears in stderr; a clean commit in the same repo is allowed;
a Forbidden bullet with no `pattern:` is not enforced; a malformed regex blocks as could-not-check;
a missing ARCHITECTURE.md is benign; and the push path is covered as well as commit.

Assert the block came from the Forbidden path specifically — not from the credential pattern and
not from the could-not-parse fallback, both of which also exit 2. Reuse the `_assert_real_hit`
style helper already in the class if it fits, or add a sibling for this pattern class.
  </action>
  <verify>
`python3 -m unittest tests.test_flow_hooks -v 2>&1 | tail -5` → OK, 0 failures; test count higher
than before. Full suite `python3 -m unittest discover -s tests 2>&1 | tail -3` → OK.
  </verify>
  <falsify>
Break the guard's Forbidden pass (make `re.compile` results never be applied) and confirm the new
tests fail — naming which. Restore. A test that stays green with the feature disabled is testing
nothing; rewrite it and report that in your SUMMARY.
  </falsify>
  <done>Every listed case has a test, each shown to fail with the feature disabled, full suite OK.</done>
</task>

<task type="auto">
  <name>Task 3: make the prose match the code, and state the shell-safety rule</name>
  <files>plugins/devflow/skills/flow-hooks/SKILL.md, plugins/devflow/references/conventions.md</files>
  <action>
flow-hooks/SKILL.md: the description of the Forbidden-regex behavior is now TRUE, so it stays —
but reviewers found it restates the guard's contract three lines below the file's own rule that
"Full script contracts live in the scripts themselves … read them there rather than restating
them here". Cut the added paragraph down to a one-line pointer; the guards table row already names
the behavior and conventions.md already states the rule.

conventions.md: add the safe-invocation rule the Forbidden-regex paragraph is missing, reusing the
existing mechanism rather than inventing one: write each declared regex to a temp file and match
with `-f <pattern-file>`; never interpolate a declared regex into a shell command. Say plainly
that a regex is data, never shell. Also trim the reporting sentence there — reviewers noted it
says "Same reporting rule as above" and then restates the rule verbatim; keep the pointer, drop
the restatement.
  </action>
  <verify>
`grep -ni 'pattern-file\|never interpolate' plugins/devflow/references/conventions.md` matches;
read the flow-hooks paragraph and confirm it is a pointer, not a contract restatement.
`python3 scripts/check-links.py` → 0 failures, reference count not lower than before.
`python3 scripts/validate-plugin.py` → exit 0, 13 Claude agents, 22 skills.
  </verify>
  <falsify>
`git show HEAD:plugins/devflow/references/conventions.md | grep -ci 'never interpolate'` must print 0.
Then confirm check-links grades these files: point a link in one of them at a nonexistent target,
run it, confirm non-zero failures, restore, confirm 0.
  </falsify>
  <done>SKILL.md is a pointer; conventions.md carries the data-not-shell rule and drops the duplicated reporting sentence; links green and shown to be graded.</done>
</task>

</tasks>
