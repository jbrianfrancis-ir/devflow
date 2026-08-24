"""Tests for the fleet scanner's parsing and its fail-closed guarantees.

The scanner is the only thing an outside driver reads, so its two promises are
load-bearing: the `## Gate` block reaches a caller as structured data (the one
exception to "never parse skill prose"), and a check that could not run is never
reported as clean (references/conventions.md → Fail-closed guards).
"""
import contextlib
import datetime
import importlib.util
import os
import shutil
import time
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
# scan() takes `versions` explicitly — there is no default, so a caller can
# never silently report version-clean. Tests that are not about versions pass
# this: "no Claude plugin system here", which flags nothing.
NO_VERSIONS = {"by_path": {}, "user": None, "latest": None, "state": "absent",
               "cache_commit": None, "cache_age_days": None}


@contextlib.contextmanager
def no_plugin_registry():
    """Pin plugin_versions() to "absent" for the duration.

    main() reads the host's ~/.claude/plugins. Without this, a scanner test
    asserts on the developer's machine: a host whose registry is missing or
    unparseable yields VER-UNKNOWN on every project, which sets needs_human and
    flips main()'s exit status. The suite passed here only because this box's
    registry happens to parse — the same class of environment leak the T2 notes
    below already guard against for ~/.devflow/fleet.json.
    """
    original = MODULE.PLUGIN_ROOT
    MODULE.PLUGIN_ROOT = "/nonexistent-plugin-root-for-test"
    try:
        yield
    finally:
        MODULE.PLUGIN_ROOT = original


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
        return MODULE.scan(str(d), datetime.date(2026, 8, 15), 3, NO_VERSIONS)

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
        with redirect_stdout(io.StringIO()), no_plugin_registry():
            # T2: --stale-days pinned explicitly so this doesn't depend on
            # the developer's ~/.devflow/fleet.json (main() falls back to it
            # when the flag is absent). T3: the plugin registry is pinned for
            # the same reason — see no_plugin_registry().
            code = MODULE.main([str(self.base), "--json", "--depth", "2", "--stale-days", "3"])
        self.assertEqual(code, 1)

    def test_exit_status_is_zero_when_everything_is_fine(self):
        state = POSITION + "\n## Gate\nnone\n" + RUN_BLOCK.replace("Repeats: 2", "Repeats: 0") + BLOCKERS_NONE
        self.project("clean", state, journal="- %s | /flow-execute | phase 3 | CONTINUE" % TODAY)
        buf = io.StringIO()
        with redirect_stdout(buf), no_plugin_registry():
            # T2/T3: see above — pinned so neither a host config of e.g.
            # stale_days: 0 nor an unparseable plugin registry can turn a
            # "clean" fixture into a non-zero exit.
            code = MODULE.main([str(self.base), "--json", "--depth", "2", "--stale-days", "3"])
        self.assertEqual(code, 0, buf.getvalue())
        envelope = json.loads(buf.getvalue())
        # docs/status-contract.md documents this envelope key; without an
        # assertion the documented machine-readable contract can regress silently.
        self.assertIn("plugin_versions", envelope)
        self.assertEqual(envelope["plugin_versions"]["state"], "absent")




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
            # git init so git_readable is True: without it GIT-UNKNOWN sets
            # needs_human on its own and any assertion about VER-UNKNOWN's
            # contribution passes vacuously.
            subprocess.run(["git", "init", "-q", str(path)], capture_output=True)
            if project_version is not None:
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


