"""Tests for flow-split-plan.py.

Fixtures are hand-written literal strings shaped like templates/plan.md (HTML path
comment on line 1, real frontmatter, `<tasks>`/`<task>` elements) — never built with the
tool's own `format_frontmatter`, so the serializer under test is never compared only
against itself. Every fixture lives under the system temp dir, never inside this repo.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/devflow/scripts/flow-split-plan.py"


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout


class TempPhase:
    """A throwaway phase dir under the system temp dir (never inside this repo, never
    under .planning/ — a stray plan file there would be read as real project state)."""

    def __init__(self, phase_name="01-demo-phase"):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.phase_dir = self.root / phase_name
        self.phase_dir.mkdir()

    def write(self, filename: str, text: str) -> None:
        (self.phase_dir / filename).write_text(text, encoding="utf-8")

    def read(self, filename: str) -> str:
        return (self.phase_dir / filename).read_text(encoding="utf-8")

    def snapshot(self) -> dict:
        return {p.name: p.read_text(encoding="utf-8") for p in sorted(self.phase_dir.iterdir())
                if p.is_file()}

    def cleanup(self) -> None:
        self.tempdir.cleanup()


def must_haves_union(snapshot: dict) -> set:
    """Every must_haves.{truths,artifacts,key_links} quoted/unquoted entry across a
    snapshot, used only as a no-loss cross-check — never the sole assertion a test makes,
    since a union check alone can't tell a real split from one that moved nothing."""
    import re
    entries = set()
    list_item = re.compile(r'^\s*-\s*"?(.*?)"?\s*$')
    for text in snapshot.values():
        in_mh = False
        for line in text.splitlines():
            if line.strip() in ("truths:", "artifacts:", "key_links:"):
                in_mh = True
                continue
            if in_mh:
                m = list_item.match(line)
                if m and line.startswith(("    -", "  -")):
                    entries.add(m.group(1))
                elif line.strip() and not line.startswith(" "):
                    in_mh = False
    return entries


# --- Fixture 1: a real four-plan phase (HTML comment, user_setup, a prose reference to a
# plan that will shift, a disjoint 3-task source plan to split). ------------------------

PLAN_01_01 = """<!-- .planning/phases/01-demo-phase/01-01-PLAN.md -->
---
phase: 01-demo-phase
plan: 01
wave: 1
depends_on: []
files_modified:
  - src/a.py
autonomous: true
requirements: [REQ-01]
must_haves:
  truths:
    - "a exists"
  artifacts:
    - src/a.py
  key_links: []
---

<objective>First plan. See 01-04 for the followup.</objective>

<context>none</context>

<tasks>

<task type="auto">
  <name>Task 1: build a</name>
  <files>src/a.py</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

</tasks>
"""

PLAN_01_02_SRC = """<!-- .planning/phases/01-demo-phase/01-02-PLAN.md -->
---
phase: 01-demo-phase
plan: 02
wave: 2
depends_on: [01-01]
files_modified:
  - src/b.py
  - src/c.py
  - src/d.py
autonomous: true
requirements: [REQ-01]
user_setup: "create an S3 bucket named demo-bucket before running"
must_haves:
  truths:
    - "src/b.py exists and passes its tests"
    - "src/c.py exists and passes its tests"
    - "src/d.py exists and passes its tests"
  artifacts:
    - src/b.py
    - src/c.py
    - src/d.py
  key_links:
    - "src/c.py calls src/d.py"
---

<objective>Second plan, over cap, needs a split.</objective>

<context>depends on 01-01</context>

<tasks>

<task type="auto">
  <name>Task 1: build b</name>
  <files>src/b.py</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

<task type="auto">
  <name>Task 2: build c</name>
  <files>src/c.py</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

<task type="auto">
  <name>Task 3: build d</name>
  <files>src/d.py</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

</tasks>
"""

PLAN_01_03 = """<!-- .planning/phases/01-demo-phase/01-03-PLAN.md -->
---
phase: 01-demo-phase
plan: 03
wave: 3
depends_on: [01-02]
files_modified:
  - src/e.py
autonomous: true
requirements: [REQ-01]
must_haves:
  truths:
    - "e exists"
  artifacts:
    - src/e.py
  key_links: []
---

<objective>Third plan, depends on second.</objective>

<context>depends on 01-02</context>

<tasks>

<task type="auto">
  <name>Task 1: build e</name>
  <files>src/e.py</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

</tasks>
"""

