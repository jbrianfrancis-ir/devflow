<!-- .planning/quick/015-02-prober-and-atomic-writes.md -->
---
phase: quick-015
plan: 02
wave: 1
depends_on: []
files_modified:
  - plugins/devflow/agents/flow-prober.md
  - plugins/devflow/scripts/flow-agent.py
  - plugins/devflow/references/hosts.md
  - scripts/validate-plugin.py
  - docs/providers.md
autonomous: true
requirements: [R4, R7]
must_haves:
  truths:
    - "a flow-prober role exists that tests one stated assumption by building a throwaway project outside the repo, reports command + exit code + verbatim output, and deletes it"
    - "flow-prober's contract requires changing exactly one variable per probe"
    - "an assumption that cannot be probed is recorded as unverified rather than pinned"
    - "hosts.md states that write roles emit to .tmp and atomically rename, so a partial file is never observable"
    - "hosts.md states that a phase directory is never diffed or audited while its write role is running"
    - "validate-plugin.py passes with the new role registered in the agent files, the bridge role sets, and hosts.md's prose lists"
  artifacts:
    - plugins/devflow/agents/flow-prober.md
  key_links:
    - "flow-agent.py's role sets contain prober and match the agents/ directory"
    - "hosts.md's Read-only roles / Write roles prose lists match flow-agent.py exactly"
---

<objective>
R4: add a probe role so a toolchain assumption is tested before it becomes an ARCHITECTURE pin.
R7: make in-flight agent output unobservable rather than racy.
</objective>

<context>
- /home/brianf/Work/devflow/.planning/ARCHITECTURE.md  (law)
- /home/brianf/Work/devflow/plugins/devflow/references/hosts.md
- /home/brianf/Work/devflow/plugins/devflow/agents/flow-researcher.md  (closest sibling — match its shape and length)
- /home/brianf/Work/devflow/plugins/devflow/scripts/flow-agent.py  (READ_ONLY_ROLES / WRITE_ROLES, lines ~15-18)
- /home/brianf/Work/devflow/scripts/validate-plugin.py  (agent count at line ~85; role-set cross-check ~107-160)
- /home/brianf/Work/devflow/docs/providers.md

REGISTRATION IS VALIDATOR-ENFORCED — a new role is not one file. `validate-plugin.py` checks all
of: the agent-file count (`len(agents) != 12`), that `flow-agent.py`'s role sets equal the set of
agent filenames with the `flow-` prefix stripped, that no role appears in both sets, that a
READ_ONLY role's frontmatter declares no Write/Edit tools, and that hosts.md's "Read-only roles:"
and "Write roles:" prose lists match the bridge sets exactly. Miss one and the validator fails —
which is the point; let it grade you.

DECISION ALREADY MADE — implement it, do not re-litigate:
`prober` goes in **WRITE_ROLES**, not READ_ONLY_ROLES. The bridge maps READ_ONLY_ROLES to a
`read-only` sandbox (`build_command`, ~line 93), and a probe that cannot create files cannot
build a throwaway project — a "read-only" prober would be a role that cannot do its job while
its label claims otherwise, which is precisely the false-green naming this whole change set is
about. Its *contract* is what keeps it safe: never touch the repo, never commit, scratch dir
outside the repo, deleted on exit. Say that plainly in the agent file.
</context>

<tasks>

<task type="auto">
  <name>Task 1: write the flow-prober agent contract</name>
  <files>plugins/devflow/agents/flow-prober.md</files>
  <action>
Create the agent file, matching the house style of `agents/flow-researcher.md` — frontmatter
(`name`, `description`, `tools`, `model`) then terse contract prose. Keep it near
flow-researcher's length; this is a narrow role.

Frontmatter: `name: flow-prober`; a description in the established voice, one line, naming who
spawns it (`/flow-plan`); `tools: Read, Write, Edit, Bash, Grep, Glob`; `model: sonnet`.

Contract, stating the requirement's substance:
- Purpose: `flow-researcher` reads documentation; nothing in DevFlow runs anything. You are given
  ONE stated assumption and you test it by building the smallest throwaway project that could
  falsify it, running it, and reporting what actually happened.
