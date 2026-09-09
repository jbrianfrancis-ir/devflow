<!-- .planning/quick/015-01-hooks-and-forbidden-regex.md -->
---
phase: quick-015
plan: 01
wave: 1
depends_on: []
files_modified:
  - plugins/devflow/templates/hooks/secret-scan-guard.py
  - plugins/devflow/skills/flow-hooks/SKILL.md
  - plugins/devflow/references/conventions.md
  - plugins/devflow/templates/architecture.md
  - tests/test_flow_hooks.py
autonomous: true
requirements: [GUARD-FAILOPEN, R8]
must_haves:
  truths:
    - "secret-scan-guard.py blocks a staged secret when git is configured with diff.mnemonicPrefix=true"
    - "secret-scan-guard.py blocks a staged secret when git is configured with diff.noprefix=true"
    - "a diff the guard cannot parse into file chunks is reported as could-not-check, never as clean"
    - "ARCHITECTURE.md's Forbidden entries may carry an optional regex, and the documented scans apply those patterns across tracked files including .planning/"
    - "a forbidden-pattern hit reports file, line and pattern class, never the matched value"
  artifacts:
    - plugins/devflow/templates/hooks/secret-scan-guard.py
    - tests/test_flow_hooks.py
  key_links:
    - "tests/test_flow_hooks.py exercises the guard under mnemonicPrefix and noprefix"
    - "templates/architecture.md's Forbidden section documents the regex column that conventions.md's scan consumes"
---

<objective>
Close the live fail-open in secret-scan-guard.py (a common git config silently disables it),
then land R8: project-specific Forbidden entries become machine-checkable by the same
fail-closed path as a credential.
</objective>

<context>
- /home/brianf/Work/devflow/.planning/ARCHITECTURE.md  (law: stdlib-only Python, no dependencies, docs are pointers)
- /home/brianf/Work/devflow/plugins/devflow/references/conventions.md  (## Secret scan, ## Fail-closed guards)
- /home/brianf/Work/devflow/plugins/devflow/templates/hooks/secret-scan-guard.py
- /home/brianf/Work/devflow/plugins/devflow/templates/hooks/_hook_common.py
- /home/brianf/Work/devflow/plugins/devflow/skills/flow-hooks/SKILL.md
- /home/brianf/Work/devflow/plugins/devflow/templates/architecture.md
- /home/brianf/Work/devflow/tests/test_flow_hooks.py

DIAGNOSIS, already root-caused — do not re-derive it:
`git config diff.mnemonicPrefix true` (set globally on this machine) makes git emit
`diff --git c/file w/file` instead of `a/`/`b/`. secret-scan-guard.py's
`DIFF_GIT_HEADER_RE = re.compile(r"^diff --git a/.* b/(.*)$")` matches nothing, so
`iter_file_chunks` yields ZERO chunks, `scan` returns None, and the guard exits 0 (allow)
with no stderr warning. `diff.noprefix=true` (emits `diff --git file file`) breaks it the
same way. Reproduced outside the test harness: a staged `api_key = "…"` passes clean.
This is why tests/test_flow_hooks.py's 5 SecretScanGuardTests fail on this machine and on main.
</context>

<tasks>

<task type="auto">
  <name>Task 1: make the guard's diff parsing independent of the user's prefix config</name>
  <files>plugins/devflow/templates/hooks/secret-scan-guard.py</files>
  <action>
Fix the cause, not the symptom. Two changes, both needed:

(a) FORCE THE PREFIXES. Every `git diff` invocation in this file (there are three: the
`git diff HEAD -U0` in `diff_for`, its `--cached` fallback, and the `{base}...HEAD` push
diff) must pin the prefixes so user config cannot change the output shape. Use git's own
config override on the command line — `git -c diff.mnemonicPrefix=false -c diff.noprefix=false
-C <cwd> diff --src-prefix=a/ --dst-prefix=b/ …`. Belt and braces is deliberate here: the
`-c` overrides neutralise the config, and the explicit `--src-prefix`/`--dst-prefix` make the
output shape independent of any future default change. Add `--no-ext-diff` too — an external
diff driver replaces the output wholesale, which is the same defeat by another route.
Factor the shared argument list into one module-level constant so a fourth call site cannot
be added without it.

(b) FAIL CLOSED ON AN UNPARSEABLE DIFF. This is the part that makes the bug non-recurring.
A non-empty diff that yields zero file chunks means the guard does not understand what git
gave it — that is `conventions.md`'s "could not check", and it must NOT read as clean. In
`scan` (or its caller), when `diff_text` is non-empty and `iter_file_chunks` produced no
chunks, return a distinct could-not-check result. `main` must translate that into a BLOCK
(exit 2) with a stderr message saying the diff could not be parsed and naming what to do,
NOT a warn-and-allow.

Note the tension with the module docstring's stated fail-open posture and resolve it in the
docstring: the existing fail-open cases are *environmental* (no git repo, no HEAD, git call
failed) — the guard could not run at all, and the primary agent-instruction control still
stands. A diff that git produced and this parser could not read is different in kind: the
guard ran, examined the outgoing change, and understood none of it. Update the docstring so
it states both rules; do not leave it claiming the file always fails open.

Keep it stdlib-only. Do not add a dependency, and do not restructure the file beyond this.
  </action>
  <verify>
Build a throwaway git repo under the system temp dir (NOT inside this repo, NOT under
.planning/) with one commit, then stage a line built at runtime from concatenated fragments so
this repo's own secret scan never sees a literal — e.g. "api_key" + ' = "' + "abcd1234efgh5678" + '"'.
Run the guard with `{"tool_input":{"command":"git commit -m x"},"cwd":"<repo>"}` on stdin under
all three configs, asserting exit 2 and "Blocked" on stderr each time, and asserting the literal
secret value never appears in stderr:
  1. `git -C <repo> config diff.mnemonicPrefix true`
  2. `git -C <repo> config --unset diff.mnemonicPrefix; git -C <repo> config diff.noprefix true`
  3. neither set (plain defaults)
Then delete the throwaway repo.
  </verify>
  <falsify>
Establish the check distinguishes fixed from broken: `git stash` your change (or run the guard
from `git show HEAD:plugins/devflow/templates/hooks/secret-scan-guard.py` written to a temp path)
and run the SAME three-config check against the ORIGINAL file. Case 1 and case 2 must exit 0
(the bug) and case 3 must exit 2. If the original already blocks all three, your reproduction is
wrong and the fix is unproven — stop and report that rather than claiming a fix. Record the
before/after exit codes for all three configs in your SUMMARY.
  </falsify>
  <done>Guard blocks under mnemonicPrefix, noprefix, and defaults; an unparseable non-empty diff exits 2; the original file was shown to fail cases 1 and 2.</done>
</task>

<task type="auto">
  <name>Task 2: regression tests for the prefix configs and the unparseable diff</name>
  <files>tests/test_flow_hooks.py</files>
  <action>
Add tests to `SecretScanGuardTests` so this cannot regress silently. Follow the file's existing
idiom exactly — `GitFixture`, `run_hook`, and the runtime-built fixture line the class already
uses so the test file is not itself a secret-scan hit.

- One test per prefix config: `diff.mnemonicPrefix=true` and `diff.noprefix=true`, each staging a
  secret-shaped line and asserting exit 2, "Blocked" in stderr, and the secret value NOT in stderr.
- One test that a non-empty diff the parser cannot chunk exits 2 rather than 0. Drive this through
  real git output if you can arrange it; if you cannot without mocking, assert it at the function
  level by calling the guard module's `scan` (import it the way the file already imports hook
  modules) with a hand-written non-empty diff string containing no recognisable `diff --git`
  header, and assert it does not return None.