PLAN_01_04 = """<!-- .planning/phases/01-demo-phase/01-04-PLAN.md -->
---
phase: 01-demo-phase
plan: 04
wave: 4
depends_on: [01-03]
files_modified:
  - src/f.py
autonomous: true
requirements: [REQ-01]
must_haves:
  truths:
    - "f exists"
  artifacts:
    - src/f.py
  key_links: []
---

<objective>Fourth plan, referenced from 01-01.</objective>

<context>depends on 01-03</context>

<tasks>

<task type="auto">
  <name>Task 1: build f</name>
  <files>src/f.py</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

</tasks>
"""

# Pinned: exactly what the new plan (01-03, disjoint split of 01-02 --after 1) must
# produce. A drifting serializer cannot round-trip this and stay green.
EXPECTED_NEW_PLAN_01_03 = (
    '<!-- .planning/phases/01-demo-phase/01-03-PLAN.md -->\n---\n'
    'phase: 01-demo-phase\nplan: 03\nwave: 2\ndepends_on: [01-01]\n'
    'files_modified:\n  - src/c.py\n  - src/d.py\n'
    'autonomous: true\nrequirements: [REQ-01]\n'
    'must_haves:\n  truths:\n'
    '    - "src/c.py exists and passes its tests"\n'
    '    - "src/d.py exists and passes its tests"\n'
    '  artifacts:\n    - src/c.py\n    - src/d.py\n'
    '  key_links:\n    - "src/c.py calls src/d.py"\n'
    'user_setup: "create an S3 bucket named demo-bucket before running"\n---\n\n'
    '<objective>Second plan, over cap, needs a split.</objective>\n\n'
    '<context>depends on 01-01</context>\n\n<tasks>\n\n'
    '<task type="auto">\n  <name>Task 1: build c</name>\n  <files>src/c.py</files>\n'
    '  <action>do it</action>\n  <verify>true</verify>\n  <falsify>false</falsify>\n'
    '  <done>done</done>\n</task>\n\n'
    '<task type="auto">\n  <name>Task 2: build d</name>\n  <files>src/d.py</files>\n'
    '  <action>do it</action>\n  <verify>true</verify>\n  <falsify>false</falsify>\n'
    '  <done>done</done>\n</task>\n\n</tasks>\n'
)


def base_phase() -> TempPhase:
    fixture = TempPhase()
    fixture.write("01-01-PLAN.md", PLAN_01_01)
    fixture.write("01-02-PLAN.md", PLAN_01_02_SRC)
    fixture.write("01-03-PLAN.md", PLAN_01_03)
    fixture.write("01-04-PLAN.md", PLAN_01_04)
    return fixture