class MarketplaceCacheFreshnessTests(unittest.TestCase):
    """The other half of staleness: how much `latest` is actually worth.

    The marketplace cache is a git clone that only moves when Claude Code
    refreshes it, so a release can be tagged and public while every local
    reading still reports the old number — which is how 0.15.0 stayed invisible
    on this machine after it shipped. The scanner never fetches, so it cannot
    say "you are behind"; it says how old the reading is and lets that speak.
    """

    PROJECT = {
        "repo": "a/b", "branch": "main", "phase": "1/1", "plans": "", "status": "verified",
        "flow": "CONTINUE", "age_days": 0, "flags": [], "next": "/flow-pr",
        "needs_human": False, "devflow_version": "0.14.1", "blockers": [], "gate": None,
        "run": None, "git_readable": True, "dirty": 0, "path": "/x", "worktree": False,
    }

    def render_with(self, **cache):
        versions = {"state": "ok", "latest": "0.15.0", "user": "0.15.0",
                    "cache_commit": "1d1c398", "cache_age_days": 0}
        versions.update(cache)
        return MODULE.render([dict(self.PROJECT)], 3, versions)

    def test_fresh_cache_does_not_nag(self):
        out = self.render_with(cache_age_days=0)
        self.assertIn("refreshed today", out)
        self.assertNotIn("marketplace update", out)

    def test_stale_cache_names_the_refresh_command(self):
        out = self.render_with(cache_age_days=9)
        self.assertIn("refreshed 9d ago", out)
        self.assertIn("claude plugin marketplace update devflow", out)

    def test_never_fetched_is_not_reported_as_fresh(self):
        out = self.render_with(cache_age_days=None)
        self.assertIn("no usable fetch record", out)
        self.assertIn("claude plugin marketplace update devflow", out)

    def test_threshold_follows_stale_days(self):
        versions = {"state": "ok", "latest": "0.15.0", "user": "0.15.0",
                    "cache_commit": "1d1c398", "cache_age_days": 4}
        self.assertNotIn("marketplace update", MODULE.render([dict(self.PROJECT)], 7, versions))
        self.assertIn("marketplace update", MODULE.render([dict(self.PROJECT)], 3, versions))

    def test_cache_commit_is_shown_so_a_reading_can_be_traced(self):
        self.assertIn("1d1c398", self.render_with(cache_age_days=2))

    def test_absent_plugin_system_reports_no_cache_fields(self):
        original = MODULE.PLUGIN_ROOT
        try:
            MODULE.PLUGIN_ROOT = "/nonexistent-plugin-root-for-test"
            v = MODULE.plugin_versions()
            self.assertEqual(v["state"], "absent")
            self.assertIsNone(v["cache_age_days"])
            self.assertIsNone(v["cache_commit"])
        finally:
            MODULE.PLUGIN_ROOT = original




class PluginVersionComparisonTests(unittest.TestCase):
    """The comparison site itself, not just the semver() helper.

    Every earlier case (0.12.0 vs 0.15.0, 0.15.0 vs 0.15.0) orders the same
    lexically as numerically, so comparing raw strings at the call site passed
    the whole suite. 0.9.0 vs 0.10.0 is the case that separates them.
    """

    def scan_with(self, pin, latest):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proj"
            (path / ".planning").mkdir(parents=True)
            (path / ".planning" / "STATE.md").write_text(
                "# State\n\n## Position\nPhase: 1 of 1 | Plans: 1/1 | Status: verified\n"
                "Next: /flow-pr\nLast: %s — ok\n\n## Gate\nnone\n\n## Blockers\n- none\n" % TODAY,
                encoding="utf-8")
            (path / ".planning" / "JOURNAL.md").write_text(
                "# Journal\n- %s | /flow-plan 1 | done | CONTINUE\n" % TODAY, encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(path)], capture_output=True)
            versions = {"by_path": {str(path.resolve()): pin}, "user": None,
                        "latest": latest, "state": "ok"}
            return MODULE.scan(str(path), datetime.date.today(), 3, versions)

    def test_nine_is_older_than_ten(self):
        # Lexically "0.9.0" > "0.10.0"; numerically it is not.
        self.assertIn("OLD-PLUGIN", self.scan_with("0.9.0", "0.10.0")["flags"])

    def test_unparseable_pin_is_unknown_not_clean(self):
        p = self.scan_with("0.15", "0.15.0")
        self.assertIn("VER-UNKNOWN", p["flags"])
        self.assertNotIn("OLD-PLUGIN", p["flags"])

    def test_unparseable_pin_does_not_crash_the_scan(self):
        # It compared semver(pin) < semver(latest) guarded on the raw strings,
        # so a non-semver pin raised TypeError and took the whole board down.
        for pin in ("0.15", "0.16.0-rc.1", "main", ""):
            self.scan_with(pin, "0.15.0")


