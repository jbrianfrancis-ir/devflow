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
DEPENDENCY_GUARD = HOOKS_DIR / "dependency-guard.py"
DESTRUCTIVE_GIT_GUARD = HOOKS_DIR / "destructive-git-guard.py"


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

    def test_blocks_staged_secret_with_mnemonic_prefix_config(self):
        # Regression for the live fail-open: diff.mnemonicPrefix=true makes git emit
        # `diff --git c/file w/file` instead of `a/`/`b/`. DIFF_GIT_HEADER_RE only matched
        # the default shape, iter_file_chunks yielded zero chunks, and the guard exited 0
        # (allow) on a staged secret with no warning. The guard must pin the prefixes so
        # this config can't change the diff shape it depends on.
        git(self.fixture.repo, "config", "diff.mnemonicPrefix", "true")
        fixture_line = "api_key" + ' = "' + "abcd1234efgh5678" + '"'
        self.fixture.append_and_stage(fixture_line)
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)
        self.assertNotIn("abcd1234efgh5678", result.stderr)
        # Must be the real hit (the diff was parsed and the pattern matched), not the
        # could-not-parse fallback also exiting 2 for an unrelated reason — a guard that
        # merely fails closed on every unparseable diff would pass this test without the
        # prefix pinning actually working.
        self.assertIn("pattern:", result.stderr)
        self.assertNotIn("could not parse", result.stderr)

    def _assert_real_hit(self, result):
        """Exit 2 via the pattern match, not via the could-not-parse fallback.

        The fallback also exits 2, so asserting only the exit code would let a guard that
        understands nothing pass every one of these tests — the vacuous negative control
        this whole rule set exists to prevent.
        """
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)
        self.assertIn("pattern:", result.stderr)
        self.assertNotIn("could not parse", result.stderr)
        self.assertNotIn("abcd1234efgh5678", result.stderr)

    def _stage_secret(self):
        self.fixture.append_and_stage("api_key" + ' = "' + "abcd1234efgh5678" + '"')

    def _write_forbidden_architecture(self, pattern, prose="a forbidden fixture entry"):
        """Write `.planning/ARCHITECTURE.md` with one `## Forbidden` bullet ending in the
        `templates/architecture.md`-documented " <dash> pattern: `<regex>`" suffix."""
        arch_dir = self.fixture.repo / ".planning"
        arch_dir.mkdir(exist_ok=True)
        (arch_dir / "ARCHITECTURE.md").write_text(
            f"## Forbidden\n- {prose} — pattern: `{pattern}`\n", encoding="utf-8")

    def test_blocks_secret_in_a_path_marked_minus_diff(self):
        # `-diff` renders the file as "Binary files ... differ": the chunk parses fine, so
        # COULD_NOT_PARSE never fires, and the added lines are simply never scanned. Fail
        # open, silently. `--text` closes it.
        (self.fixture.repo / ".gitattributes").write_text("*.txt -diff\n", encoding="utf-8")
        git(self.fixture.repo, "add", ".gitattributes")
        self._stage_secret()
        self._assert_real_hit(run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"}, "cwd": str(self.fixture.repo)}))

    def test_blocks_secret_behind_a_textconv_filter(self):
        # A textconv filter rewrites content before the scan sees it. `--no-textconv`.
        (self.fixture.repo / ".gitattributes").write_text("*.txt diff=redact\n", encoding="utf-8")
        git(self.fixture.repo, "add", ".gitattributes")
        git(self.fixture.repo, "config", "diff.redact.textconv", "sed -e s/./X/g")
        self._stage_secret()
        self._assert_real_hit(run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"}, "cwd": str(self.fixture.repo)}))

    def test_blocks_secret_with_color_ui_always(self):
        # color.ui=always wraps the header in escapes so DIFF_GIT_HEADER_RE matches nothing.
        # Without --no-color this exits 2 via COULD_NOT_PARSE, which looks like a block but
        # is the guard understanding nothing — and on a clean tree it blocked every commit.
        git(self.fixture.repo, "config", "color.ui", "always")
        self._stage_secret()
        self._assert_real_hit(run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"}, "cwd": str(self.fixture.repo)}))

    def test_reports_the_line_number_of_a_hit(self):
        # conventions.md's reporting rule has always said file + line + pattern class. The
        # guard reported file and class only, so the stated contract ran ahead of the code.
        self.fixture.append_and_stage("a harmless first line")
        self.fixture.append_and_stage("api_key" + ' = "' + "abcd1234efgh5678" + '"')
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"}, "cwd": str(self.fixture.repo)})
        self.assertEqual(2, result.returncode)
        # f.txt starts with "hello", then the two appended lines -> the secret is line 3.
        self.assertIn("f.txt:3", result.stderr)
        self.assertNotIn("abcd1234efgh5678", result.stderr)

    def test_forbidden_pattern_does_not_match_its_own_declaration(self):
        # C3: a plain-literal Forbidden entry contains the literal it forbids, so scanning the
        # declaring file made every commit in the repo block from the line that declares the
        # rule — escapable only by deleting the entry, i.e. turning the control off.
        literal = "SUPERSECRET" + "MARKER"
        self._write_forbidden_architecture(literal, "no marker in the tree")
        git(self.fixture.repo, "add", ".planning/ARCHITECTURE.md")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"}, "cwd": str(self.fixture.repo)})
        self.assertEqual(0, result.returncode)

    def test_forbidden_scan_reads_architecture_from_the_repo_root(self):
        # C2: reading .planning/ARCHITECTURE.md relative to the hook's cwd meant running git
        # from any subdirectory silently disabled the whole Forbidden check, while the
        # credential scan still fired from that same cwd — so it looked like it had run.
        literal = "SUBDIR" + "FORBIDDEN"
        self._write_forbidden_architecture(literal, "no subdir literal")
        subdir = self.fixture.repo / "sub"
        subdir.mkdir()
        (subdir / "x.txt").write_text("value = " + literal + "\n", encoding="utf-8")
        git(self.fixture.repo, "add", "-A")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"}, "cwd": str(subdir)})
        self.assertEqual(2, result.returncode)
        self.assertIn("no subdir literal", result.stderr)
        self.assertNotIn(literal, result.stderr)

    def test_catastrophic_forbidden_regex_blocks_instead_of_hanging(self):
        # C1: Python `re` has no timeout, so a nested-quantifier pattern hung the guard on
        # every commit forever. A guard that hangs is not fail-closed; it is one that gets
        # removed. Expiry is could-not-check -> block.
        self._write_forbidden_architecture(r"(a+)+$", "catastrophic by construction")
        self.fixture.append_and_stage("a" * 60 + "!")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"}, "cwd": str(self.fixture.repo)})
        self.assertEqual(2, result.returncode)
        self.assertIn("did not finish", result.stderr)

    def test_allows_a_clean_commit_with_color_ui_always(self):
        # The other direction, and the one that actually bricked the workflow: a guard that
        # blocks every commit is not safer than one that blocks none, it just gets removed.
        git(self.fixture.repo, "config", "color.ui", "always")
        self.fixture.append_and_stage("a harmless line with no credential in it")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"}, "cwd": str(self.fixture.repo)})
        self.assertEqual(0, result.returncode)

    def test_blocks_staged_secret_with_noprefix_config(self):
        # Same bypass class as mnemonicPrefix, via diff.noprefix=true instead
        # (`diff --git file file`, no prefixes at all).
        git(self.fixture.repo, "config", "diff.noprefix", "true")
        fixture_line = "api_key" + ' = "' + "abcd1234efgh5678" + '"'
        self.fixture.append_and_stage(fixture_line)
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)
        self.assertNotIn("abcd1234efgh5678", result.stderr)
        # Same distinction as the mnemonicPrefix test above: must be the real parsed hit,
        # not the could-not-parse fallback exiting 2 for an unrelated reason.
        self.assertIn("pattern:", result.stderr)
        self.assertNotIn("could not parse", result.stderr)

    def test_blocks_forbidden_pattern_literal(self):
        # R8: a literal matching a regex declared on an ARCHITECTURE.md Forbidden bullet is
        # blocked by the same fail-closed path as a credential. Built at runtime so this
        # file's own literal never trips a Forbidden pattern some other repo might declare.
        literal = "FORBID" + "DEN" + "LIT" + "ERAL"
        prose = "a forbidden team identifier"
        self._write_forbidden_architecture(r"\b" + literal + r"\b", prose)
        self.fixture.append_and_stage("line containing " + literal + " here")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked", result.stderr)
        self.assertIn(prose, result.stderr)
        # The matched value must never be echoed.
        self.assertNotIn(literal, result.stderr)
        # Must be the Forbidden path specifically, not the credential pattern and not the
        # could-not-parse fallback — both of which also exit 2.
        self.assertNotIn("secret pattern", result.stderr)
        self.assertNotIn("credential-shaped filename", result.stderr)
        self.assertNotIn("could not parse the outgoing diff", result.stderr)
        self.assertNotIn("could-not-check", result.stderr)

    def test_allows_clean_commit_with_forbidden_pattern_configured(self):
        literal = "FORBID" + "DEN" + "LIT" + "ERAL"
        self._write_forbidden_architecture(r"\b" + literal + r"\b")
        self.fixture.append_and_stage("a totally unrelated clean line")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(0, result.returncode)

    def test_forbidden_bullet_without_pattern_is_not_enforced(self):
        # A Forbidden bullet with no `pattern:` suffix stays prose-only guidance — silently
        # unenforced, by design.
        literal = "FORBID" + "DEN" + "LIT" + "ERAL"
        prose = "mentions " + literal + " in prose only, no pattern declared"
        arch_dir = self.fixture.repo / ".planning"
        arch_dir.mkdir(exist_ok=True)
        (arch_dir / "ARCHITECTURE.md").write_text(f"## Forbidden\n- {prose}\n", encoding="utf-8")
        self.fixture.append_and_stage("line containing " + literal + " here")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(0, result.returncode)

    def test_malformed_forbidden_pattern_blocks_as_could_not_check(self):
        # A regex that fails to compile is could-not-check, not clean — it must BLOCK even
        # though the staged content itself is unrelated and harmless.
        self._write_forbidden_architecture("[unclosed", prose="a malformed pattern entry")
        self.fixture.append_and_stage("a totally unrelated clean line")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn("could-not-check", result.stderr)
        self.assertIn("a malformed pattern entry", result.stderr)
        # Distinct from the diff-parse could-not-check fallback.
        self.assertNotIn("could not parse the outgoing diff", result.stderr)

    def test_missing_architecture_md_is_benign(self):
        # No .planning/ARCHITECTURE.md at all (GitFixture doesn't write one) is "no patterns
        # declared", not an error — a clean-otherwise commit must not be blocked just because
        # its content happens to look like a literal some OTHER repo's Forbidden entry names.
        literal = "FORBID" + "DEN" + "LIT" + "ERAL"
        self.fixture.append_and_stage("line containing " + literal + " here")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git commit -m x"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(0, result.returncode)

    def test_blocks_forbidden_pattern_on_push(self):
        literal = "FORBID" + "DEN" + "LIT" + "ERAL"
        prose = "a forbidden literal for push"
        self.fixture.checkout("flow/test")
        self._write_forbidden_architecture(r"\b" + literal + r"\b", prose)
        self.fixture.append_and_stage("line containing " + literal + " here")
        git(self.fixture.repo, "commit", "-q", "-m", "wip")
        result = run_hook(SECRET_SCAN_GUARD, {
            "tool_input": {"command": "git push origin flow/test"},
            "cwd": str(self.fixture.repo),
        })
        self.assertEqual(2, result.returncode)
        self.assertIn(prose, result.stderr)
        self.assertNotIn(literal, result.stderr)

    def test_unparseable_diff_is_could_not_check_not_clean(self):
        # A non-empty diff that iter_file_chunks can't split into file sections (no
        # recognisable `diff --git` header at all) must be reported as could-not-check, per
        # conventions.md's fail-closed-guards rule — never collapsed into "nothing found".
        module = load_module(SECRET_SCAN_GUARD, "secret_scan_guard_for_unparseable_test")
        result = module.scan("this diff has no recognisable header line at all\n+still no header\n")
        self.assertIsNotNone(result)
        self.assertIs(result, module.COULD_NOT_PARSE)


class DependencyGuardTests(unittest.TestCase):
    PACKAGE_JSON = json.dumps({
        "name": "app",
        "scripts": {"test": "vitest"},
        "dependencies": {"react": "^17.0.0"},
    }, indent=2) + "\n"

    def setUp(self):
        self.fixture = GitFixture()
        self.addCleanup(self.fixture.cleanup)
        self.manifest = self.fixture.repo / "package.json"
        self.manifest.write_text(self.PACKAGE_JSON, encoding="utf-8")

    def edit(self, old, new, path=None, mode="default"):
        return run_hook(DEPENDENCY_GUARD, {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(path or self.manifest),
                           "old_string": old, "new_string": new},
            "cwd": str(self.fixture.repo),
            "permission_mode": mode,
        })

    def bash(self, command, mode="default"):
        return run_hook(DEPENDENCY_GUARD, {
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "cwd": str(self.fixture.repo),
            "permission_mode": mode,
        })

    def decision(self, result):
        self.assertEqual(0, result.returncode, result.stderr)
        if not result.stdout.strip():
            return None, ""
        output = json.loads(result.stdout)["hookSpecificOutput"]
        return output["permissionDecision"], output["permissionDecisionReason"]

    def test_asks_on_new_dependency(self):
        decision, reason = self.decision(self.edit(
            '"react": "^17.0.0"', '"react": "^17.0.0",\n    "left-pad": "1.3.0"'))
        self.assertEqual("ask", decision)
        self.assertIn("left-pad 1.3.0", reason)
        self.assertIn("DECISIONS.md", reason)

    def test_asks_on_version_change(self):
        decision, reason = self.decision(self.edit('"^17.0.0"', '"^18.2.0"'))
        self.assertEqual("ask", decision)
        self.assertIn("react ^17.0.0 -> ^18.2.0", reason)

    def test_allows_unrelated_manifest_edit(self):
        decision, _ = self.decision(self.edit('"test": "vitest"', '"test": "vitest run"'))
        self.assertIsNone(decision)

    def test_allows_non_manifest_file(self):
        target = self.fixture.repo / "notes.md"
        target.write_text("react ^17.0.0\n", encoding="utf-8")
        decision, _ = self.decision(self.edit("^17.0.0", "^18.2.0", path=target))
        self.assertIsNone(decision)

    def test_asks_on_bash_package_add(self):
        decision, reason = self.decision(self.bash("cd web && npm install left-pad lodash"))
        self.assertEqual("ask", decision)
        self.assertIn("left-pad, lodash", reason)

    def test_allows_bash_install_from_existing_manifest(self):
        for command in ("npm install", "pip install -r requirements.txt", "git commit -m 'npm add x'"):
            decision, _ = self.decision(self.bash(command))
            self.assertIsNone(decision, command)

    def test_blocks_in_bypass_permissions_mode(self):
        result = self.bash("uv add httpx", mode="bypassPermissions")
        self.assertEqual(2, result.returncode)
        self.assertIn("httpx", result.stderr)

    def test_asks_on_write_of_new_lockfile_entries(self):
        result = run_hook(DEPENDENCY_GUARD, {
            "tool_name": "Write",
            "tool_input": {"file_path": str(self.fixture.repo / "go.mod"),
                           "content": "module x\n\nrequire github.com/a/b v1.2.0\n"},
            "cwd": str(self.fixture.repo),
        })
        decision, reason = self.decision(result)
        self.assertEqual("ask", decision)
        self.assertIn("github.com/a/b v1.2.0", reason)

    def test_asks_when_manifest_unparseable_after_edit(self):
        decision, reason = self.decision(self.edit('"^17.0.0"', '"^17.0.0'))
        self.assertEqual("ask", decision)
        self.assertIn("could-not-check", reason)

    def test_configured_manifest_list_replaces_default(self):
        (self.fixture.repo / ".planning" / "config.json").write_text(
            json.dumps({"dependency_manifests": ["deps.lst"]}), encoding="utf-8")
        decision, _ = self.decision(self.edit('"^17.0.0"', '"^18.2.0"'))
        self.assertIsNone(decision)
        listing = self.fixture.repo / "deps.lst"
        listing.write_text("a\n", encoding="utf-8")
        decision, reason = self.decision(self.edit("a", "b", path=listing))
        self.assertEqual("ask", decision)
        self.assertIn("deps.lst", reason)


    # --- routine within-major revision bumps (Brian, 2026-10-23: "minor and patch bumps should
    # skip that prompt - those revision changes can go into an existing PR") ------------------

    def write(self, name, content):
        return run_hook(DEPENDENCY_GUARD, {
            "tool_name": "Write",
            "tool_input": {"file_path": str(self.fixture.repo / name), "content": content},
            "cwd": str(self.fixture.repo),
        })

    def test_allows_minor_and_patch_bump_of_existing_dependency(self):
        for new in ('"^17.0.2"', '"^17.3.0"'):
            with self.subTest(new=new):
                decision, _ = self.decision(self.edit('"^17.0.0"', new))
                self.assertIsNone(decision)

    def test_routine_bump_passes_in_bypass_mode_too(self):
        result = self.edit('"^17.0.0"', '"^17.0.1"', mode="bypassPermissions")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stdout.strip())

    def test_still_asks_when_routine_bump_comes_with_a_new_dependency(self):
        decision, reason = self.decision(self.edit(
            '"react": "^17.0.0"', '"react": "^17.0.1",\n    "left-pad": "1.3.0"'))
        self.assertEqual("ask", decision)
        self.assertIn("left-pad 1.3.0", reason)
        self.assertNotIn("react", reason)

    def test_still_asks_on_downgrade_range_change_and_unreadable_versions(self):
        for new in ('"^16.14.0"', '"^17.0.0-rc.1"', '">=17.0.0"', '"~17.0.1"', '"17.x"',
                    '"*"', '"latest"', '"npm:preact@^17.0.1"', '"git+https://x.test/r.git"'):
            with self.subTest(new=new):
                decision, _ = self.decision(self.edit('"^17.0.0"', new))
                self.assertEqual("ask", decision)

    def test_csproj_and_central_package_bumps(self):
        for name in ("App.csproj", "Directory.Packages.props"):
            element = "PackageReference" if name.endswith(".csproj") else "PackageVersion"
            path = self.fixture.repo / name
            path.write_text(f'<Project><ItemGroup>\n  <{element} Include="Aspire.Hosting" '
                            f'Version="13.6.2" />\n</ItemGroup></Project>\n', encoding="utf-8")
            with self.subTest(name=name, bump="patch"):
                decision, _ = self.decision(self.edit('"13.6.2"', '"13.6.3"', path=path))
                self.assertIsNone(decision)
            with self.subTest(name=name, bump="minor"):
                decision, _ = self.decision(self.edit('"13.6.2"', '"13.7.0"', path=path))
                self.assertIsNone(decision)
            with self.subTest(name=name, bump="major"):
                decision, reason = self.decision(self.edit('"13.6.2"', '"14.0.0"', path=path))
                self.assertEqual("ask", decision)
                self.assertIn("Aspire.Hosting 13.6.2 -> 14.0.0", reason)
            for new in ('"[13.6.2,14.0)"', '"13.*"', '"$(AspireVersion)"', '"13.6.1"'):
                with self.subTest(name=name, new=new):
                    decision, _ = self.decision(self.edit('"13.6.2"', new, path=path))
                    self.assertEqual("ask", decision)

    def test_requirements_and_go_mod_bumps(self):
        req = self.fixture.repo / "requirements.txt"
        req.write_text("httpx==0.27.0\nrequests==2.31.0\n", encoding="utf-8")
        decision, _ = self.decision(self.edit("requests==2.31.0", "requests==2.32.3", path=req))
        self.assertIsNone(decision)
        decision, _ = self.decision(self.edit("httpx==0.27.0", "httpx==0.27.2", path=req))
        self.assertIsNone(decision)
        decision, _ = self.decision(self.edit("httpx==0.27.0", "httpx==0.28.0", path=req))
        self.assertEqual("ask", decision)  # 0.x: the minor is the major
        decision, _ = self.decision(self.edit("requests==2.31.0", "requests>=2.31.0", path=req))
        self.assertEqual("ask", decision)
        gomod = self.fixture.repo / "go.mod"
        gomod.write_text("module x\n\nrequire github.com/a/b v1.2.0\n", encoding="utf-8")
        decision, _ = self.decision(self.edit("v1.2.0", "v1.3.1", path=gomod))
        self.assertIsNone(decision)
        decision, _ = self.decision(self.edit("b v1.2.0", "b/v2 v2.0.0", path=gomod))
        self.assertEqual("ask", decision)

    def test_lockfile_registry_change_is_never_routine(self):
        def lock(version, host):
            return json.dumps({"lockfileVersion": 3, "packages": {
                "": {"name": "app"},
                "node_modules/react": {
                    "version": version,
                    "resolved": f"https://{host}/react/-/react-{version}.tgz"}}})
        (self.fixture.repo / "package-lock.json").write_text(
            lock("17.0.0", "registry.npmjs.org"), encoding="utf-8")
        decision, _ = self.decision(self.write("package-lock.json",
                                               lock("17.0.2", "registry.npmjs.org")))
        self.assertIsNone(decision)
        decision, reason = self.decision(self.write("package-lock.json",
                                                    lock("17.0.2", "npm.evil.test")))
        self.assertEqual("ask", decision)
        self.assertIn("npm.evil.test", reason)

    def test_cargo_lock_git_source_change_is_never_routine(self):
        def lock(version, source):
            return f'[[package]]\nname = "serde"\nversion = "{version}"\nsource = "{source}"\n'
        registry = "registry+https://github.com/rust-lang/crates.io-index"
        (self.fixture.repo / "Cargo.lock").write_text(lock("1.0.190", registry), encoding="utf-8")
        decision, _ = self.decision(self.write("Cargo.lock", lock("1.0.200", registry)))
        self.assertIsNone(decision)
        decision, _ = self.decision(self.write(
            "Cargo.lock", lock("1.0.200", "git+https://github.com/someone/serde#abc123")))
        self.assertEqual("ask", decision)

    def test_bash_package_add_still_asks_even_for_an_existing_package(self):
        # The guard cannot tell what the resolver will pick, so a command naming a package
        # always gates; a routine bump goes through a manifest edit instead.
        decision, _ = self.decision(self.bash("npm install react@17.0.2"))
        self.assertEqual("ask", decision)

    def test_is_routine_bump_table(self):
        guard = load_module(DEPENDENCY_GUARD, "dependency_guard_routine")
        routine = [("1.2.3", "1.2.4"), ("1.2.3", "1.9.0"), ("^1.2.3", "^1.3.0"),
                   ("~=1.2", "~=1.4"), ("==2.31.0", "==2.32.3"), ("v1.2.0", "v1.3.1"),
                   ("[1.2.3]", "[1.2.4]"), ("1.2.3-rc.1", "1.2.3"), ("0.4.1", "0.4.7"),
                   ("10.0.1", "10.0.100"), ("1.2.3.4", "1.2.3.5"),
                   ("4.17.20 (registry.npmjs.org)", "4.17.21 (registry.npmjs.org)"),
                   ("==1.2; python_version<'3.11'", "==1.3; python_version<'3.11'")]
        gated = [("1.2.3", "2.0.0"), ("2.0.0", "1.9.9"), ("1.2.4", "1.2.3"), ("0.4.1", "0.5.0"),
                 ("0.0.1", "0.0.2"), ("1.2.3", "1.2.4-beta.1"), ("v1.2.0", "v1.2.1+incompatible"),
                 ("^1.2.3", "~1.2.4"), ("1.2.3", "^1.2.4"), ("^1.2.3", ">=1.2.3"),
                 ("1.2.3", "1.x"), ("1.2.3", "*"), ("1.2.3", "latest"), ("", "1.2.3"),
                 ("[1.0,2.0)", "[1.1,2.0)"), ("$(V)", "1.2.3"), ("None", "1.2.3"),
                 ("4.17.20 (registry.npmjs.org)", "4.17.21 (npm.evil.test)"),
                 ("4.17.20", "4.17.21 (npm.evil.test)"),
                 ("==1.2; python_version<'3.11'", "==1.3")]
        for old, new in routine:
            with self.subTest(old=old, new=new):
                self.assertTrue(guard.is_routine_bump(old, new))
        for old, new in gated:
            with self.subTest(old=old, new=new):
                self.assertFalse(guard.is_routine_bump(old, new))