class BasePhaseSplitTests(unittest.TestCase):
    def setUp(self):
        self.fixture = base_phase()
        self.addCleanup(self.fixture.cleanup)
        self.before = self.fixture.snapshot()

    def test_preamble_preserved_on_both_outputs(self):
        result = run(str(self.fixture.phase_dir), "02", "--after", "1")
        self.assertEqual(0, result.returncode, result.stderr)
        src_text = self.fixture.read("01-02-PLAN.md")
        new_text = self.fixture.read("01-03-PLAN.md")
        self.assertTrue(src_text.startswith(
            "<!-- .planning/phases/01-demo-phase/01-02-PLAN.md -->\n"))
        self.assertTrue(new_text.startswith(
            "<!-- .planning/phases/01-demo-phase/01-03-PLAN.md -->\n"))

    def test_user_setup_survives_on_source(self):
        result = run(str(self.fixture.phase_dir), "02", "--after", "1")
        self.assertEqual(0, result.returncode, result.stderr)
        src_text = self.fixture.read("01-02-PLAN.md")
        self.assertIn(
            'user_setup: "create an S3 bucket named demo-bucket before running"', src_text)

    def test_new_plan_frontmatter_matches_pinned_literal(self):
        result = run(str(self.fixture.phase_dir), "02", "--after", "1")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(EXPECTED_NEW_PLAN_01_03, self.fixture.read("01-03-PLAN.md"))

    def test_partition_not_union_tasks_move_and_source_shrinks(self):
        result = run(str(self.fixture.phase_dir), "02", "--after", "1")
        self.assertEqual(0, result.returncode, result.stderr)
        src_text = self.fixture.read("01-02-PLAN.md")
        new_text = self.fixture.read("01-03-PLAN.md")
        # source no longer has tasks 2/3 (build c, build d)
        self.assertNotIn("build c", src_text)
        self.assertNotIn("build d", src_text)
        self.assertIn("build b", src_text)
        # new plan has them, renumbered starting at Task 1
        self.assertIn("Task 1: build c", new_text)
        self.assertIn("Task 2: build d", new_text)
        self.assertNotIn("Task 3", new_text)
        # source shrank in bytes relative to its own pre-split size
        self.assertLess(len(src_text.encode("utf-8")),
                         len(self.before["01-02-PLAN.md"].encode("utf-8")))

    @staticmethod
    def _files_modified_block(text: str) -> str:
        return text.split("files_modified:", 1)[1].split("autonomous:", 1)[0]

    def test_files_modified_partitioned_per_side(self):
        result = run(str(self.fixture.phase_dir), "02", "--after", "1")
        self.assertEqual(0, result.returncode, result.stderr)
        src_files = self._files_modified_block(self.fixture.read("01-02-PLAN.md"))
        new_files = self._files_modified_block(self.fixture.read("01-03-PLAN.md"))
        self.assertIn("- src/b.py", src_files)
        self.assertNotIn("- src/c.py", src_files)
        self.assertNotIn("- src/d.py", src_files)
        self.assertIn("- src/c.py", new_files)
        self.assertIn("- src/d.py", new_files)
        self.assertNotIn("- src/b.py", new_files)

    def test_no_must_haves_entry_lost_across_a_split(self):
        # Additional no-loss cross-check — kept alongside, not instead of, the partition
        # assertions above (a union check alone can't tell a real split from no split).
        run(str(self.fixture.phase_dir), "02", "--after", "1")
        after = self.fixture.snapshot()
        self.assertEqual(must_haves_union(self.before), must_haves_union(after))

    def test_tail_shift_renumbers_files_and_plan_fields(self):
        result = run(str(self.fixture.phase_dir), "02", "--after", "1")
        self.assertEqual(0, result.returncode, result.stderr)
        names = sorted(p.name for p in self.fixture.phase_dir.iterdir())
        self.assertEqual(
            ["01-01-PLAN.md", "01-02-PLAN.md", "01-03-PLAN.md", "01-04-PLAN.md",
             "01-05-PLAN.md"], names)
        self.assertIn("plan: 04", self.fixture.read("01-04-PLAN.md"))
        self.assertIn("plan: 05", self.fixture.read("01-05-PLAN.md"))
        self.assertIn('"e exists"', self.fixture.read("01-04-PLAN.md"))
        self.assertIn("depends_on: [01-04]", self.fixture.read("01-05-PLAN.md"))

    def test_prose_reference_rewritten_for_shifted_plan(self):
        run(str(self.fixture.phase_dir), "02", "--after", "1")
        text_01 = self.fixture.read("01-01-PLAN.md")
        self.assertIn("See 01-05 for the followup", text_01)
        self.assertNotIn("See 01-04 for the followup", text_01)

    def test_dry_run_writes_nothing(self):
        result = run(str(self.fixture.phase_dir), "02", "--after", "1", "--dry-run")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(self.before, self.fixture.snapshot())

    def test_dangling_split_exits_nonzero_and_writes_nothing(self):
        bad = self.fixture.read("01-04-PLAN.md").replace(
            "depends_on: [01-03]", "depends_on: [01-09]")
        self.fixture.write("01-04-PLAN.md", bad)
        before = self.fixture.snapshot()
        result = run(str(self.fixture.phase_dir), "02", "--after", "1")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("01-09", result.stderr)
        self.assertEqual(before, self.fixture.snapshot())


# --- Fixture 2: untracked plans in a real git repo (B6) ---------------------------------

PLAN_UT_01 = """---
phase: 01-demo-phase
plan: 01
wave: 1
depends_on: []
files_modified:
  - src/a.py
autonomous: true
requirements: [REQ-01]
must_haves:
  truths:
    - "a exists"
  artifacts:
    - src/a.py
  key_links: []
---

<objective>First plan.</objective>

<context>none</context>

<tasks>

<task type="auto">
  <name>Task 1: build a</name>
  <files>src/a.py</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

</tasks>
"""

PLAN_UT_02_SRC = """---
phase: 01-demo-phase
plan: 02
wave: 1
depends_on: []
files_modified:
  - src/b.py
  - src/c.py
autonomous: true
requirements: [REQ-01]
must_haves:
  truths:
    - "src/b.py works"
    - "src/c.py works"
  artifacts:
    - src/b.py
    - src/c.py
  key_links: []
---

<objective>Second plan.</objective>

<context>none</context>

<tasks>

<task type="auto">
  <name>Task 1: build b</name>
  <files>src/b.py</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

<task type="auto">
  <name>Task 2: build c</name>
  <files>src/c.py</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

</tasks>
"""

