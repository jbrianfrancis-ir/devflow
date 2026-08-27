import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = ROOT / "plugins/devflow/templates/hooks"
CONVENTIONS = ROOT / "plugins/devflow/references/conventions.md"

BASE_BRANCH_GUARD = HOOKS_DIR / "base-branch-guard.py"
PROTECTED_PATHS_GUARD = HOOKS_DIR / "protected-paths-guard.py"
SECRET_SCAN_GUARD = HOOKS_DIR / "secret-scan-guard.py"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_hook(script, payload, env=None):
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=full_env,
    )


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout


class GitFixture:
    """A scratch git repo with a `.planning/config.json` (`git.base`) and one commit."""

    def __init__(self, base="main", protected_paths=None):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        git(self.repo, "init", "-q", "-b", base)
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "test")
        (self.repo / ".planning").mkdir()
        config = {"git": {"base": base}}
        if protected_paths is not None:
            config["protected_paths"] = protected_paths
        (self.repo / ".planning" / "config.json").write_text(
            json.dumps(config), encoding="utf-8")
        (self.repo / "f.txt").write_text("hello\n", encoding="utf-8")
        git(self.repo, "add", "f.txt", ".planning/config.json")
        git(self.repo, "commit", "-q", "-m", "init")

    def checkout(self, branch):
        git(self.repo, "checkout", "-q", "-b", branch)

    def append_and_stage(self, line):
        with (self.repo / "f.txt").open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
        git(self.repo, "add", "f.txt")

    def cleanup(self):
        self.tempdir.cleanup()


