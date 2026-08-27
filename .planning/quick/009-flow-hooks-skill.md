<!-- .planning/quick/009-flow-hooks-skill.md — ad-hoc mini-plan (flow-quick), not tied to ROADMAP. -->
---
phase: quick-009
plan: 01
wave: 1
depends_on: []
files_modified:
  - plugins/devflow/templates/hooks/base-branch-guard.py
  - plugins/devflow/templates/hooks/protected-paths-guard.py
  - plugins/devflow/templates/hooks/secret-scan-guard.py
  - plugins/devflow/skills/flow-hooks/SKILL.md
  - tests/test_flow_hooks.py
  - plugins/devflow/.claude-plugin/plugin.json
  - plugins/devflow/.codex-plugin/plugin.json
  - .claude-plugin/marketplace.json
  - scripts/validate-plugin.py
  - README.md
  - docs/README.md
  - docs/hooks.md
autonomous: true
requirements: []
must_haves:
  truths:
    - "Running /flow-hooks in a project with .planning/ merges idempotent PreToolUse hook entries into .claude/settings.json without disturbing existing keys"
    - "A commit/push attempted on the project's configured base branch is blocked (exit 2, reason on stderr) by base-branch-guard.py"
    - "A commit/push whose diff matches the same secret pattern class as conventions.md's Secret scan section is blocked by secret-scan-guard.py"
    - "An Edit/Write targeting a path listed in protected_paths is blocked by protected-paths-guard.py unless the approval env var is set"
    - "Each guard fails open (exit 0) with a stderr warning, never a silent pass, when it cannot determine the answer (no git repo, unreadable config)"
  backstop_truths: []
  artifacts:
    - plugins/devflow/templates/hooks/base-branch-guard.py
    - plugins/devflow/templates/hooks/protected-paths-guard.py
    - plugins/devflow/templates/hooks/secret-scan-guard.py
    - plugins/devflow/skills/flow-hooks/SKILL.md
    - tests/test_flow_hooks.py
    - docs/hooks.md
  key_links:
    - "flow-hooks/SKILL.md copies templates/hooks/*.py into the target repo's .claude/hooks/ and wires them into .claude/settings.json"
    - "secret-scan-guard.py's embedded pattern is asserted equal to conventions.md's documented pattern by a test, so the two copies cannot drift silently"
    - "validate-plugin.py's skill count and the marketplace/plugin manifest versions are updated together, or CI fails"
---

<objective>
Add a `flow-hooks` skill that scaffolds three deterministic Claude Code hooks into a consuming
project's `.claude/settings.json`, hardening three of DevFlow's existing instruction-only hard
rules (never commit to base branch; secret-scan every commit/push; protected paths) so they hold
even if an agent ignores its written instructions.
</objective>

<context>
Verified against the live Claude Code hooks contract (code.claude.com/docs/en/hooks) this session:
PreToolUse hooks receive JSON on stdin (`tool_name`, `tool_input`, `cwd`, ...); exit 2 blocks with
stderr shown as the reason (cannot be overridden); exit 0 with no JSON output means "no decision,
normal flow continues." settings.json registers hooks under `hooks.PreToolUse[]`, each entry a
`{matcher, hooks: [{type: "command", command}]}` block.

Read: .planning/ARCHITECTURE.md (stdlib-only, no deployable surface, layout override),
plugins/devflow/references/conventions.md (Secret scan section — the regex to mirror; Plugin
self-bootstrap section — the JSON-merge precedent for .claude/settings.json), plugins/devflow/
skills/flow-design/SKILL.md (closest existing precedent: a skill that scaffolds constraints into
a consuming project), scripts/validate-plugin.py (hardcoded skill/agent counts to update),
README.md command table (~line 60-81), docs/README.md (index to extend).

Do NOT install these hooks into this repo's own .claude/settings.json — ship the skill and
templates only.
</context>

