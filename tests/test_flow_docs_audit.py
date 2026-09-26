"""Tests for plugins/devflow/scripts/flow-docs-audit.py — the `/flow-audit --docs`
claims inventory.

Every test builds a disposable fixture repo, runs the audit over it, and asserts
the status of each claim by rule (D1-D5), plus the fail-closed cases: an
uncheckable claim is `could-not-check`, never `verified`.
"""
import contextlib
import importlib.util
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/devflow/scripts/flow-docs-audit.py"

SPEC = importlib.util.spec_from_file_location("flow_docs_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

FENCE = "```"


class DocsAuditTestCase(unittest.TestCase):
    def make_repo(self, files):
        """files: {relative_path: str or bytes}."""
        root = tempfile.mkdtemp(prefix="flow-docs-audit-fixture-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        for rel, content in files.items():
            full = Path(root) / rel
            full.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                full.write_bytes(content)
            else:
                full.write_text(content, encoding="utf-8")
        return root

    def audit(self, files, paths=()):
        return MODULE.run(self.make_repo(files), paths)

    def status(self, report, rule, claim):
        """The one status recorded for `claim` under `rule`; fails if absent."""
        hits = [c for c in report["claims"] if c["rule"] == rule and c["claim"] == claim]
        self.assertEqual(1, len(hits), f"{rule} {claim!r}: {report['claims']}")
        return hits[0]["status"]

    def claims(self, report, rule):
        return [c["claim"] for c in report["claims"] if c["rule"] == rule]


class PathClaimTests(DocsAuditTestCase):
    """D1: repo-relative paths in backticks and Markdown links."""

    FILES = {
        "scripts/build.py": "print('x')\n",
        "docs/guide.md": "# Guide\n",
        "README.md": (
            "# App\n\n"
            "Run `scripts/build.py`, not `scripts/gone.py`.\n"
            "See [the guide](docs/guide.md) and [old](docs/old.md).\n"
            "Branch `origin/main`, template `phases/NN-slug/PLAN.md`, glob `src/*.py`.\n"
            "Link [site](https://example.com/a/b.md) and [up](../outside.md).\n"
        ),
    }

    def test_existing_path_is_verified_and_missing_is_contradicted(self):
        report = self.audit(self.FILES)
        self.assertEqual("verified", self.status(report, "D1", "scripts/build.py"))
        self.assertEqual("contradicted", self.status(report, "D1", "scripts/gone.py"))

    def test_links_resolve_against_the_referring_file(self):
        report = self.audit(self.FILES)
        self.assertEqual("verified", self.status(report, "D1", "docs/guide.md"))
        self.assertEqual("contradicted", self.status(report, "D1", "docs/old.md"))

    def test_link_from_a_subdirectory_does_not_resolve_against_the_root(self):
        report = self.audit({"scripts/build.py": "", "docs/a.md": "[x](scripts/build.py)\n"})
        self.assertEqual("contradicted", self.status(report, "D1", "scripts/build.py"))

    def test_link_escaping_the_root_is_could_not_check(self):
        report = self.audit(self.FILES)
        self.assertEqual("could-not-check", self.status(report, "D1", "../outside.md"))

    def test_urls_placeholders_globs_and_slash_words_are_not_claims(self):
        claims = self.claims(self.audit(self.FILES), "D1")
        for skipped in ("origin/main", "phases/NN-slug/PLAN.md", "src/*.py",
                        "https://example.com/a/b.md"):
            self.assertNotIn(skipped, claims)

    def test_paths_inside_fences_are_not_d1_claims(self):
        report = self.audit({"README.md": f"# A\n\n{FENCE}text\nscripts/gone.py\n{FENCE}\n"})
        self.assertEqual([], self.claims(report, "D1"))


class ScriptInvocationTests(DocsAuditTestCase):
    """D2: scripts invoked in shell fences."""

    def fixture(self, body, info="bash"):
        return {
            "scripts/ok.py": "",
            "tools/run.sh": "",
            "web/dev.sh": "",
            "README.md": f"# A\n\n{FENCE}{info}\n{body}\n{FENCE}\n",
        }

    def test_interpreter_script_that_exists_is_verified(self):
        report = self.audit(self.fixture("python3 scripts/ok.py --flag"))
        self.assertEqual("verified", self.status(report, "D2", "python3 scripts/ok.py"))

    def test_missing_script_is_contradicted(self):
        report = self.audit(self.fixture("bash tools/missing.sh\n./run-me.sh"))
        self.assertEqual("contradicted", self.status(report, "D2", "bash tools/missing.sh"))
        self.assertEqual("contradicted", self.status(report, "D2", "./run-me.sh"))

    def test_cd_moves_the_working_directory(self):
        report = self.audit(self.fixture("cd web && ./dev.sh"))
        self.assertEqual("verified", self.status(report, "D2", "./dev.sh"))

    def test_cd_to_an_unknown_directory_is_could_not_check(self):
        report = self.audit(self.fixture("cd $APP_DIR\n./dev.sh"))
        self.assertEqual("could-not-check", self.status(report, "D2", "./dev.sh"))

    def test_python_module_and_inline_code_are_not_claims(self):
        report = self.audit(self.fixture("python3 -m http.server\npython -c 'print(1)'"))
        self.assertEqual([], self.claims(report, "D2"))

    def test_output_fences_and_console_output_lines_are_skipped(self):
        output = self.audit(self.fixture("./missing.sh", info="text"))
        self.assertEqual([], self.claims(output, "D2"))
        console = self.audit(self.fixture("$ ./tools/run.sh\n./missing.sh", info="console"))
        self.assertEqual(["./tools/run.sh"], self.claims(console, "D2"))


class PackageScriptTests(DocsAuditTestCase):
    """D3: npm/pnpm/yarn scripts against the nearest package.json."""

    PKG = '{"scripts": {"build": "tsc", "test": "jest"}}'

    def test_present_script_is_verified_and_absent_is_contradicted(self):
        report = self.audit({
            "package.json": self.PKG,
            "README.md": f"Run `npm run build`.\n\n{FENCE}sh\npnpm deploy-it\nyarn lint\nnpm test\n{FENCE}\n",
        })
        self.assertEqual("verified", self.status(report, "D3", "npm run build"))
        self.assertEqual("verified", self.status(report, "D3", "npm test"))
        self.assertEqual("contradicted", self.status(report, "D3", "pnpm deploy-it"))
        self.assertEqual("contradicted", self.status(report, "D3", "yarn lint"))

    def test_package_manager_builtins_are_not_claims(self):
        report = self.audit({"package.json": self.PKG,
                             "README.md": f"{FENCE}sh\nnpm install\npnpm add left-pad\nyarn\n{FENCE}\n"})
        self.assertEqual([], self.claims(report, "D3"))

    def test_nearest_package_json_wins(self):
        report = self.audit({
            "package.json": self.PKG,
            "web/package.json": '{"scripts": {"dev": "vite"}}',
            "README.md": f"{FENCE}sh\ncd web\nnpm run dev\nnpm run build\n{FENCE}\n",
        })
        self.assertEqual("verified", self.status(report, "D3", "npm run dev"))
        self.assertEqual("contradicted", self.status(report, "D3", "npm run build"))

    def test_no_package_json_is_could_not_check(self):
        report = self.audit({"README.md": "Run `npm run build`.\n"})
        self.assertEqual("could-not-check", self.status(report, "D3", "npm run build"))

    def test_unparseable_package_json_is_could_not_check(self):
        report = self.audit({"package.json": "{not json", "README.md": "Run `npm run build`.\n"})
        self.assertEqual("could-not-check", self.status(report, "D3", "npm run build"))


class MakeTargetTests(DocsAuditTestCase):
    """D4: make targets against the Makefile."""

    MAKEFILE = "test: build\n\tpytest\n\nbuild lint:\n\techo hi\nVAR := 1\n"

    def test_present_target_is_verified_and_absent_is_contradicted(self):
        report = self.audit({"Makefile": self.MAKEFILE,
                             "README.md": f"Run `make test`.\n\n{FENCE}\nmake -j4 lint deploy\n{FENCE}\n"})
        self.assertEqual("verified", self.status(report, "D4", "make test"))
        self.assertEqual("verified", self.status(report, "D4", "make lint"))
        self.assertEqual("contradicted", self.status(report, "D4", "make deploy"))

    def test_variable_assignment_is_not_a_target(self):
        report = self.audit({"Makefile": self.MAKEFILE, "README.md": "Run `make VAR`.\n"})
        self.assertEqual("contradicted", self.status(report, "D4", "make VAR"))

    def test_no_makefile_is_could_not_check(self):
        report = self.audit({"README.md": "Run `make test`.\n"})
        self.assertEqual("could-not-check", self.status(report, "D4", "make test"))

    def test_includes_make_a_missing_target_could_not_check(self):
        report = self.audit({"Makefile": "include common.mk\ntest:\n\ttrue\n",
                             "README.md": "Run `make deploy`.\n"})
        self.assertEqual("could-not-check", self.status(report, "D4", "make deploy"))


class EnvVarTests(DocsAuditTestCase):
    """D5: env names in an environment table must be referenced in non-doc files."""

    DOC = ("# Config\n\n## Environment\n\n| Var | Used by |\n|---|---|\n"
           "| `API_URL` | app |\n| `GHOST_KEY` | nothing |\n| `ENV_ONLY` | dotenv |\n")

    def test_referenced_name_is_verified_with_a_location(self):
        report = self.audit({"app/main.py": "import os\nURL = os.environ['API_URL']\n",
                             "docs/config.md": self.DOC})
        self.assertEqual("verified", self.status(report, "D5", "API_URL"))
        hit = next(c for c in report["claims"] if c["claim"] == "API_URL")
        self.assertIn("app/main.py:2", hit["detail"])

    def test_unreferenced_name_is_contradicted(self):
        report = self.audit({"app/main.py": "x = 1\n", "docs/config.md": self.DOC})
        self.assertEqual("contradicted", self.status(report, "D5", "GHOST_KEY"))

    def test_env_files_and_docs_are_never_evidence(self):
        report = self.audit({
            "app/main.py": "x = 1\n",
            ".env": "ENV_ONLY=1\n",
            "docs/other.md": "ENV_ONLY is used.\n",
            "docs/config.md": self.DOC,
        })
        self.assertEqual("contradicted", self.status(report, "D5", "ENV_ONLY"))

    def test_tables_outside_an_env_heading_are_not_claims(self):
        report = self.audit({"app/main.py": "", "README.md": "# Commands\n\n| Cmd |\n|---|\n| `API_URL` |\n"})
        self.assertEqual([], self.claims(report, "D5"))

    def test_no_readable_source_file_is_could_not_check(self):
        report = self.audit({"docs/config.md": self.DOC})
        self.assertEqual("could-not-check", self.status(report, "D5", "API_URL"))


class FailClosedTests(DocsAuditTestCase):
    def test_undecodable_doc_is_could_not_check(self):
        report = self.audit({"README.md": b"# A\n\xff\xfe `scripts/x.py`\n"})
        self.assertEqual("could-not-check", self.status(report, "DOC", "README.md"))
        self.assertEqual(0, report["summary"]["verified"])

    def test_unterminated_fence_is_could_not_check(self):
        report = self.audit({"scripts/a.py": "", "README.md": f"`scripts/a.py`\n\n{FENCE}bash\n./x.sh\n"})
        self.assertEqual("could-not-check", self.status(report, "DOC", "README.md"))
        self.assertEqual("verified", self.status(report, "D1", "scripts/a.py"))
        self.assertEqual([], self.claims(report, "D2"))

    def test_requested_missing_path_is_could_not_check(self):
        report = self.audit({"README.md": "# A\n"}, paths=["docs/nope.md"])
        self.assertEqual("could-not-check", self.status(report, "DOC", "docs/nope.md"))


class ScopeAndSeverityTests(DocsAuditTestCase):
    def test_default_scope(self):
        report = self.audit({
            "README.md": "", "AGENTS.md": "", "docs/a.md": "", "docs/sub/b.md": "",
            "notes/c.md": "", ".planning/ARCHITECTURE.md": "",
        })
        self.assertEqual(
            [".planning/ARCHITECTURE.md", "AGENTS.md", "README.md", "docs/a.md", "docs/sub/b.md"],
            report["files"])

    def test_contradiction_in_readme_quick_start_is_high(self):
        report = self.audit({"README.md": "# A\n\n## Quick start\n\n`scripts/gone.py`\n\n## Notes\n\n`scripts/lost.py`\n"})
        severity = {c["claim"]: c["severity"] for c in report["claims"]}
        self.assertEqual({"scripts/gone.py": "HIGH", "scripts/lost.py": "MEDIUM"}, severity)


class CliTests(DocsAuditTestCase):
    def run_main(self, argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = MODULE.main(argv)
        return code, out.getvalue()

    def test_exit_codes(self):
        clean = self.make_repo({"a/b.py": "", "README.md": "`a/b.py`\n"})
        dirty = self.make_repo({"README.md": "`a/b.py`\n"})
        self.assertEqual(0, self.run_main(["--root", clean])[0])
        code, out = self.run_main(["--root", dirty])
        self.assertEqual(1, code)
        self.assertIn('"contradicted": 1', out)
        self.assertEqual(2, self.run_main(["--root", os.path.join(clean, "missing")])[0])


if __name__ == "__main__":
    unittest.main()