PLAN_UT_03 = """---
phase: 01-demo-phase
plan: 03
wave: 2
depends_on: [01-02]
files_modified:
  - src/e.py
autonomous: true
requirements: [REQ-01]
must_haves:
  truths:
    - "e exists"
  artifacts:
    - src/e.py
  key_links: []
---

<objective>Third plan.</objective>

<context>depends on 01-02</context>

<tasks>

<task type="auto">
  <name>Task 1: build e</name>
  <files>src/e.py</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

</tasks>
"""


class UntrackedGitSplitTests(unittest.TestCase):
    def test_untracked_plans_split_successfully(self):
        fixture = TempPhase()
        self.addCleanup(fixture.cleanup)
        git(fixture.root, "init", "-q")
        git(fixture.root, "config", "user.email", "test@example.com")
        git(fixture.root, "config", "user.name", "test")
        fixture.write("01-01-PLAN.md", PLAN_UT_01)
        fixture.write("01-02-PLAN.md", PLAN_UT_02_SRC)
        fixture.write("01-03-PLAN.md", PLAN_UT_03)
        # deliberately NOT `git add`ed — this is plans' real state at /flow-plan step 4
        result = run(str(fixture.phase_dir), "02", "--after", "1")
        self.assertEqual(0, result.returncode, result.stderr)
        names = sorted(p.name for p in fixture.phase_dir.iterdir())
        self.assertEqual(
            ["01-01-PLAN.md", "01-02-PLAN.md", "01-03-PLAN.md", "01-04-PLAN.md"], names)
        self.assertIn("plan: 04", fixture.read("01-04-PLAN.md"))

    def test_mixed_tracked_and_untracked_plans_split_successfully(self):
        fixture = TempPhase()
        self.addCleanup(fixture.cleanup)
        git(fixture.root, "init", "-q")
        git(fixture.root, "config", "user.email", "test@example.com")
        git(fixture.root, "config", "user.name", "test")
        fixture.write("01-01-PLAN.md", PLAN_UT_01)
        fixture.write("01-02-PLAN.md", PLAN_UT_02_SRC)
        git(fixture.root, "add", "01-demo-phase/01-01-PLAN.md", "01-demo-phase/01-02-PLAN.md")
        git(fixture.root, "commit", "-q", "-m", "init")
        fixture.write("01-03-PLAN.md", PLAN_UT_03)  # untracked
        result = run(str(fixture.phase_dir), "02", "--after", "1")
        self.assertEqual(0, result.returncode, result.stderr)
        names = sorted(p.name for p in fixture.phase_dir.iterdir())
        self.assertEqual(
            ["01-01-PLAN.md", "01-02-PLAN.md", "01-03-PLAN.md", "01-04-PLAN.md"], names)


# --- Fixture 3: decoy tokens that must survive untouched, plus one real reference -------

PLAN_DECOY_01 = """---
phase: 01-demo-phase
plan: 01
wave: 1
depends_on: []
files_modified:
  - src/a.py
autonomous: true
requirements: [REQ-01]
must_haves:
  truths:
    - "a exists"
  artifacts:
    - src/a.py
  key_links: []
---

<objective>First plan. See RFC dated 2026-09-09 and lines 12-40, ticket AB-01-03, \
version 5.01-04.x. Also see 01-03 for the followup.</objective>

<context>none</context>

<tasks>

<task type="auto">
  <name>Task 1: build a</name>
  <files>src/a.py</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

</tasks>
"""


class DecoyReferenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = TempPhase()
        self.addCleanup(self.fixture.cleanup)
        self.fixture.write("01-01-PLAN.md", PLAN_DECOY_01)
        self.fixture.write("01-02-PLAN.md", PLAN_UT_02_SRC)
        self.fixture.write("01-03-PLAN.md", PLAN_UT_03)
        self.result = run(str(self.fixture.phase_dir), "02", "--after", "1")
        self.assertEqual(0, self.result.returncode, self.result.stderr)
        self.objective = self.fixture.read("01-01-PLAN.md")

    def test_iso_date_decoy_untouched(self):
        self.assertIn("2026-09-09", self.objective)

    def test_line_range_decoy_untouched(self):
        self.assertIn("lines 12-40", self.objective)

    def test_ticket_id_decoy_untouched(self):
        self.assertIn("ticket AB-01-03", self.objective)

    def test_version_string_decoy_untouched(self):
        self.assertIn("version 5.01-04.x", self.objective)

    def test_real_reference_is_rewritten(self):
        self.assertIn("see 01-04 for the followup", self.objective)
        self.assertNotIn("see 01-03 for the followup", self.objective)