class BaseBranchGuardTests(unittest.TestCase):
    def setUp(self):
        self.fixture = GitFixture()
        self.addCleanup(self.fixture.cleanup)

    def test_blocks_commit_on_base_branch(self):
        result = run_hook(BASE_BRANCH_GUARD, {
            "tool_input": {"command": "git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)

    def test_blocks_push_on_base_branch(self):
        result = run_hook(BASE_BRANCH_GUARD, {
            "tool_input": {"command": "git push origin main"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)

    def test_allows_commit_on_feature_branch(self):
        self.fixture.checkout("flow/test")
        result = run_hook(BASE_BRANCH_GUARD, {
            "tool_input": {"command": "git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(0, result.returncode)

    def test_allows_non_git_command(self):
        result = run_hook(BASE_BRANCH_GUARD, {
            "tool_input": {"command": "ls -la"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(0, result.returncode)

    def test_fails_open_when_not_a_git_repo(self):
        with tempfile.TemporaryDirectory() as scratch:
            result = run_hook(BASE_BRANCH_GUARD, {
                "tool_input": {"command": "git commit -m x"},
                "cwd": scratch,
            })
            self.assertEqual(0, result.returncode)
            self.assertTrue(result.stderr.strip())

    def test_blocks_on_fallback_base_when_no_config(self):
        # No .planning/config.json at all — falls back to checking the branch name against
        # {"main", "master"} directly.
        with tempfile.TemporaryDirectory() as scratch:
            git(scratch, "init", "-q", "-b", "main")
            git(scratch, "config", "user.email", "test@example.com")
            git(scratch, "config", "user.name", "test")
            (Path(scratch) / "f.txt").write_text("hello\n", encoding="utf-8")
            git(scratch, "add", "f.txt")
            git(scratch, "commit", "-q", "-m", "init")
            result = run_hook(BASE_BRANCH_GUARD, {
                "tool_input": {"command": "git commit -m x"},
                "cwd": scratch,
            })
            self.assertEqual(2, result.returncode)
            self.assertIn("Blocked", result.stderr)


class ProtectedPathsGuardTests(unittest.TestCase):
    def setUp(self):
        self.fixture = GitFixture(protected_paths=["src/prod.env", "*.pem"])
        self.addCleanup(self.fixture.cleanup)

    def test_blocks_matching_path_without_env(self):
        target = str(self.fixture.repo / "src" / "prod.env")
        result = run_hook(PROTECTED_PATHS_GUARD, {
            "tool_input": {"file_path": target},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)

    def test_allows_matching_path_with_env_set(self):
        target = str(self.fixture.repo / "src" / "prod.env")
        result = run_hook(PROTECTED_PATHS_GUARD, {
            "tool_input": {"file_path": target},
            "cwd": str(self.fixture.repo),
        }, env={"DEVFLOW_PROTECTED_PATH_OK": "1"})
        self.assertEqual(0, result.returncode)

    def test_allows_non_matching_path(self):
        target = str(self.fixture.repo / "src" / "other.txt")
        result = run_hook(PROTECTED_PATHS_GUARD, {
            "tool_input": {"file_path": target},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(0, result.returncode)

    def test_allows_when_no_protected_paths_configured(self):
        fixture = GitFixture()
        self.addCleanup(fixture.cleanup)
        target = str(fixture.repo / "anything.txt")
        result = run_hook(PROTECTED_PATHS_GUARD, {
            "tool_input": {"file_path": target},
            "cwd": str(fixture.repo),
        })
        self.assertEqual(0, result.returncode)

    def test_blocks_glob_matching_path(self):
        target = str(self.fixture.repo / "certs" / "server.pem")
        result = run_hook(PROTECTED_PATHS_GUARD, {
            "tool_input": {"file_path": target},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)

    def test_blocks_unnormalized_path_that_matches_after_normalization(self):
        target = str(self.fixture.repo / "sub" / ".." / "src" / "prod.env")
        result = run_hook(PROTECTED_PATHS_GUARD, {
            "tool_input": {"file_path": target},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)

    def test_fails_open_on_malformed_config(self):
        (self.fixture.repo / ".planning" / "config.json").write_text(
            "{not json", encoding="utf-8")
        target = str(self.fixture.repo / "src" / "prod.env")
        result = run_hook(PROTECTED_PATHS_GUARD, {
            "tool_input": {"file_path": target},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(0, result.returncode)
        self.assertTrue(result.stderr.strip())

    def test_blocks_symlink_resolving_to_a_protected_path(self):
        # Regression: a symlink whose literal path doesn't match a protected glob but whose
        # resolved target does must still be caught — the write follows the link.
        real_target = self.fixture.repo / "src" / "prod.env"
        link = self.fixture.repo / "link_to_prod_env"
        link.symlink_to(real_target)
        result = run_hook(PROTECTED_PATHS_GUARD, {
            "tool_input": {"file_path": str(link)},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)


class SecretScanGuardTests(unittest.TestCase):
    def setUp(self):
        self.fixture = GitFixture()
        self.addCleanup(self.fixture.cleanup)

    def test_blocks_staged_secret_pattern(self):
        # Built at runtime (not a single-line literal) so this repo's own conventions.md
        # secret scan doesn't flag the test fixture as a real hit when this file is committed.
        fixture_line = "api_key" + ' = "' + "abcd1234efgh5678" + '"'
        self.fixture.append_and_stage(fixture_line)
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)
        self.assertNotIn("abcd1234efgh5678", result.stderr)

    def test_blocks_added_env_file_regardless_of_content(self):
        (self.fixture.repo / ".env").write_text("NOT_A_SECRET=1\n", encoding="utf-8")
        git(self.fixture.repo, "add", ".env")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)

    def test_allows_clean_diff(self):
        self.fixture.append_and_stage("clean addition")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(0, result.returncode)

    def test_allows_non_git_command(self):
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "ls -la"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(0, result.returncode)

    def test_fails_open_when_not_a_git_repo(self):
        with tempfile.TemporaryDirectory() as scratch:
            result = run_hook(SECRET_SCAN_GUARD, {
                "tool_input": {"command": "git commit -m x"},
                "cwd": scratch,
            })
            self.assertEqual(0, result.returncode)
            self.assertTrue(result.stderr.strip())

    def test_blocks_secret_on_push(self):
        self.fixture.checkout("flow/test")
        fixture_line = "api_key" + ' = "' + "abcd1234efgh5678" + '"'
        self.fixture.append_and_stage(fixture_line)
        git(self.fixture.repo, "commit", "-q", "-m", "wip")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git push origin flow/test"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)

    def test_blocks_secret_on_push_with_master_fallback_when_no_config(self):
        # No .planning/config.json at all — falls back through common.resolve_diff_base to
        # whichever of {main, master} actually exists as a ref, not a hardcoded "main".
        with tempfile.TemporaryDirectory() as scratch:
            git(scratch, "init", "-q", "-b", "master")
            git(scratch, "config", "user.email", "test@example.com")
            git(scratch, "config", "user.name", "test")
            (Path(scratch) / "f.txt").write_text("hello\n", encoding="utf-8")
            git(scratch, "add", "f.txt")
            git(scratch, "commit", "-q", "-m", "init")
            git(scratch, "checkout", "-q", "-b", "flow/test")
            fixture_line = "api_key" + ' = "' + "abcd1234efgh5678" + '"'
            with (Path(scratch) / "f.txt").open("a", encoding="utf-8") as stream:
                stream.write(fixture_line + "\n")
            git(scratch, "add", "f.txt")
            git(scratch, "commit", "-q", "-m", "wip")
            result = run_hook(SECRET_SCAN_GUARD, {
                "tool_input": {"command": "git push origin flow/test"},
                "cwd": scratch,
            })
            self.assertEqual(2, result.returncode)
            self.assertIn("Blocked", result.stderr)

    def test_blocks_unstaged_secret_on_commit_dash_a(self):
        # Regression: git commit -a/-am commits unstaged tracked-file changes, which a
        # `--cached`-only diff never sees. Nothing is staged here on purpose.
        fixture_line = "api_key" + ' = "' + "abcd1234efgh5678" + '"'
        with (self.fixture.repo / "f.txt").open("a", encoding="utf-8") as stream:
            stream.write(fixture_line + "\n")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -am x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)

    def test_blocks_binary_credential_file(self):
        # Regression: a real binary .pfx/.pem emits no `+++`/`+` hunk lines at all (just
        # "Binary files ... differ"), so detection must key off that line, not `+++`/`+`.
        (self.fixture.repo / "cert.pfx").write_bytes(bytes(range(256)))
        git(self.fixture.repo, "add", "cert.pfx")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)

    def test_allows_deleting_a_binary_credential_file(self):
        # Regression: the binary-file fix above must not fire on a pure deletion (the
        # "Binary files a/x and /dev/null differ" case) — removing a leaked credential file
        # is remediation, not a new hit, and must not be blocked.
        (self.fixture.repo / "cert.pfx").write_bytes(bytes(range(256)))
        git(self.fixture.repo, "add", "cert.pfx")
        git(self.fixture.repo, "commit", "-q", "-m", "add cert")
        git(self.fixture.repo, "rm", "-q", "cert.pfx")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(0, result.returncode)

    def test_blocks_new_untracked_file_added_and_committed_in_one_command(self):
        # Regression: `git add x && git commit` in a single Bash call stages and commits x
        # before the hook's own diff-against-HEAD would ever see it (x has no tracked
        # history yet) — must be caught by scanning untracked candidates directly.
        # Blocked on filename alone (id_rsa* is a credential-shaped glob) — content doesn't
        # need to look like a real key, so no fixture string can trip this repo's own
        # conventions.md secret scan when this test file itself is committed.
        (self.fixture.repo / "id_rsa").write_text("not a real key, just a name\n", encoding="utf-8")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git add id_rsa && git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)

    def test_blocks_new_untracked_file_added_with_add_all(self):
        (self.fixture.repo / "id_rsa").write_text("secret key material\n", encoding="utf-8")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git add -A && git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)

    def test_blocks_unrelated_untracked_credential_file_whenever_git_add_present(self):
        # Deliberate over-blocking, by design: scanning is intentionally conservative
        # (whenever `git add` appears anywhere in the command, every untracked file is a
        # candidate) rather than trying to compute exactly which files this invocation
        # targets — see scan_new_untracked_files's docstring for why the narrower version
        # was unsafe.
        (self.fixture.repo / "id_rsa").write_text("not a real key, just a name\n", encoding="utf-8")
        self.fixture.append_and_stage("clean addition")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git add f.txt && git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)

    def test_blocks_glob_expanded_add_target(self):
        # Regression: a literal-token match on `git add` args can't see through a shell glob
        # — verified live to bypass an earlier version of this check.
        (self.fixture.repo / "secret1.pem").write_text("not a real key\n", encoding="utf-8")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git add secret*.pem && git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)

    def test_blocks_variable_expanded_add_target(self):
        # Regression: same bypass class as the glob case, via a shell variable instead.
        (self.fixture.repo / "id_rsa").write_text("not a real key\n", encoding="utf-8")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "F=id_rsa; git add $F && git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)

    def test_blocks_newline_separated_add_and_commit(self):
        # Regression: an earlier version only split chained statements on &&/;/||, so an
        # add and commit on separate lines of the same Bash command evaded it entirely.
        (self.fixture.repo / "id_rsa").write_text("not a real key\n", encoding="utf-8")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "echo preparing\ngit add id_rsa\ngit commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)

    def test_blocks_empty_credential_shaped_file(self):
        # Regression: a 0-byte credential-shaped file emits only a `diff --git`/`new file
        # mode` header — no `+++`/`+`/binary-differ line at all — so detection must not
        # depend on any content-bearing line existing.
        (self.fixture.repo / "id_rsa").touch()
        git(self.fixture.repo, "add", "id_rsa")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)

    def test_allows_deleting_a_text_credential_file(self):
        (self.fixture.repo / ".env").write_text("NOT_A_SECRET=1\n", encoding="utf-8")
        git(self.fixture.repo, "add", ".env")
        git(self.fixture.repo, "commit", "-q", "-m", "add env")
        git(self.fixture.repo, "rm", "-q", ".env")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(0, result.returncode)


class SecretPatternDriftTest(unittest.TestCase):
    """The regex embedded in secret-scan-guard.py must stay byte-identical to the one
    documented in conventions.md's "Secret scan (fail-closed)" section — a test, not a
    comment, so the two copies cannot drift silently."""

    def test_embedded_pattern_matches_conventions_md(self):
        text = CONVENTIONS.read_text(encoding="utf-8")
        _, _, section = text.partition("## Secret scan (fail-closed)")
        self.assertTrue(section, "conventions.md: 'Secret scan (fail-closed)' section not found")
        match = re.search(r"```\n(.+?)\n```", section, re.S)
        self.assertIsNotNone(match, "conventions.md: fenced secret-scan pattern not found")
        documented_pattern = match.group(1)

        module = load_module(SECRET_SCAN_GUARD, "secret_scan_guard")
        self.assertEqual(documented_pattern, module.SECRET_PATTERN)


if __name__ == "__main__":
    unittest.main()