The 5 existing failures must now pass — they were correct all along, and the guard was wrong.
Do NOT weaken any existing assertion to make it pass.
  </action>
  <verify>
`python3 -m unittest tests.test_flow_hooks -v 2>&1 | tail -5` reports OK with 0 failures and
0 errors, and the run includes MORE tests than before your change. Capture both counts:
`git stash && python3 -m unittest tests.test_flow_hooks 2>&1 | tail -3` for the before number,
then restore. Record before/after test counts and failure counts in your SUMMARY.
  </verify>
  <falsify>
Prove the new tests actually grade the guard rather than passing vacuously: temporarily revert
ONE of the two prefix overrides you added in task 1 (drop `-c diff.mnemonicPrefix=false` and the
`--src-prefix`/`--dst-prefix` pair) and re-run `python3 -m unittest tests.test_flow_hooks`.
The mnemonicPrefix test MUST fail. Restore the override and confirm OK. If the test still passes
with the fix removed, it is testing nothing — rewrite it and say so in your SUMMARY.
  </falsify>
  <done>Full test_flow_hooks suite is OK with 0 failures; new tests were shown to fail against the unfixed guard; no existing assertion weakened.</done>
</task>

<task type="auto">
  <name>Task 3: R8 — Forbidden entries carry an optional regex, enforced by the existing scans</name>
  <files>plugins/devflow/templates/architecture.md, plugins/devflow/references/conventions.md</files>
  <action>
R8: `ARCHITECTURE.md`'s **Forbidden** list is prose and nothing enforces it. A project that
forbade committing a signing team id had two committed and pushed, because the secret-scan
pattern does not match Apple Team IDs and would not match whatever the next project forbids.