- **Change one variable.** This is the load-bearing rule, so give it the weight of a rule and not
  a footnote: a probe that moves several things at once produces a confident wrong conclusion,
  which is worse than no probe because it arrives carrying evidence. The motivating case: a probe
  added an entitlement, ad-hoc signing, and a hosted test target together and credited the
  entitlement; a later probe isolated it and the entitlement turned out not to be the cause — the
  wrong cause had already reached a plan and two commit messages. If testing the assumption needs
  more than one variable moved, run more than one probe, each isolating one.
- Scope: a scratch directory OUTSIDE the repo (use the system temp dir), deleted before you exit,
  whether the probe succeeded or failed. Never create, edit, or delete anything inside the repo;
  never commit; never install a package that ARCHITECTURE.md does not pin — an assumption that
  needs an unpinned package is unprobeable here, which is a reportable result.
- Report: the exact command, its exit code, and verbatim output (trimmed to the relevant lines,
  and say when you trimmed). A conclusion is one line and must be traceable to that output.
- **Fail-closed**: an assumption you could not probe — missing toolchain, needs credentials,
  needs hardware, would take longer than a few minutes — is reported as **unverified**, never as
  confirmed and never silently dropped. Per conventions.md's three-outcome rule, "could not
  check" is its own outcome. State that an unverified assumption must be recorded as unverified
  rather than pinned in ARCHITECTURE.md.
- Never echo credential material; reference env vars by name only.
  </action>
  <verify>
`head -8 plugins/devflow/agents/flow-prober.md` shows the four frontmatter keys with
`name: flow-prober`; `grep -ci 'one variable' plugins/devflow/agents/flow-prober.md` >= 1;
`grep -ci 'unverified' plugins/devflow/agents/flow-prober.md` >= 1.
`python3 scripts/validate-plugin.py` will now FAIL on the agent count and the role-set mismatch —
that is expected at this point and task 2 fixes it. Record the exact validator error text in your
SUMMARY as evidence the registration checks are live, then proceed. Do not "fix" it by deleting
the file.
  </verify>
  <falsify>
The file is new, so a grep for its own content proves only that you wrote it. Instead falsify the
validator's grip: confirm `python3 scripts/validate-plugin.py` exits NON-ZERO right now with this
file present and unregistered, and quote the message. If the validator passes with an unregistered
13th agent, the registration cross-check is not live and task 2's verify will be vacuous — say so
in your SUMMARY and treat task 2's checks as unproven.
  </falsify>
  <done>Agent file exists with correct frontmatter and states the one-variable rule, the outside-the-repo scratch rule, and the unverified-not-pinned rule; the validator was shown to reject it as unregistered.</done>
</task>

<task type="auto">
  <name>Task 2: register prober in the bridge, the validator, and hosts.md</name>
  <files>plugins/devflow/scripts/flow-agent.py, scripts/validate-plugin.py, plugins/devflow/references/hosts.md</files>
  <action>
Three edits that must land together or the validator stays red:

- `flow-agent.py`: add `"prober"` to `WRITE_ROLES` (see the decision in this plan's context —
  it needs `workspace-write` to build a scratch project). Keep the literal regex-parseable:
  ARCHITECTURE.md notes validate-plugin.py parses these sets by regex, so keep the existing
  brace-and-comma formatting; do not reformat to a different structure.
- `scripts/validate-plugin.py`: change the expected agent count from 12 to 13, in both the
  condition and the message text so they cannot disagree.
- `hosts.md` (~line 52): add `prober` to the **Write roles** prose list. The validator compares
  this list to the bridge set exactly — the prose wraps across lines, so keep it parseable by the
  existing regex and re-read the surrounding sentence after editing.
  </action>
  <verify>
`python3 scripts/validate-plugin.py` → exit 0 and prints "13 Claude agents".
`python3 -m unittest discover -s tests 2>&1 | tail -3` → OK, 0 failures, 0 errors.
`grep -n 'prober' plugins/devflow/scripts/flow-agent.py plugins/devflow/references/hosts.md scripts/validate-plugin.py` shows the role in the bridge and hosts.md.
  </verify>
  <falsify>
Prove each of the three registration points is independently load-bearing, one at a time,
restoring after each: (1) remove `"prober"` from WRITE_ROLES → validator must fail on the
role-set mismatch; (2) set the expected count back to 12 → validator must fail on the count;
(3) remove `prober` from hosts.md's Write roles list → validator must fail on the hosts.md
cross-check. Record all three error messages in your SUMMARY. Any one that does NOT fail is a
registration check that is not actually enforcing — report it as such rather than assuming.
  </falsify>
  <done>Validator green at 13 agents, full test suite OK, and all three registration points individually shown to fail when broken.</done>
