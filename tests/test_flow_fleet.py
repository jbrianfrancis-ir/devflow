"""Tests for the fleet scanner's parsing and its fail-closed guarantees.

The scanner is the only thing an outside driver reads, so its two promises are
load-bearing: the `## Gate` block reaches a caller as structured data (the one
exception to "never parse skill prose"), and a check that could not run is never
reported as clean (references/conventions.md → Fail-closed guards).
"""
import datetime
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCANNER = ROOT / "plugins/devflow/scripts/flow-fleet.py"

# Journal date for fixtures that mean "this project has recent activity". It must
# track the clock: the scanner flags STALE at age_days >= stale_days (default 3)
# and STALE implies needs_human, so a hardcoded date silently converts any
# "nothing needs a human" assertion into a time bomb that fires days later and
# never passes again.
TODAY = datetime.date.today().isoformat()
SPEC = importlib.util.spec_from_file_location("flow_fleet", SCANNER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

POSITION = """# State

## Position
Phase: 3 of 6 (payments) | Plans: 2/4 | Status: executing
Last: 2026-08-15 — executor paused
Next: /flow-execute 3
"""

GATE_BLOCK = """
## Gate
type: decision
asked: Job queue backend not settled by REQ-07
options:
  1. Postgres — matches the ARCHITECTURE pin; needs a dev container
  2. SQLite — zero infra; no concurrent writers
default: none
plan: 03-02 | task: 2
"""

RUN_BLOCK = """
## Run
Iteration: 7 | Started: 2026-08-15T09:12Z | Repeats: 2
Signature: rule5:phase03:plans2/4:verif-gaps
"""

BLOCKERS_NONE = "\n## Blockers\n- none\n"


class ParseGateTests(unittest.TestCase):
    def test_absent_block_is_none(self):
        self.assertIsNone(MODULE.parse_gate(POSITION))

    def test_literal_none_is_none(self):
        self.assertIsNone(MODULE.parse_gate(POSITION + "\n## Gate\nnone\n"))

    def test_populated_block_parses_every_field(self):
        g = MODULE.parse_gate(POSITION + GATE_BLOCK + BLOCKERS_NONE)
        self.assertEqual(g["type"], "decision")
        self.assertEqual(g["asked"], "Job queue backend not settled by REQ-07")
        self.assertEqual(g["default"], "none")
        self.assertEqual(g["plan"], "03-02")
        self.assertEqual(g["task"], "2")
        self.assertEqual(len(g["options"]), 2)
        # The numbering is a rendering detail; the option text is the payload.
        self.assertTrue(g["options"][0].startswith("Postgres —"))
        self.assertTrue(g["options"][1].startswith("SQLite —"))

    def test_options_stop_at_the_next_field(self):
        """`default:` and `plan:` follow the option list; neither may be swallowed as an option."""
        g = MODULE.parse_gate(POSITION + GATE_BLOCK + BLOCKERS_NONE)
        self.assertFalse(any("default" in o or "task:" in o for o in g["options"]))

    def test_human_action_gate_without_options(self):
        block = "\n## Gate\ntype: human-action\nasked: Grant the repo to this session\ndefault: none\n"
        g = MODULE.parse_gate(POSITION + block)
        self.assertEqual(g["type"], "human-action")
        self.assertEqual(g["options"], [])

    def test_gate_without_asked_is_not_a_gate_record(self):
        """A record that never says what it asks would render as a blank prompt."""
        self.assertIsNone(MODULE.parse_gate(POSITION + "\n## Gate\ntype: decision\ndefault: none\n"))

    def test_single_line_comment_is_not_content(self):
        block = "\n## Gate\n<!-- when gated, replace `none` with: -->\nnone\n"
        self.assertIsNone(MODULE.parse_gate(POSITION + block))

    def test_multiline_comment_body_is_not_content(self):
        """Inner comment lines carry no `<!--` prefix, so a line filter would let them
        through and surface a commented example as a live gate."""
        block = ("\n## Gate\n<!-- when gated, replace with:\n"
                 "type: decision\nasked: Example question\noptions:\n  1. a — b\n-->\nnone\n")
        self.assertIsNone(MODULE.parse_gate(POSITION + block))

    def test_shipped_state_template_is_not_a_live_gate(self):
        """The template documents the gate format as a commented example inside the very
        section it describes. If the parser ever reads it as real, every project created
        from the template would board as gated on a placeholder question."""
        template = (ROOT / "plugins/devflow/templates/state.md").read_text(encoding="utf-8")
        self.assertIsNone(MODULE.parse_gate(template))


class ParseRunTests(unittest.TestCase):
    def test_absent_block_is_none_meaning_cold_start(self):
        self.assertIsNone(MODULE.parse_run(POSITION))

    def test_well_formed_block(self):
        r = MODULE.parse_run(POSITION + RUN_BLOCK)
        self.assertEqual(r["iteration"], 7)
        self.assertEqual(r["repeats"], 2)
        self.assertEqual(r["started"], "2026-08-15T09:12Z")
        self.assertEqual(r["signature"], "rule5:phase03:plans2/4:verif-gaps")
        self.assertNotIn("malformed", r)

    def test_malformed_block_is_flagged_never_zeroed(self):
        """A zeroed counter would read as a fresh run and silently disarm the stuck rail."""
        for bad in ("\n## Run\nIteration: not-a-number | Repeats: nope\n",
                    "\n## Run\nIteration: 4\n",          # no Repeats
                    "\n## Run\nRepeats: 2\n"):           # no Iteration
            with self.subTest(bad=bad.strip()):
                r = MODULE.parse_run(POSITION + bad)
                self.assertTrue(r.get("malformed"), bad)
                self.assertNotIn("repeats", r)


class ScanTests(unittest.TestCase):
    """End-to-end over real directories, since scan() also consults git."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def project(self, name, state, journal="- 2026-08-15 | /flow-execute | phase 3 | GATE"):
        d = self.base / name
        (d / ".planning").mkdir(parents=True)
        (d / ".planning" / "STATE.md").write_text(state, encoding="utf-8")
        if journal is not None:
            (d / ".planning" / "JOURNAL.md").write_text("# Journal\n" + journal + "\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", "-b", "main", "."], cwd=d, check=True,
                       capture_output=True)
        subprocess.run(["git", "add", "-A"], cwd=d, check=True, capture_output=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-qm", "init"], cwd=d, check=True, capture_output=True)
        return d

    def scan(self, d):
        return MODULE.scan(str(d), datetime.date(2026, 8, 15), 3)

    def test_gate_reaches_json_as_structured_data(self):
        p = self.scan(self.project("gated", POSITION + GATE_BLOCK + BLOCKERS_NONE))
        self.assertEqual(p["flow"], "GATE")
        self.assertTrue(p["needs_human"])
        self.assertEqual(p["gate"]["asked"], "Job queue backend not settled by REQ-07")
        self.assertEqual(len(p["gate"]["options"]), 2)
        # It must survive a JSON round-trip — that is how a driver actually receives it.
        self.assertEqual(json.loads(json.dumps(p))["gate"]["plan"], "03-02")

    def test_no_gate_is_null(self):
        state = POSITION + "\n## Gate\nnone\n" + BLOCKERS_NONE
        p = self.scan(self.project("clean", state,
                                   journal="- 2026-08-15 | /flow-execute | phase 3 | CONTINUE"))
        self.assertIsNone(p["gate"])
        self.assertFalse(p["needs_human"])

    def test_missing_journal_is_unknown_and_needs_a_human(self):
        """flow: unknown means the check did not run — that is attention, not silence."""
        p = self.scan(self.project("nojournal", POSITION + BLOCKERS_NONE, journal=None))
        self.assertEqual(p["flow"], "unknown")
        self.assertIn("FLOW-UNKNOWN", p["flags"])
        self.assertTrue(p["needs_human"])
        self.assertEqual(MODULE.rank(p), 0)

    def test_unparseable_journal_state_is_unknown(self):
        p = self.scan(self.project("badjournal", POSITION + BLOCKERS_NONE,
                                   journal="- 2026-08-15 | /flow-execute | phase 3 | WAT"))
        self.assertEqual(p["flow"], "unknown")
        self.assertTrue(p["needs_human"])

    def test_malformed_run_block_needs_a_human(self):
        state = POSITION + "\n## Run\nIteration: oops\n" + BLOCKERS_NONE
        p = self.scan(self.project("badrun", state,
                                   journal="- 2026-08-15 | /flow-execute | phase 3 | CONTINUE"))
        self.assertIn("RUN-UNKNOWN", p["flags"])
        self.assertTrue(p["needs_human"])
        self.assertEqual(MODULE.rank(p), 0)

    def test_run_counters_reach_json(self):
        state = POSITION + RUN_BLOCK + BLOCKERS_NONE
        p = self.scan(self.project("running", state,
                                   journal="- 2026-08-15 | /flow-plan | gaps | CONTINUE"))
        self.assertEqual(p["run"]["repeats"], 2)
        self.assertEqual(p["run"]["iteration"], 7)

    def test_render_surfaces_gate_options_to_the_human(self):
        """The whole point of the structured gate: the choices reach the operator."""
        p = self.scan(self.project("gated", POSITION + GATE_BLOCK + BLOCKERS_NONE))
        out = MODULE.render([p], 3)
        self.assertIn("Job queue backend not settled by REQ-07", out)
        self.assertIn("1. Postgres", out)
        self.assertIn("2. SQLite", out)

    def test_exit_status_is_one_when_any_project_needs_a_human(self):
        # T1: journal must itself carry a live GATE, not just be recent — a
        # journal that only says CONTINUE would still pass this assertion via
        # staleness (age_days >= stale_days also sets needs_human), which
        # never actually exercises the GATE path the test is named for.
        self.project("gated", POSITION + GATE_BLOCK + BLOCKERS_NONE,
                     journal="- %s | /flow-execute | phase 3 | GATE" % TODAY)
        with redirect_stdout(io.StringIO()):
            # T2: --stale-days pinned explicitly so this doesn't depend on
            # the developer's ~/.devflow/fleet.json (main() falls back to it
            # when the flag is absent).
            code = MODULE.main([str(self.base), "--json", "--depth", "2", "--stale-days", "3"])
        self.assertEqual(code, 1)

    def test_exit_status_is_zero_when_everything_is_fine(self):
        state = POSITION + "\n## Gate\nnone\n" + RUN_BLOCK.replace("Repeats: 2", "Repeats: 0") + BLOCKERS_NONE
        self.project("clean", state, journal="- %s | /flow-execute | phase 3 | CONTINUE" % TODAY)
        buf = io.StringIO()
        with redirect_stdout(buf):
            # T2: see above — pinned so a host config of e.g. stale_days: 0
            # can't turn a "clean" fixture stale and flip this to non-zero.
            code = MODULE.main([str(self.base), "--json", "--depth", "2", "--stale-days", "3"])
        self.assertEqual(code, 0, buf.getvalue())




class PluginVersionTests(unittest.TestCase):
    """Version staleness, and the three outcomes it must not collapse.

    Every DevFlow repo carries the self-bootstrap block, so each gets its own
    pinned install and they drift apart with nothing reconciling them. The
    scanner reports that drift; these pin the reporting, and in particular that
    "no Claude plugin system here" (absent) is never confused with "the registry
    would not parse" (unreadable) — the first is not applicable, the second is a
    check that did not run.
    """

    def scan_with(self, versions, project_version=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proj"
            (path / ".planning").mkdir(parents=True)
            (path / ".planning" / "STATE.md").write_text(
                "# State\n\n## Position\nPhase: 1 of 2 | Plans: 1/1 | Status: verified\n"
                "Next: /flow-plan 2\nLast: %s — ok\n\n## Gate\nnone\n\n## Blockers\n- none\n" % TODAY,
                encoding="utf-8")
            (path / ".planning" / "JOURNAL.md").write_text(
                "# Journal\n- %s | /flow-plan 1 | done | CONTINUE\n" % TODAY, encoding="utf-8")
            if project_version:
                versions = dict(versions)
                versions["by_path"] = {str(Path(path).resolve()): project_version}
            return MODULE.scan(str(path), datetime.date.today(), 3, versions)

    def test_behind_the_newest_known_is_flagged(self):
        p = self.scan_with({"by_path": {}, "user": "0.15.0", "latest": "0.15.0", "state": "ok"},
                           project_version="0.12.0")
        self.assertIn("OLD-PLUGIN", p["flags"])
        self.assertEqual(p["devflow_version"], "0.12.0")

    def test_current_version_is_not_flagged(self):
        p = self.scan_with({"by_path": {}, "user": "0.15.0", "latest": "0.15.0", "state": "ok"},
                           project_version="0.15.0")
        self.assertNotIn("OLD-PLUGIN", p["flags"])

    def test_absent_plugin_system_is_not_a_failure(self):
        # A Codex host or a container has no ~/.claude/plugins. That is "not
        # applicable" — flagging it would make every project on such a machine
        # need a human for a check that does not apply there.
        p = self.scan_with({"by_path": {}, "user": None, "latest": None, "state": "absent"})
        self.assertNotIn("VER-UNKNOWN", p["flags"])
        self.assertNotIn("OLD-PLUGIN", p["flags"])
        self.assertIsNone(p["devflow_version"])

    def test_unreadable_registry_is_never_clean(self):
        # It exists but would not parse: a check that did not run, so it must
        # flag and count in needs_human (conventions.md → Fail-closed guards).
        p = self.scan_with({"by_path": {}, "user": None, "latest": None, "state": "unreadable"})
        self.assertIn("VER-UNKNOWN", p["flags"])
        self.assertTrue(p["needs_human"])

    def test_unknown_latest_cannot_flag_anything_stale(self):
        p = self.scan_with({"by_path": {}, "user": None, "latest": None, "state": "ok"},
                           project_version="0.12.0")
        self.assertNotIn("OLD-PLUGIN", p["flags"])

    def test_semver_rejects_non_versions(self):
        self.assertEqual(MODULE.semver("1.2.3"), (1, 2, 3))
        for bad in ("1.2", "1.2.3.4", "v1.2.3", "1.2.x", None, "", "main"):
            self.assertIsNone(MODULE.semver(bad), bad)

    def test_semver_orders_numerically_not_lexically(self):
        # "0.9.0" > "0.10.0" as strings; the whole check depends on it not being.
        self.assertLess(MODULE.semver("0.9.0"), MODULE.semver("0.10.0"))

    def test_plugin_versions_reports_absent_when_no_plugin_root(self):
        original = MODULE.PLUGIN_ROOT
        try:
            MODULE.PLUGIN_ROOT = "/nonexistent-plugin-root-for-test"
            self.assertEqual(MODULE.plugin_versions()["state"], "absent")
        finally:
            MODULE.PLUGIN_ROOT = original


if __name__ == "__main__":
    unittest.main()