In `templates/architecture.md`'s Forbidden section, document an OPTIONAL regex on an entry.
Pick one syntax and show it once — a trailing backticked regex on the bullet reads best, e.g.
a bullet ending `` — pattern: `\b[A-Z0-9]{10}\b` ``. State that the regex is optional (prose-only
entries stay valid and stay unenforced), that it is an ordinary extended-regex, and that it is
matched case-sensitively unless the author writes it otherwise. Keep the example generic — do
NOT put a real team id, key, or credential in the template.

In `conventions.md`'s `## Secret scan (fail-closed)` section, add a short subsection stating that
the pre-commit and pre-push scans ADDITIONALLY apply any regexes declared on ARCHITECTURE.md's
Forbidden entries, and that these run across tracked files including `.planning/` — the secret
scan's own scope is the diff, but a forbidden literal that reached `.planning/` in an earlier
commit is exactly the case this exists to catch. Reuse the existing reporting rule verbatim in
force: report file, line, and pattern class only, never the matched value; a hit is fail-closed
and only a human clears it. Say plainly that a Forbidden entry with no regex is not enforced —
an unenforced rule that reads as enforced is the defect this PR is about.

Respect "docs are pointers": the rule text lives in conventions.md, the syntax lives in the
architecture template, and neither restates the other beyond a pointer.
  </action>
  <verify>
`grep -n 'pattern:' plugins/devflow/templates/architecture.md` shows the regex syntax inside the
Forbidden section (confirm by reading the section, not the grep alone);
`grep -ni 'forbidden' plugins/devflow/references/conventions.md` returns a match inside the secret
scan section; `grep -ni 'never the matched value\|never echo the matched value' plugins/devflow/references/conventions.md`
still matches (reporting rule intact).
`python3 scripts/check-links.py` → 0 failures, reference count >= 225.
Confirm no credential-shaped literal entered either file: run this repo's own conventions.md
secret-scan pattern over `git diff -U0` for these two files and confirm no hit.
  </verify>
  <falsify>
Both greps use words that may already appear in these files. Establish they read your change:
`git show HEAD:plugins/devflow/templates/architecture.md | grep -c 'pattern:'` and
`git show HEAD:plugins/devflow/references/conventions.md | grep -ci forbidden`. If either is
already non-zero, that grep does not distinguish before from after — replace it with a grep for a
distinctive phrase you actually wrote, re-run, and report the substitution in your SUMMARY.
  </falsify>
  <done>Template documents the optional regex with a generic example; conventions.md states the scans apply them across tracked files including .planning/, with the existing never-echo reporting rule; both greps shown to distinguish before from after.</done>
</task>

<task type="auto">
  <name>Task 4: teach /flow-hooks to scaffold the forbidden-pattern check</name>
  <files>plugins/devflow/skills/flow-hooks/SKILL.md</files>
  <action>
`/flow-hooks` scaffolds the deterministic PreToolUse backstops. R8's acceptance is that a
project-specific forbidden literal is blocked at commit by the same fail-closed path as a
credential — so the secret-scan guard it scaffolds must also apply ARCHITECTURE.md's Forbidden
regexes.

Update the skill's description of the secret-scan guard to say it additionally reads
`.planning/ARCHITECTURE.md`'s Forbidden entries and applies any regex they declare, reporting
file/line/pattern class only. If the skill enumerates what each guard covers, extend that
enumeration rather than adding a parallel one.

Do NOT add a fourth guard or a new `--only` token for this — it is the same guard doing one more
check, and a separate guard would give a project two places to look when a commit is blocked.
State explicitly that a malformed or unreadable ARCHITECTURE.md makes this check "could not
check" — reported, never silently skipped, consistent with conventions.md's three-outcome rule.

Prose only. Do not implement the ARCHITECTURE.md parsing in this task — task 1's guard changes
are already committed and this task must not touch that file.
  </action>
  <verify>
`grep -ni 'forbidden' plugins/devflow/skills/flow-hooks/SKILL.md` matches;
`grep -c 'only' plugins/devflow/skills/flow-hooks/SKILL.md` — read the `--only` list and confirm
it still names exactly the three original tokens (base, secret, paths), no fourth added.
`python3 scripts/validate-plugin.py` → exit 0, "22 shared skills" (unchanged);
`python3 scripts/check-links.py` → 0 failures.
  </verify>
  <falsify>
`git show HEAD:plugins/devflow/skills/flow-hooks/SKILL.md | grep -ci forbidden` must print 0 —
if it does not, the grep is pre-polluted; substitute a distinctive phrase you wrote and report it.
Separately, confirm validate-plugin.py is actually grading this file: temporarily corrupt its
frontmatter `name:` value, run the validator, confirm it errors, and restore.
  </falsify>
  <done>Skill states the secret-scan guard applies Forbidden regexes and treats an unreadable ARCHITECTURE.md as could-not-check; the --only token list is unchanged; validator green.</done>
</task>

</tasks>
