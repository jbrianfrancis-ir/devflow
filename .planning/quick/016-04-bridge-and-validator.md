<!-- .planning/quick/016-04-bridge-and-validator.md -->
---
phase: quick-016
plan: 04
wave: 4
depends_on: []
files_modified:
  - plugins/devflow/scripts/flow-agent.py
  - scripts/validate-plugin.py
  - plugins/devflow/references/hosts.md
  - plugins/devflow/agents/flow-prober.md
  - tests/test_flow_agent.py
autonomous: true
requirements: [prober-boundary, validator-failopen]
must_haves:
  truths:
    - "the prober's scratch root is enforced on the claude path as well as the codex path, or every claim about it is scoped to the path that enforces it"
    - "the SCRATCH_ROLES validator check errors when its regex matches nothing, instead of reporting clean"
    - "the prober sandbox rooting has a test"
    - "hosts.md's .tmp rule does not claim to bind the prober, whose only outputs are throwaway and outside the repo"
  artifacts: [plugins/devflow/scripts/flow-agent.py, tests/test_flow_agent.py]
  key_links: ["hosts.md and flow-prober.md describe exactly the boundary flow-agent.py enforces"]
---

<objective>
The prober boundary is claimed absolutely and enforced on only half the provider matrix, and the
validator check that pins it fails open. Close both.
</objective>

<context>
- /home/brianf/Work/devflow/.planning/ARCHITECTURE.md — law. STDLIB ONLY.
- /home/brianf/Work/devflow/plugins/devflow/scripts/flow-agent.py — `build_command`, `SCRATCH_ROLES`, `main`.
- /home/brianf/Work/devflow/scripts/validate-plugin.py — the role-set parsing block (~line 108-145).
- /home/brianf/Work/devflow/tests/test_flow_agent.py — house style; note `DEVFLOW_SMOKE` gates one live-CLI test, so add offline tests only.

FINDING (security + architecture lenses, independently): the scratch-root boundary is enforced
only for `provider == "codex"`. That branch passes `--sandbox <access>` and `--cd <root>`. The
claude branch never uses `root` at all — no `--add-dir`, no directory argument — so isolation
there is only the process `cwd`, which does not constrain Bash tool calls using absolute paths.
Meanwhile hosts.md says "the bridge roots its sandbox at a scratch directory" and flow-prober.md
says "the repo is not writable to you at all". For host=codex, provider=claude, role=prober, that
guarantee never applied.

FINDING (architecture lens): the new SCRATCH_ROLES subset check fails OPEN. If the regex misses —
the set is reformatted, renamed, or a comment containing `}` moves inside it — `scratch_roles`
becomes the empty set, `stray` is empty, and the guard reports clean while checking nothing. Its
sibling READ_ONLY/WRITE parse cannot do this, because a missed match surfaces as a `roles !=
expected` mismatch.

FINDING (reuse lens): that same check copy-pastes the brace-literal regex and set comprehension
from the `for key in ("READ_ONLY_ROLES", "WRITE_ROLES")` loop three lines above.

FINDING (architecture, nit): hosts.md's "Write roles emit to `.tmp` and atomically rename. Every
one of the roles above producing a file…" now sweeps in `prober`, whose only files are throwaway
scratch outside the repo that no reader ever polls.
</context>

<tasks>

<task type="auto">
  <name>Task 1: enforce the scratch root on the claude path, or scope the claim</name>
  <files>plugins/devflow/scripts/flow-agent.py, plugins/devflow/references/hosts.md, plugins/devflow/agents/flow-prober.md</files>
  <action>
Prefer ENFORCEMENT over weakening the claim. On the claude branch of `build_command`, constrain
the peer to `root` the way that CLI supports it (`--add-dir <root>` alongside the working
directory, or the equivalent directory-scoping flag) so a scratch role cannot write into the
checkout by absolute path. Read what flags the invocation already uses and stay consistent.

If — and only if — the claude CLI offers no flag that actually constrains writes to a directory,
then do the honest thing instead: scope BOTH claims to the path that enforces them. hosts.md and
flow-prober.md must then say, in plain words, "codex peer: sandboxed at the scratch root; claude
peer: rooted there by cwd, with the contract holding the line" — the same honesty flow-prober.md
already applies to the natively-spawned case. Whichever branch you take, the prose and the code
must agree exactly; a guarantee stated more strongly than the code delivers is the defect this
whole branch exists to remove, and it has already bitten here once.

State in your SUMMARY which branch you took and the evidence for it (the flag you used, or what
you checked to conclude none exists).
  </action>
  <verify>
