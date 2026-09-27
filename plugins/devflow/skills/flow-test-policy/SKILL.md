---
name: flow-test-policy
description: >-
  Agent test-layer policy for DevFlow product work. Prefer integration/behavior
  as the feedback driver; thin units for pure logic/regression pins only; forbid
  coverage theater and classic unit-TDD as default. Use when planning, executing,
  verifying, or reviewing tests. Supports --provider native|claude|codex.
---

# flow-test-policy

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

**Agent provider**: accept `--provider native|claude|codex`. Resolve and dispatch every role in this run exactly as `{devflow_root}/references/hosts.md` specifies. The selected provider applies to all delegated roles unless this skill explicitly calls an external consultation engine. A missing or failed peer is fail-closed; report `FLOW: BLOCKED` with remediation and never fall back silently.

Read and obey `{devflow_root}/references/test-policy.md` in full.

When `/flow-plan`, `/flow-execute`, `/flow-verify`, or `/flow-pr` (tests lens) touch tests:

1. Name the **behavior/integration/Smoke** proof for each user-visible or boundary-crossing must_have.
2. Allow new unit files only with a one-line justification: `pure-logic` or `regression-pin: <bug/issue>`. Every new test class/describe carries a `protects:` reason from test-policy.md.
3. Reject or revise plans/diffs that add wrapper/DTO/glue units or post-hoc coverage suites.
4. Never treat "coverage % went up" as phase proof.
5. Reject new per-phase test folders or requirement-id test names; place tests by behaviour.
6. When the diff removes or replaces a feature, require its tests to be deleted in the same diff (optional one-line doc addendum with the last SHA). Never keep a test only because a phase doc cites it.

End status lines follow `{devflow_root}/references/autonomy.md`.