# --- Fixture 4: B3 — real edge vs. no spurious edge --------------------------------------

PLAN_ORDERED_SRC = """---
phase: 01-demo-phase
plan: 02
wave: 1
depends_on: []
files_modified:
  - src/db/repo.ts
  - src/routes/route.ts
autonomous: true
requirements: [REQ-01]
must_haves:
  truths:
    - "repo works"
    - "route works"
  artifacts:
    - src/db/repo.ts
    - src/routes/route.ts
  key_links:
    - "route imports repo"
---

<objective>Ordered plan: T1 creates repo.ts, T2 tests it, T3 adds a route importing \
repo.ts, T4 tests the route.</objective>

<context>none</context>

<tasks>

<task type="auto">
  <name>Task 1: create repo</name>
  <files>src/db/repo.ts</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

<task type="auto">
  <name>Task 2: test repo</name>
  <files>src/db/repo.ts</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

<task type="auto">
  <name>Task 3: add route importing repo</name>
  <files>src/db/repo.ts, src/routes/route.ts</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

<task type="auto">
  <name>Task 4: test route</name>
  <files>src/routes/route.ts</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

</tasks>
"""

PLAN_DISJOINT_SRC = """---
phase: 01-demo-phase
plan: 01
wave: 1
depends_on: []
files_modified:
  - src/db/repo.ts
  - src/routes/route.ts
autonomous: true
requirements: [REQ-01]
must_haves:
  truths:
    - "repo works"
    - "route works"
  artifacts:
    - src/db/repo.ts
    - src/routes/route.ts
  key_links: []
---

<objective>Disjoint plan: two unrelated tasks on separate files.</objective>

<context>none</context>

<tasks>

<task type="auto">
  <name>Task 1: build repo</name>
  <files>src/db/repo.ts</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

<task type="auto">
  <name>Task 2: build route</name>
  <files>src/routes/route.ts</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

</tasks>
"""


class DependsOnEdgeTests(unittest.TestCase):
    def test_ordered_split_gets_depends_on_edge_and_later_wave(self):
        fixture = TempPhase()
        self.addCleanup(fixture.cleanup)
        fixture.write("01-02-PLAN.md", PLAN_ORDERED_SRC)
        result = run(str(fixture.phase_dir), "02", "--after", "2")
        self.assertEqual(0, result.returncode, result.stderr)
        new_text = fixture.read("01-03-PLAN.md")
        src_text = fixture.read("01-02-PLAN.md")
        self.assertIn("depends_on: [01-02]", new_text)
        self.assertIn("wave: 2", new_text)
        self.assertIn("wave: 1", src_text)  # source's own wave is untouched

    def test_disjoint_split_does_not_get_spurious_edge(self):
        fixture = TempPhase()
        self.addCleanup(fixture.cleanup)
        fixture.write("01-01-PLAN.md", PLAN_DISJOINT_SRC)
        result = run(str(fixture.phase_dir), "01", "--after", "1")
        self.assertEqual(0, result.returncode, result.stderr)
        new_text = fixture.read("01-02-PLAN.md")
        src_text = fixture.read("01-01-PLAN.md")
        self.assertIn("depends_on: []", new_text)
        self.assertIn("wave: 1", new_text)
        self.assertIn("depends_on: []", src_text)
        self.assertIn("wave: 1", src_text)


# --- Fixture 5: autonomous recomputed per side -------------------------------------------

PLAN_CHECKPOINT_SRC = """---
phase: 01-demo-phase
plan: 01
wave: 1
depends_on: []
files_modified:
  - src/x.py
  - src/y.py
autonomous: false
requirements: [REQ-01]
must_haves:
  truths:
    - "src/x.py exists"
    - "src/y.py exists"
  artifacts:
    - src/x.py
    - src/y.py
  key_links: []
---

<objective>Checkpoint plan: T1 builds x, T2 is a human checkpoint, T3 builds y.</objective>

<context>none</context>

<tasks>

<task type="auto">
  <name>Task 1: build x</name>
  <files>src/x.py</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

<task type="checkpoint:human-action">
  <name>Task 2: get a secret</name>
  <files></files>
  <action>create the account</action>
  <verify><human-check>done manually</human-check></verify>
  <done>done</done>
</task>

<task type="auto">
  <name>Task 3: build y</name>
  <files>src/y.py</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

</tasks>
"""