<tasks>
<task type="auto">
  <name>Task 1: Write the three hook scripts</name>
  <files>plugins/devflow/templates/hooks/base-branch-guard.py, plugins/devflow/templates/hooks/protected-paths-guard.py, plugins/devflow/templates/hooks/secret-scan-guard.py</files>
  <action>
  Stdlib Python 3 only (json, re, subprocess, os, sys — matching scripts/*.py conventions). Each
  script: read stdin JSON per the verified contract; on any internal error (git call fails,
  .planning/config.json missing/malformed, cwd not a git repo) print a clear warning to stderr and
  exit 0 — fail open, but loud, never a silent pass (conventions.md's fail-closed-guards principle
  applied honestly: this is a best-effort backstop layered on top of the still-primary
  agent-instruction controls, not the sole safety net, so blocking on infra noise would be worse
  than the gap it closes).

  base-branch-guard.py: matcher target is Bash. Parse `tool_input.command`; if it does not match
  `\bgit\s+(commit|push)\b`, exit 0. Else resolve the base branch — read `git.base` from
  `.planning/config.json` under `cwd`; if absent, fall back to checking the current branch against
  {"main", "master"}. Get current branch via `git -C <cwd> branch --show-current`. If it equals the
  base branch, print `Blocked: direct commit/push to base branch '<base>' — use a flow/<slug>
  feature branch.` to stderr and exit 2. Else exit 0.

  protected-paths-guard.py: matcher target is Edit|Write. Read `tool_input.file_path` (support both
  since Edit and Write share this field). Read `protected_paths` (glob list) from
  `.planning/config.json` under `cwd`; empty/missing list → exit 0. If the path matches any glob
  (fnmatch), check env var `DEVFLOW_PROTECTED_PATH_OK`; if unset, print `Blocked: <path> is a
  protected path (<matched glob>) — set DEVFLOW_PROTECTED_PATH_OK=1 after human review to proceed.`
  to stderr and exit 2. Else exit 0.

  secret-scan-guard.py: matcher target is Bash. Parse `tool_input.command`; if not a git
  commit/push, exit 0. For commit: `git -C <cwd> diff --cached -U0`. For push: resolve base as in
  base-branch-guard.py, then `git -C <cwd> diff <base>...HEAD -U0`. Apply the exact regex
  alternation from conventions.md's "Secret scan (fail-closed)" section (copy verbatim into a
  Python constant, comment noting it must stay in sync with that section — a test in Task 3 checks
  this) to added lines only (lines starting `+`, excluding the `+++` diff header), plus the
  added-line-in-`.env*`/`*.pem`/`*.pfx`/`*.key`/`id_rsa*` unconditional-hit rule. On a hit, print
  `Blocked: possible secret in <file> (pattern: <class>) — remove/rotate before committing.` (never
  echo the matched value) to stderr and exit 2. Else exit 0.
  </action>
  <verify>Each script runs standalone: `echo '{"tool_input":{"command":"git commit -m x"},"cwd":"/tmp/x"}' | python3 plugins/devflow/templates/hooks/base-branch-guard.py; echo $?` behaves per the logic above in a scratch git repo set up by hand.</verify>
  <done>All three scripts exist, are executable (`chmod +x`), exit 0 on the safe case and 2 with a stderr reason on the blocked case, and never raise an uncaught exception (wrap the body in try/except that falls through to the fail-open path).</done>
</task>

<task type="auto">
  <name>Task 2: Write the flow-hooks skill</name>
  <files>plugins/devflow/skills/flow-hooks/SKILL.md</files>
  <action>
  Follow the shared skill header (host setup, agent provider block) used by every other skill —
  copy the boilerplate from flow-design/SKILL.md verbatim. Then: no `.planning/` required to run,
  but read `.planning/config.json` when present for `git.base` and `protected_paths`, and
  `.planning/STATE.md` first if present (context rule, all skills).

  Default: install all three guards. Accept an optional selection (host question mechanism, or a
  plain arg like `--only base,secret,paths`) to install a subset.

  For each selected guard: copy `{devflow_root}/templates/hooks/<name>.py` to
  `.claude/hooks/<name>.py` in the target repo (create the dir; `chmod +x`). Then merge into
  `.claude/settings.json` (read existing JSON or start from `{}`; never overwrite unrelated keys —
  same discipline as the Plugin self-bootstrap merge in conventions.md): ensure
  `hooks.PreToolUse` is a list, and append one `{"matcher": "<Bash|Edit|Write>", "hooks": [{"type":
  "command", "command": "python3 \"${CLAUDE_PROJECT_DIR}/.claude/hooks/<name>.py\""}]}` block per
  guard — idempotent: skip a guard whose command path already appears anywhere in
  `hooks.PreToolUse` rather than appending a duplicate entry.

  Print a summary of what was installed/skipped and remind the user to commit
  `.claude/hooks/` and `.claude/settings.json` (these are the target repo's own files, not
  DevFlow's — do not commit on the user's behalf here; this skill only writes files).
  </action>
  <verify>Manual dry run against a scratch project: run twice, confirm the second run reports "already installed" for each guard rather than duplicating entries.</verify>
  <done>plugins/devflow/skills/flow-hooks/SKILL.md exists, follows the same frontmatter/header shape as every other skill, and its logic matches Task 1's script contracts exactly (matcher, command form, config fields read).</done>
</task>

<task type="auto">
  <name>Task 3: Tests</name>
  <files>tests/test_flow_hooks.py</files>
  <action>
  For each script, drive it via `subprocess.run([sys.executable, script_path], input=json.dumps(payload), capture_output=True, text=True)` against a `tempfile.TemporaryDirectory` git fixture (`git init`, set a branch, write `.planning/config.json`, make a commit or stage a diff as needed). Cover: base-branch-guard blocks on base branch / allows on a feature branch / allows non-git commands; protected-paths-guard blocks a matching path without the env var, allows with it set, allows a non-matching path; secret-scan-guard blocks a staged diff containing a matching secret pattern, allows a clean diff, allows non-git commands. Also add one static test that extracts the regex from conventions.md's "Secret scan (fail-closed)" section (read the file, regex out the fenced pattern block) and asserts it is byte-identical to the constant embedded in secret-scan-guard.py, so the two copies cannot drift silently.
  </action>
  <verify>`python3 -m unittest tests.test_flow_hooks -v` — all pass.</verify>
  <done>tests/test_flow_hooks.py exists and passes; the conventions.md-vs-script pattern-drift test is present and passing.</done>
</task>

<task type="auto">
  <name>Task 4: Manifests, validator, docs, README</name>
  <files>plugins/devflow/.claude-plugin/plugin.json, plugins/devflow/.codex-plugin/plugin.json, .claude-plugin/marketplace.json, scripts/validate-plugin.py, README.md, docs/README.md, docs/hooks.md</files>
  <action>
  Bump version 0.16.0 → 0.17.0 in all three manifest files (Claude plugin, Codex plugin, root
  marketplace — validate-plugin.py checks these match). In scripts/validate-plugin.py, update the
  hardcoded `if len(skills) != 20` to `21` (new flow-hooks skill; agent count of 11 is unchanged —
  flow-hooks has no dedicated subagent). Add one row to README's command table (~line 60-81),
  category `guardrails`: `| guardrails | /flow-hooks | Scaffold deterministic base-branch,
  protected-paths, and secret-scan hooks into .claude/settings.json |`. Write docs/hooks.md (follow
  the existing docs/ page style — see docs/autonomy.md or docs/review.md: summarize, link to
  conventions.md as source of truth for the underlying rules, don't restate the regex or JSON
  schema in full) and add it to docs/README.md's index under "Working the loop".
  </action>
  <verify>`python3 scripts/validate-plugin.py && python3 -m unittest discover -s tests -v && python3 scripts/check-links.py` — all exit 0 (the full `## Smoke` command from ARCHITECTURE.md).</verify>
  <done>All three manifests agree on 0.17.0; validate-plugin.py passes with 21 skills; README/docs/README.md link-check clean; README stays ≤110 lines / ≤14KB (SC-01 from the completed docs-restructure phase — don't regress it).</done>
</task>
</tasks>
</content>