class DestructiveGitGuardTests(unittest.TestCase):
    """Commands that discard work or rewrite shared history are blocked on any branch."""

    BLOCKED = [
        "git push --force",
        "git push -f origin flow/x",
        "git push origin flow/x --force",
        "git push -uf origin flow/x",
        "git push --force-with-lease",
        "git push --force-with-lease=main:abc123 origin main",
        "git push origin +flow/x",
        "git push origin +HEAD:refs/heads/flow/x",
        "git push origin -- +flow/x",
        "git reset --hard",
        "git reset --hard HEAD~1",
        "git clean -f",
        "git clean --force",
        "git clean -fd",
        "git clean -xdf",
        "git branch -D flow/x",
        "git branch --delete --force flow/x",
        "git branch -d -f flow/x",
        "git branch -df flow/x",
        "git -C /tmp/repo push -f",
        "git -c core.pager=cat reset --hard",
        "/usr/bin/git push -f",
        "GIT_TRACE=1 git push -f",
        "sudo git reset --hard",
        "cd repo && git reset --hard origin/main",
        "git fetch; git push -f",
        "echo ok | git clean -fdx",
        "echo $(git reset --hard)",
        "bash -c 'git push --force'",
        "bash -c \"git status && git push -f\"",
        "eval git branch -D flow/x",
        "git status\ngit push -f",
    ]

    ALLOWED = [
        "git push",
        "git push -u origin flow/x",
        "git push origin flow/x",
        "git push origin :refs/heads/old",
        "git push -o ci.skip origin flow/x",
        "git push -ofoo origin flow/x",
        "git push --force-if-includes origin flow/x",
        "git reset",
        "git reset --soft HEAD~1",
        "git reset HEAD f.txt",
        "git clean -n",
        "git clean -n -f",
        "git clean -fn",
        "git clean --dry-run --force",
        "git branch -d flow/x",
        "git branch -f flow/x HEAD",
        "git log --force",
        "git commit -m 'do not push --force'",
        "git commit -m \"reset --hard is never the fix\"",
        "echo git push -f",
        "ls -la",
    ]

    def setUp(self):
        self.guard = load_module(DESTRUCTIVE_GIT_GUARD, "destructive_git_guard")

    def test_blocks_every_destructive_form(self):
        for command in self.BLOCKED:
            with self.subTest(command=command):
                self.assertIsNotNone(self.guard.find_destructive(command))

    def test_allows_safe_git_and_non_git_commands(self):
        for command in self.ALLOWED:
            with self.subTest(command=command):
                self.assertIsNone(self.guard.find_destructive(command))

    def test_hook_exits_2_with_reason_on_force_push(self):
        result = run_hook(DESTRUCTIVE_GIT_GUARD, {"tool_input": {"command": "git push --force"}})
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked: git push --force", result.stderr)

    def test_hook_blocks_force_with_lease(self):
        result = run_hook(DESTRUCTIVE_GIT_GUARD, {
            "tool_input": {"command": "git push --force-with-lease origin flow/x"}})
        self.assertEqual(2, result.returncode)
        self.assertIn("--force-with-lease", result.stderr)

    def test_hook_blocks_on_a_feature_branch_too(self):
        fixture = GitFixture()
        self.addCleanup(fixture.cleanup)
        fixture.checkout("flow/test")
        result = run_hook(DESTRUCTIVE_GIT_GUARD, {
            "tool_input": {"command": "git reset --hard"}, "cwd": str(fixture.repo)})
        self.assertEqual(2, result.returncode)
        self.assertIn("Blocked: git reset --hard", result.stderr)

    def test_hook_allows_normal_push(self):
        result = run_hook(DESTRUCTIVE_GIT_GUARD, {
            "tool_input": {"command": "git push -u origin flow/x"}})
        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stderr)

    def test_hook_fails_open_loudly_on_bad_json(self):
        result = subprocess.run(
            [sys.executable, str(DESTRUCTIVE_GIT_GUARD)],
            input="not json", capture_output=True, text=True)
        self.assertEqual(0, result.returncode)
        self.assertIn("destructive-git-guard:", result.stderr)


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
