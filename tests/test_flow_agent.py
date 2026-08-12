import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "plugins/devflow/scripts/flow-agent.py"
SPEC = importlib.util.spec_from_file_location("flow_agent", BRIDGE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


GOOD = {
    "status": "COMPLETED", "summary": "done", "artifacts": ["result.md"],
    "completed": ["abc123"], "checkpoint": None, "error": None,
}


class FlowAgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        (self.repo / ".git").mkdir(parents=True)
        self.prompt = self.base / "prompt.md"
        self.prompt.write_text("Do the bounded role.", encoding="utf-8")
        self.bin = self.base / "bin"
        self.bin.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def fake(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def run_bridge(self, provider, role, extra_env=None):
        env = os.environ.copy()
        env["PATH"] = str(self.bin) + os.pathsep + env.get("PATH", "")
        env.update(extra_env or {})
        run = subprocess.run(
            [sys.executable, str(BRIDGE), "--provider", provider, "--role", role,
             "--repo", str(self.repo), "--prompt-file", str(self.prompt)],
            text=True, capture_output=True, env=env,
        )
        return run, json.loads(run.stdout)

    def test_codex_read_only_and_structured_result(self):
        result = json.dumps(GOOD).replace("'", "'\\''")
        self.fake("codex", f"printf '%s' '{result}'")
        run, value = self.run_bridge("codex", "reviewer")
        self.assertEqual(0, run.returncode)
        self.assertEqual(GOOD, value)

    def test_claude_write_result_envelope(self):
        outer = json.dumps({"structured_output": GOOD}).replace("'", "'\\''")
        self.fake("claude", f"printf '%s' '{outer}'")
        run, value = self.run_bridge("claude", "executor")
        self.assertEqual(0, run.returncode)
        self.assertEqual(GOOD, value)

    def test_missing_binary_fails_closed(self):
        run, value = self.run_bridge("codex", "reviewer", {"PATH": str(self.bin)})
        self.assertNotEqual(0, run.returncode)
        self.assertEqual("FAILED", value["status"])
        self.assertIn("not installed", value["error"])

    def test_nonzero_exit_does_not_echo_stderr(self):
        self.fake("claude", "echo 'secret repository context' >&2\nexit 7")
        run, value = self.run_bridge("claude", "planner")
        self.assertNotEqual(0, run.returncode)
        self.assertNotIn("secret repository context", run.stdout + run.stderr)
        self.assertIn("status 7", value["error"])

    def test_malformed_output_fails_closed(self):
        self.fake("codex", "printf 'not-json'")
        run, value = self.run_bridge("codex", "mapper")
        self.assertNotEqual(0, run.returncode)
        self.assertIn("malformed", value["error"])

    def test_commands_never_bypass_permissions(self):
        schema = self.base / "schema.json"
        codex = MODULE.build_command("codex", "executor", self.repo, "task", schema)
        claude = MODULE.build_command("claude", "reviewer", self.repo, "task", schema)
        command = " ".join(codex + claude)
        self.assertNotIn("dangerously", command)
        self.assertNotIn("yolo", command)
        self.assertIn("workspace-write", codex)
        self.assertIn("plan", claude)

    def test_provider_precedence_and_native_resolution(self):
        self.assertEqual("codex", MODULE.resolve_provider(None, None, "codex"))
        self.assertEqual("claude", MODULE.resolve_provider(None, "claude", "codex"))
        self.assertEqual("codex", MODULE.resolve_provider("codex", "claude", "claude"))
        with self.assertRaises(ValueError):
            MODULE.resolve_provider(None, "other", "codex")


if __name__ == "__main__":
    unittest.main()