class PluginRegistryReadingTests(unittest.TestCase):
    """plugin_versions() against real files, not a hand-built dict.

    Every other test hands scan()/render() a synthetic versions mapping, so the
    whole reading path — scopes, latest, the manifest merge, FETCH_HEAD — was
    unexercised: reversing max() to min(), dropping the user scope, or hardcoding
    cache_age_days all left the suite green.
    """

    def build(self, registry=None, manifest=None, fetch_head_age_days=None):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = Path(tmp) / "plugins"
        (root / "marketplaces" / "devflow" / ".claude-plugin").mkdir(parents=True)
        (root / "marketplaces" / "devflow" / ".git").mkdir(parents=True)
        if registry is not None:
            (root / "installed_plugins.json").write_text(json.dumps(registry), encoding="utf-8")
        if manifest is not None:
            (root / "marketplaces" / "devflow" / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps(manifest), encoding="utf-8")
        if fetch_head_age_days is not None:
            fh = root / "marketplaces" / "devflow" / ".git" / "FETCH_HEAD"
            fh.write_text("x", encoding="utf-8")
            when = time.time() - fetch_head_age_days * 86400
            os.utime(fh, (when, when))
        for name, value in (("PLUGIN_ROOT", str(root)),
                            ("INSTALLED_PLUGINS", str(root / "installed_plugins.json")),
                            ("MARKETPLACE_MANIFEST", str(root / "marketplaces" / "devflow" /
                                                         ".claude-plugin" / "marketplace.json")),
                            ("MARKETPLACE_CACHE", str(root / "marketplaces" / "devflow"))):
            original = getattr(MODULE, name)
            setattr(MODULE, name, value)
            self.addCleanup(setattr, MODULE, name, original)
        return MODULE.plugin_versions()

    REGISTRY = {"version": 2, "plugins": {"devflow@devflow": [
        {"scope": "user", "version": "0.14.1"},
        {"scope": "project", "projectPath": "/somewhere/app", "version": "0.12.0"},
    ]}}

    def test_reads_both_scopes(self):
        v = self.build(registry=self.REGISTRY)
        self.assertEqual(v["user"], "0.14.1")
        self.assertEqual(v["by_path"][os.path.realpath("/somewhere/app")], "0.12.0")

    def test_latest_is_the_highest_not_the_lowest(self):
        self.assertEqual(self.build(registry=self.REGISTRY)["latest"], "0.14.1")

    def test_manifest_raises_latest_above_every_pin(self):
        v = self.build(registry=self.REGISTRY,
                       manifest={"plugins": [{"name": "devflow", "version": "0.15.0"}]})
        self.assertEqual(v["latest"], "0.15.0")

    def test_cache_age_comes_from_fetch_head(self):
        v = self.build(registry=self.REGISTRY, fetch_head_age_days=6)
        self.assertEqual(v["cache_age_days"], 6)

    def test_no_fetch_head_is_none_not_zero(self):
        self.assertIsNone(self.build(registry=self.REGISTRY)["cache_age_days"])

    def test_future_fetch_head_is_unknown_not_today(self):
        # A clock moved back or a restored tree must not read as the freshest
        # possible cache.
        self.assertIsNone(self.build(registry=self.REGISTRY, fetch_head_age_days=-5)["cache_age_days"])

    def test_missing_registry_is_absent(self):
        self.assertEqual(self.build()["state"], "absent")

    def test_corrupt_registry_is_unreadable(self):
        v = self.build(registry=None)
        root = Path(MODULE.INSTALLED_PLUGINS)
        root.write_text("{not json", encoding="utf-8")
        self.assertEqual(MODULE.plugin_versions()["state"], "unreadable")

    def test_wrong_top_level_shape_is_unreadable_not_empty(self):
        # Parses fine, means nothing: reporting "ok, nothing registered" for a
        # file we failed to understand is the fail-open this guard prevents.
        for payload in ([], {"plugins": "none"}, {"plugins": []}):
            self.assertEqual(self.build(registry=payload)["state"], "unreadable", payload)

    def test_unknown_entry_shapes_are_tolerated(self):
        # The file carries a schema version and may grow fields; an unknown
        # entry shape is skipped, not treated as corruption.
        v = self.build(registry={"plugins": {"devflow@devflow": [
            "a string", {"scope": "user", "version": "0.15.0"}]}})
        self.assertEqual(v["state"], "ok")
        self.assertEqual(v["user"], "0.15.0")


if __name__ == "__main__":
    unittest.main()