</task>

<task type="auto">
  <name>Task 3: R7 — atomic writes and the no-reads-mid-write rule</name>
  <files>plugins/devflow/references/hosts.md</files>
  <action>
R7: four of thirteen reported issues in the source phase were stale — filed against a snapshot
taken while the planner was mid-write, describing defects already fixed. A watcher polling for a
"stable" directory reported stable during a write lull, twice. The orchestrator has no way to
know an agent is partway through a multi-file write.

Add a short subsection to hosts.md near the write-role material, stating both halves:

- **Write roles emit to `.tmp` and atomically rename.** A role producing a file writes
  `<name>.tmp` and renames it into place, so a reader sees either the previous complete file or
  the new one, never a mixture. Say it applies per file, so a multi-file write is still a
  sequence of atomic single-file appearances — which is why the second rule is also needed and
  the first does not subsume it.
- **Never diff or audit a phase directory while its write role is running.** Wait for completion.
  State the trap in one line, since it is the part that reads as safe and is not: *a quiet
  directory is not a finished one* — polling for stability cannot distinguish a finished write
  from a pause between two files, and it reported stable mid-write twice.

State this once, here, for all write roles — per ARCHITECTURE's "docs are pointers, never copies",
do NOT copy it into each agent file. If hosts.md already names the write roles (it does, ~line 52),
place this so it plainly governs that set.

Do not touch the "Read-only roles:" / "Write roles:" list content itself in this task — task 2
owns it and the validator compares it byte-wise against the bridge.
  </action>
  <verify>
`grep -n '\.tmp' plugins/devflow/references/hosts.md` matches, and
`grep -ni 'quiet directory' plugins/devflow/references/hosts.md` matches;
read the section to confirm both rules are stated and that it sits with the write-role material.
`python3 scripts/validate-plugin.py` → exit 0, "13 Claude agents" (hosts.md role lists still parse).
`python3 scripts/check-links.py` → 0 failures, reference count >= 225.
  </verify>
  <falsify>
`git show HEAD:plugins/devflow/references/hosts.md | grep -c '\.tmp'` must print 0. If it does not,
substitute a distinctive phrase you wrote and report the substitution.
Then prove the validator still grades hosts.md after your edit — temporarily delete `prober` from
its Write roles list, confirm the validator fails, and restore. An edit that accidentally broke
the prose regex would make that list silently unchecked, which is this PR's own defect class.
  </falsify>
  <done>hosts.md states atomic .tmp+rename and the no-mid-write-read rule once, governing all write roles; the role-list cross-check still fires.</done>
</task>

<task type="auto">
  <name>Task 4: document the probe role for users</name>
  <files>docs/providers.md</files>
  <action>
`docs/providers.md` is public prose describing how roles are dispatched. Add `flow-prober` to
whatever enumeration of roles it carries, in the file's existing voice and format — one entry,
saying what it does (tests one stated assumption with a throwaway build, outside the repo) and
when it runs (`/flow-plan`, for an assumption headed for an ARCHITECTURE.md pin).

If the file describes the read-only/write split, note prober is a write role because it builds a
scratch project, and that this is about sandbox access, not about touching the repo — its contract
forbids that. Keep it to two or three sentences.

"Docs are pointers, never copies": link to the agent file or reference rather than restating its
contract. Read the file first and match what is actually there — do not invent a section.
  </action>
  <verify>
`grep -n 'prober' docs/providers.md` matches;
`python3 scripts/check-links.py` → 0 failures, reference count >= 225 (any link you added resolves).
Read the surrounding section to confirm the entry matches the file's existing format rather than
sitting in a new ad-hoc block.
  </verify>
  <falsify>
`git show HEAD:docs/providers.md | grep -c prober` must print 0.
Then prove check-links.py would catch a bad link from this file: temporarily change a link you
added (or an existing one in the section) to a nonexistent target, run check-links.py, confirm it
reports a failure and the count is non-zero, then restore and confirm 0 failures. If it does not
catch it, the link guard does not cover this file — report that in your SUMMARY.
  </falsify>
  <done>providers.md lists flow-prober in its existing format; check-links green and shown to catch a deliberately broken link from this file.</done>
</task>

</tasks>
