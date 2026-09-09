import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/devflow/scripts/flow-split-plan.py"

spec = importlib.util.spec_from_file_location("flow_split_plan", SCRIPT)
flow_split_plan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow_split_plan)


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def plan(phase, num, wave, depends_on, files_modified, truths, artifacts, key_links,
         objective, context, tasks):
    # Build the frontmatter with the module's own serializer, so a fixture is guaranteed
    # to be exactly the shape the tool under test expects (no hand-templated YAML drift).
    fm = flow_split_plan.format_frontmatter(
        phase=phase, plan_num=num, wave=str(wave), depends_on=depends_on,
        files_modified=files_modified, autonomous="true", requirements=[f"REQ-{num}"],
        must_haves={"truths": truths, "artifacts": artifacts, "key_links": key_links})
    return f"""{fm}
<objective>{objective}</objective>

<context>{context}</context>

<tasks>

{tasks}

</tasks>
"""


def task(n, name, files):
    return f"""<task type="auto">
  <name>Task {n}: {name}</name>
  <files>{files}</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>"""


class PhaseFixture:
    """A throwaway phase directory (four plans, a depends_on chain, and a cross-plan prose
    reference) built entirely under the system temp dir — never inside this repo."""

    def __init__(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.phase_dir = Path(self.tempdir.name) / "01-demo-phase"
        self.phase_dir.mkdir()
        self._write_default()

    def _write_default(self):
        (self.phase_dir / "01-01-PLAN.md").write_text(plan(
            "01-demo-phase", "01", 1, [], ["src/a.py"],
            ["a exists"], ["src/a.py"], ["a links to b"],
            "First plan. See 01-04 for the followup.", "none",
            task(1, "build a", "src/a.py"),
        ), encoding="utf-8")
        (self.phase_dir / "01-02-PLAN.md").write_text(plan(
            "01-demo-phase", "02", 2, ["01-01"], ["src/b.py", "src/c.py", "src/d.py"],
            ["src/b.py exists and works", "src/c.py exists and works",
             "src/d.py exists and works"],
            ["src/b.py", "src/c.py", "src/d.py"],
            ["src/b.py calls src/c.py", "src/c.py calls src/d.py"],
            "Second plan, over cap, needs a split.", "depends on 01-01",
            "\n\n".join([task(1, "build b", "src/b.py"), task(2, "build c", "src/c.py"),
                         task(3, "build d", "src/d.py")]),
        ), encoding="utf-8")
        (self.phase_dir / "01-03-PLAN.md").write_text(plan(
            "01-demo-phase", "03", 3, ["01-02"], ["src/e.py"],
            ["e exists"], ["src/e.py"], [],
            "Third plan, depends on second.", "depends on 01-02",
            task(1, "build e", "src/e.py"),
        ), encoding="utf-8")
        (self.phase_dir / "01-04-PLAN.md").write_text(plan(
            "01-demo-phase", "04", 4, ["01-03"], ["src/f.py"],
            ["f exists"], ["src/f.py"], [],
            "Fourth plan, referenced from 01-01.", "depends on 01-03",
            task(1, "build f", "src/f.py"),
        ), encoding="utf-8")

    def snapshot(self):
        return {p.name: p.read_text(encoding="utf-8")
                for p in sorted(self.phase_dir.iterdir())}

    def cleanup(self):
        self.tempdir.cleanup()


def must_haves_union(snapshot):
    """The set of every must_haves.{truths,backstop_truths,artifacts,key_links} entry
    across every plan in a snapshot (filename -> text), dequoted."""
    entries = set()
    for text in snapshot.values():
        fm_text, _ = flow_split_plan.split_frontmatter(text)
        data = flow_split_plan.parse_yaml_lite(fm_text)
        mh = data.get("must_haves", {})
        for key in ("truths", "backstop_truths", "artifacts", "key_links"):
            for raw in mh.get(key, []):
                entries.add(flow_split_plan.dequote(raw))
    return entries


class SplitTailShiftTests(unittest.TestCase):
    def setUp(self):
        self.fixture = PhaseFixture()
        self.addCleanup(self.fixture.cleanup)
        self.before = self.fixture.snapshot()

    def test_tail_shift_renumbers_files_and_plan_fields(self):
        result = run(str(self.fixture.phase_dir), "02", "--after", "1")
        self.assertEqual(0, result.returncode, result.stderr)
        names = sorted(p.name for p in self.fixture.phase_dir.iterdir())
        self.assertEqual(
            ["01-01-PLAN.md", "01-02-PLAN.md", "01-03-PLAN.md", "01-04-PLAN.md",
             "01-05-PLAN.md"], names)
        # old 01-03 -> 01-04, old 01-04 -> 01-05; each file's `plan:` field matches its
        # new filename number.
        self.assertIn("plan: 04", (self.fixture.phase_dir / "01-04-PLAN.md").read_text())
        self.assertIn("plan: 05", (self.fixture.phase_dir / "01-05-PLAN.md").read_text())
        # the content that used to live in 01-03 (depends_on [01-02], "e exists") now
        # lives at 01-04 — the rename carried the file's own content, not a fresh plan.
        self.assertIn('"e exists"', (self.fixture.phase_dir / "01-04-PLAN.md").read_text())

    def test_depends_on_entries_following_a_shifted_plan_are_rewritten(self):
        run(str(self.fixture.phase_dir), "02", "--after", "1")
        # old 01-04 (now 01-05) depended on old 01-03 (now 01-04) -> depends_on: [01-04]
        text_05 = (self.fixture.phase_dir / "01-05-PLAN.md").read_text()
        self.assertIn("depends_on: [01-04]", text_05)
        # old 01-03 (now 01-04) depended on 01-02, which did NOT shift -> unchanged
        text_04 = (self.fixture.phase_dir / "01-04-PLAN.md").read_text()
        self.assertIn("depends_on: [01-02]", text_04)

    def test_prose_nn_mm_references_are_rewritten(self):
        run(str(self.fixture.phase_dir), "02", "--after", "1")
        text_01 = (self.fixture.phase_dir / "01-01-PLAN.md").read_text()
        self.assertIn("See 01-05 for the followup", text_01)
        self.assertNotIn("See 01-04 for the followup", text_01)

    def test_no_must_haves_entry_is_lost_across_a_split(self):
        run(str(self.fixture.phase_dir), "02", "--after", "1")
        after = self.fixture.snapshot()
        self.assertEqual(must_haves_union(self.before), must_haves_union(after))

    def test_dry_run_writes_nothing(self):
        result = run(str(self.fixture.phase_dir), "02", "--after", "1", "--dry-run")
        self.assertEqual(0, result.returncode, result.stderr)
        after = self.fixture.snapshot()
        self.assertEqual(self.before, after)

    def test_dangling_split_exits_nonzero_and_writes_nothing(self):
        # Point 01-04's depends_on at a plan id that will not exist, pre- or post-shift.
        bad = (self.fixture.phase_dir / "01-04-PLAN.md").read_text().replace(
            "depends_on: [01-03]", "depends_on: [01-09]")
        (self.fixture.phase_dir / "01-04-PLAN.md").write_text(bad, encoding="utf-8")
        before = self.fixture.snapshot()
        result = run(str(self.fixture.phase_dir), "02", "--after", "1")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("01-09", result.stderr)
        after = self.fixture.snapshot()
        self.assertEqual(before, after)

    def test_reported_byte_size_matches_file_on_disk(self):
        result = run(str(self.fixture.phase_dir), "02", "--after", "1")
        self.assertEqual(0, result.returncode, result.stderr)
        reported = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line.startswith("01-") or "bytes)" not in line:
                continue
            plan_id, rest = line.split(":", 1)
            path_str, size_str = rest.rsplit("(", 1)
            reported[plan_id.strip()] = int(size_str.split()[0])
        self.assertTrue(reported, "no per-plan byte-size lines found in stdout")
        for plan_id, size in reported.items():
            num = plan_id.split("-")[1]
            path = self.fixture.phase_dir / f"01-{num}-PLAN.md"
            self.assertEqual(size, path.stat().st_size, f"{plan_id}: reported size mismatch")


if __name__ == "__main__":
    unittest.main()
