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

    def config(self, provider):
        planning = self.repo / ".planning"
        planning.mkdir(exist_ok=True)
        (planning / "config.json").write_text(
            json.dumps({"agents": {"provider": provider}}), encoding="utf-8")

    def run_bridge(self, provider, role, extra_env=None, host=None, stdin=""):
        env = os.environ.copy()
        env["PATH"] = str(self.bin) + os.pathsep + env.get("PATH", "")
        env.update(extra_env or {})
        # Default the host to the other CLI so the bridge is genuinely cross-provider.
        host = host or ("claude" if provider == "codex" else "codex")
        command = [sys.executable, str(BRIDGE), "--host", host, "--role", role,
                   "--repo", str(self.repo), "--prompt-file", str(self.prompt)]
        if provider is not None:
            command += ["--provider", provider]
        run = subprocess.run(command, text=True, capture_output=True, env=env, input=stdin)
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

    def test_model_is_passed_through_and_optional(self):
        schema = self.base / "schema.json"
        for provider in ("codex", "claude"):
            plain = MODULE.build_command(provider, "executor", self.repo, "task", schema)
            self.assertNotIn("--model", plain)
            tiered = MODULE.build_command(provider, "executor", self.repo, "task",
                                          schema, "some-model")
            self.assertEqual("some-model", tiered[tiered.index("--model") + 1])
            # The prompt must stay last: codex exec takes it positionally.
            self.assertEqual(plain[-1], tiered[-1])

    def test_provider_precedence_and_native_resolution(self):
        self.assertEqual("codex", MODULE.resolve_provider(None, None, "codex"))
        self.assertEqual("claude", MODULE.resolve_provider(None, "claude", "codex"))
        self.assertEqual("codex", MODULE.resolve_provider("codex", "claude", "claude"))
        with self.assertRaises(ValueError):
            MODULE.resolve_provider(None, "other", "codex")

    def test_project_config_supplies_provider_when_flag_omitted(self):
        self.config("codex")
        self.fake("codex", f"printf '%s' '{json.dumps(GOOD)}'")
        run, value = self.run_bridge(None, "reviewer", host="claude")
        self.assertEqual(0, run.returncode)
        self.assertEqual(GOOD, value)

    def test_command_flag_overrides_project_config(self):
        self.config("codex")
        outer = json.dumps({"structured_output": GOOD})
        self.fake("claude", f"printf '%s' '{outer}'")
        run, value = self.run_bridge("claude", "reviewer", host="codex")
        self.assertEqual(0, run.returncode)
        self.assertEqual(GOOD, value)

    def test_native_never_starts_a_second_cli(self):
        # Both the explicit flag and the bare default resolve to the host.
        for provider in (None, "native"):
            run, value = self.run_bridge(provider, "reviewer", host="codex")
            self.assertNotEqual(0, run.returncode)
            self.assertIn("spawn an in-host agent", value["error"])

    def test_malformed_project_config_is_ignored(self):
        planning = self.repo / ".planning"
        planning.mkdir(exist_ok=True)
        (planning / "config.json").write_text("{not json", encoding="utf-8")
        run, value = self.run_bridge(None, "reviewer", host="codex")
        self.assertIn("spawn an in-host agent", value["error"])

    def test_peer_stdin_is_closed(self):
        # codex exec consumes a non-TTY stdin; a leaked pipe would block until timeout.
        result = json.dumps(GOOD).replace("'", "'\\''")
        self.fake("codex", f"if read leaked; then printf 'LEAKED'; "
                           f"else printf '%s' '{result}'; fi")
        run, value = self.run_bridge("codex", "reviewer", stdin="leaked data\n")
        self.assertEqual(0, run.returncode)
        self.assertEqual(GOOD, value)


@unittest.skipUnless(os.environ.get("DEVFLOW_SMOKE") == "1",
                     "set DEVFLOW_SMOKE=1 to run real-CLI smoke tests (costs tokens)")
class BridgeSmokeTests(unittest.TestCase):
    """Exercise the real CLIs.

    The mocked tests above pin our own contract but cannot catch provider CLI
    drift — flag renames, output-envelope changes, or stdin handling. Opt-in
    because each case spends real tokens.
    """

    # Must be real, verifiable work. An earlier version asked the peer to report a
    # canned success; a capable model correctly refused to fabricate one, so the
    # test measured compliance rather than the bridge.
    PROMPT = ("Check whether a README.md file exists at the root of this repository. "
              "Return status COMPLETED, summary stating what you found, artifacts "
              "listing README.md if it is present, an empty completed array, and "
              "null checkpoint and error.")

    def bridge(self, provider, host, timeout=300):
        import shutil
        if shutil.which(provider) is None:
            self.skipTest(f"{provider} CLI is not installed")
        with tempfile.TemporaryDirectory() as temp:
            prompt = Path(temp) / "prompt.md"
            prompt.write_text(self.PROMPT, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(BRIDGE), "--host", host, "--provider", provider,
                 "--role", "reviewer", "--repo", str(ROOT),
                 "--prompt-file", str(prompt), "--timeout", str(timeout)],
                text=True, capture_output=True, timeout=timeout + 60,
                # Deliberately an open pipe: a bridge that leaks stdin hangs here.
                input="",
            )

    def assert_valid(self, run):
        self.assertEqual(0, run.returncode, run.stdout + run.stderr)
        value = MODULE.validate_result(json.loads(run.stdout))
        self.assertIsNotNone(value, f"schema drift: {run.stdout}")
        self.assertEqual("COMPLETED", value["status"])

    def test_real_codex_peer(self):
        self.assert_valid(self.bridge("codex", "claude"))

    def test_real_claude_peer(self):
        self.assert_valid(self.bridge("claude", "codex"))


if __name__ == "__main__":
    unittest.main()