Import `build_command` and assert, for BOTH providers with `role="prober"` and a scratch workdir:
the argv constrains the peer to the scratch dir (name the flag), or — in the scoped-claim branch —
that hosts.md and flow-prober.md no longer contain an unqualified "not writable" / "sandboxed"
claim. Assert non-scratch roles (`executor`, `verifier`) are unchanged for both providers.
`python3 scripts/validate-plugin.py` → exit 0, 13 agents. `python3 scripts/check-links.py` → 0 failures.
  </verify>
  <falsify>
Whichever branch you took, break it and confirm detection: if you added a flag, remove it and
confirm your new assertion fails; if you scoped the claims, restore the absolute wording in
hosts.md and confirm your prose assertion fails. A check that passes either way is not a check.
  </falsify>
  <done>Code and prose agree on exactly what is enforced for each provider, non-scratch roles unchanged, and the check was shown to fail when the fix is removed.</done>
</task>

<task type="auto">
  <name>Task 2: the SCRATCH_ROLES check must not fail open</name>
  <files>scripts/validate-plugin.py</files>
  <action>
Fold `SCRATCH_ROLES` into the existing `for key in ("READ_ONLY_ROLES", "WRITE_ROLES")` loop's key
tuple rather than keeping the copy-pasted regex and comprehension, so all three sets are parsed
one way.

Then make a missed match an ERROR, not an empty set: if `SCRATCH_ROLES` is absent from
`flow-agent.py` entirely, or its literal does not parse, `err(...)` saying so. Keep the existing
subset assertion (SCRATCH_ROLES ⊆ WRITE_ROLES). Note in a comment why this one needs the explicit
error while the other two do not — their misses surface as a `roles != expected` mismatch, this
one's does not, and a guard that reports clean while checking nothing is the failure mode this
repo's conventions call out by name.
  </action>
  <verify>
`python3 scripts/validate-plugin.py` → exit 0, "13 Claude agents".
Then three mutations of `plugins/devflow/scripts/flow-agent.py`, restoring after each, each of
which must make the validator exit non-zero with a message naming SCRATCH_ROLES:
(1) rename the set to `SCRATCH_ROLES_X`; (2) reformat the literal so the brace regex cannot match
(e.g. put a `}`-containing comment inside it); (3) remove `prober` from WRITE_ROLES while leaving
it in SCRATCH_ROLES.
Record all three messages.
  </verify>
  <falsify>
Mutations (1) and (2) ARE the falsification — before this task they left the validator green,
which is the finding. Run both against the PRE-fix validator (`git show HEAD:scripts/validate-plugin.py`
to a temp path) and confirm it exits 0 on each, then against yours and confirm non-zero. Record
both sides. If the pre-fix validator already fails them, the finding is wrong; say so.
  </falsify>
  <done>All three sets parsed by one loop; a missing or unparseable SCRATCH_ROLES is an error; pre-fix validator shown to pass mutations (1) and (2) that the fixed one rejects.</done>
</task>

<task type="auto">
  <name>Task 3: test the sandbox rooting, and stop the .tmp rule over-claiming</name>
  <files>tests/test_flow_agent.py, plugins/devflow/references/hosts.md</files>
  <action>
The prober sandbox rooting shipped with zero tests while its own comment claims the boundary is
"a property of the sandbox rather than a promise in its prompt". Add offline tests (no live CLI —
`DEVFLOW_SMOKE` gates that and must stay gated) in the file's existing idiom:
- `build_command(..., role="prober", workdir=scratch)` constrains the peer to the scratch dir for
  each provider, exactly as task 1 implemented it, and never passes the repo path as the root.
- `prober` is in `WRITE_ROLES` and in `SCRATCH_ROLES`.
- a non-scratch write role (`executor`) still gets the repo as its root, and a read-only role
  (`verifier`) still gets the read-only access class.

hosts.md: scope the `.tmp`/atomic-rename sentence so it binds the roles that write `.planning/`
artifacts, not the prober — whose only outputs are throwaway, outside the repo, and never polled
by a reader. Do not touch the "Read-only roles:/Write roles:" lists themselves; the validator
compares them byte-wise against the bridge.
  </action>
  <verify>
`python3 -m unittest tests.test_flow_agent -v 2>&1 | tail -5` → OK, 0 failures, count higher than
before. Full suite `python3 -m unittest discover -s tests 2>&1 | tail -3` → OK, 0 failures.
`python3 scripts/validate-plugin.py` → exit 0, 13 agents (hosts.md role lists still parse).
  </verify>
  <falsify>
Remove the scratch-root handling from `build_command` (make it always use `repo`) and confirm the
new tests fail, naming which. Restore.
Then delete `prober` from hosts.md's Write roles list and confirm the validator still fails — your
`.tmp` sentence edit must not have broken that prose parse. Restore and confirm green.
  </falsify>
  <done>Sandbox rooting has tests that fail when it is removed; the .tmp rule no longer claims the prober; the hosts.md role-list cross-check still fires.</done>
</task>

</tasks>