class AutonomousRecomputeTests(unittest.TestCase):
    def test_autonomous_recomputed_per_side(self):
        fixture = TempPhase()
        self.addCleanup(fixture.cleanup)
        fixture.write("01-01-PLAN.md", PLAN_CHECKPOINT_SRC)
        result = run(str(fixture.phase_dir), "01", "--after", "1")
        self.assertEqual(0, result.returncode, result.stderr)
        # source kept only Task 1 (no checkpoint) -> autonomous: true, even though the
        # SOURCE FILE originally declared autonomous: false
        self.assertIn("autonomous: true", fixture.read("01-01-PLAN.md"))
        # new plan got the checkpoint task -> autonomous: false
        self.assertIn("autonomous: false", fixture.read("01-02-PLAN.md"))


# --- Fixture 6: forced OSError mid-write leaves the phase dir byte-identical -------------

PLAN_OS_01 = """---
phase: 01-demo-phase
plan: 01
wave: 1
depends_on: []
files_modified:
  - src/a.py
autonomous: true
requirements: [REQ-01]
must_haves:
  truths:
    - "a exists"
  artifacts:
    - src/a.py
  key_links: []
---

<objective>First plan, untouched.</objective>

<context>none</context>

<tasks>

<task type="auto">
  <name>Task 1: build a</name>
  <files>src/a.py</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

</tasks>
"""

PLAN_OS_02_SRC = """---
phase: 01-demo-phase
plan: 02
wave: 2
depends_on: [01-01]
files_modified:
  - src/b.py
  - src/c.py
autonomous: true
requirements: [REQ-01]
must_haves:
  truths:
    - "b works"
    - "c works"
  artifacts:
    - src/b.py
    - src/c.py
  key_links: []
---

<objective>Second plan, to be split (source).</objective>

<context>none</context>

<tasks>

<task type="auto">
  <name>Task 1: build b</name>
  <files>src/b.py</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

<task type="auto">
  <name>Task 2: build c</name>
  <files>src/c.py</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

</tasks>
"""

PLAN_OS_05 = """---
phase: 01-demo-phase
plan: 05
wave: 1
depends_on: []
files_modified:
  - src/z.py
autonomous: true
requirements: [REQ-01]
must_haves:
  truths:
    - "z exists"
  artifacts:
    - src/z.py
  key_links: []
---

<objective>Sparse tail plan, numbered 05 (gap between 02 and 05 is fine).</objective>

<context>none</context>

<tasks>

<task type="auto">
  <name>Task 1: build z</name>
  <files>src/z.py</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>

</tasks>
"""


class ForcedOSErrorRollbackTests(unittest.TestCase):
    def test_forced_oserror_mid_write_leaves_phase_dir_byte_identical(self):
        fixture = TempPhase()
        self.addCleanup(fixture.cleanup)
        fixture.write("01-01-PLAN.md", PLAN_OS_01)
        fixture.write("01-02-PLAN.md", PLAN_OS_02_SRC)
        fixture.write("01-05-PLAN.md", PLAN_OS_05)
        # The new plan's target slot (01-03-PLAN.md) is genuinely never occupied by any
        # real plan — obstruct it as a directory so the write phase hits IsADirectoryError
        # only AFTER the rename phase has already moved 01-05 -> 01-06 for real.
        (fixture.phase_dir / "01-03-PLAN.md").mkdir()
        before = fixture.snapshot()
        before_dirs = {p.name for p in fixture.phase_dir.iterdir() if p.is_dir()}

        result = run(str(fixture.phase_dir), "02", "--after", "1")

        self.assertNotEqual(0, result.returncode)
        self.assertIn("write phase failed", result.stderr)
        after = fixture.snapshot()
        after_dirs = {p.name for p in fixture.phase_dir.iterdir() if p.is_dir()}
        self.assertEqual(before, after)
        self.assertEqual(before_dirs, after_dirs)
        # the 05 -> 06 rename must have been rolled back, not left applied
        self.assertTrue((fixture.phase_dir / "01-05-PLAN.md").exists())
        self.assertFalse((fixture.phase_dir / "01-06-PLAN.md").exists())


if __name__ == "__main__":
    unittest.main()
