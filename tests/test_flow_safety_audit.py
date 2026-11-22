"""Tests for plugins/devflow/scripts/flow-safety-audit.py — the `/flow-audit --safety` helper.

pure-logic: heuristic parsers over fixture repos. protects: the safety checks fire on the
hazard shapes they name, stay quiet on the guarded form, and never print a credential.
"""
import contextlib
import importlib.util
import io
import re
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/devflow/scripts/flow-safety-audit.py"
SPEC = importlib.util.spec_from_file_location("flow_safety_audit", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SafetyAuditTests(unittest.TestCase):
    def make_repo(self, files):
        root = tempfile.mkdtemp(prefix="flow-safety-audit-fixture-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        for rel, content in files.items():
            path = Path(root) / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return root

    def run_main(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = MODULE.main(list(argv))
        return code, out.getvalue()

    def found(self, files):
        return {(rel, check) for rel, _line, check, _msg in MODULE.scan(self.make_repo(files))}

    def test_non_local_test_db_host_is_flagged_without_printing_credentials(self):
        root = self.make_repo({
            "tests/appsettings.Testing.json":
                '{"Db": "Server=prod-sql.example.com,1433;User Id=sa;Password=hunter2",'
                ' "Ok": "Host=localhost;Database=t", "L1": "Server=(localdb)\\\\MSSQLLocalDB;Database=t",'
                ' "L2": "Data Source=(LocalDB)\\\\v11.0;x", "L3": "Server=.\\\\SQLEXPRESS;x", "L4": "Server=(local);x",'
                ' "L5": "Server=localhost\\\\SQLEXPRESS;x", "L6": "Server=.;x", "Bad": "Server=prod-sql2.example.com\\\\SQLEXPRESS;x"}\n',
            "docker-compose.test.yml":
                "services:\n  db:\n    image: postgres\n  app:\n    environment:\n"
                "      A: postgres://u:pw@db:5432/app\n      B: postgresql://admin:p@ss@prod-db.example.com/app\n",
            "tests/conftest.py": 'host = os.environ["DB_HOST"]\n',
        })
        code, out = self.run_main("--root", root)
        self.assertEqual(0, code)
        self.assertIn("tests/appsettings.Testing.json:1  S1-TESTDB  test DB host 'prod-sql.example.com'", out)
        self.assertIn("docker-compose.test.yml:7  S1-TESTDB  test DB host 'prod-db.example.com'", out)
        self.assertIn("test DB host 'prod-sql2.example.com\\\\SQLEXPRESS'", out)
        self.assertEqual(3, out.count("S1-TESTDB"))  # localhost, LocalDB/SQLEXPRESS, compose `db`, env lookup: local/unknown
        for value in ("hunter2", "pw@", "p@ss", "admin"):
            self.assertNotIn(value, out)

    def test_unguarded_recursive_rm_is_flagged_and_the_guarded_form_is_clean(self):
        found = self.found({
            "scripts/clean.sh": '#!/usr/bin/env bash\nrm -rf "$BUILD_DIR/out"\n',
            "scripts/ok.sh": '#!/usr/bin/env bash\nset -Eeuo pipefail\nt=$(realpath "${T:?}")\nrm -rf -- "${T:?}"\n',
            "scripts/other-var.sh": '#!/usr/bin/env bash\nset -u\nroot=$(realpath .)\nrm -rf -- "${T:?}"\n',
            "scripts/far.sh": '#!/usr/bin/env bash\nset -u\nt=$(realpath "${T:?}")\n' + ":\n" * 15 + 'rm -rf -- "${T:?}"\n',
            # `rmtree` + `(` split so this file's own unguarded fixture does not trip a self-audit.
            "tools/clean.py": "import shutil, sys\nroot = os.path.realpath('.')\nshutil.rmtree" "(sys.argv[1])\n",
            "tools/ok.py": "p = os.path.realpath(sys.argv[1])\nif not p.startswith(ROOT): sys.exit(1)\nshutil.rmtree(p)\n",
        })
        self.assertEqual({("scripts/clean.sh", "S2-RM-GUARD"), ("scripts/clean.sh", "S2-SET-U"),
                          ("scripts/clean.sh", "S2-REALPATH"), ("scripts/other-var.sh", "S2-REALPATH"),
                          ("scripts/far.sh", "S2-REALPATH"), ("tools/clean.py", "S2-REALPATH")}, found)

    def test_reference_delete_guard_example_passes_every_check(self):
        doc = (ROOT / "plugins/devflow/references/safety-checks.md").read_text(encoding="utf-8")
        example = re.search(r"^## S2 .*?^```bash\n(.*?)^```", doc, re.M | re.S).group(1)
        self.assertIn("rm -rf", example)
        self.assertEqual(set(), self.found({"scripts/clean.sh": example}))

    def test_agent_job_on_untrusted_trigger_with_secrets_or_write_token_is_flagged(self):
        found = self.found({
            ".github/workflows/agent.yml":
                "on:\n  issue_comment:\n    types: [created]\npermissions:\n  contents: write\njobs:\n"
                "  build:\n    steps:\n      - run: make\n"
                "  agent:\n    steps:\n      - uses: anthropics/claude-code-action@v1\n"
                "        with:\n          key: ${{ secrets.ANTHROPIC_API_KEY }}\n",
            ".github/workflows/default-token.yml": "on: pull_request_target\njobs:\n  fix:\n    steps:\n      - run: codex exec fix\n",
            ".github/workflows/read-only.yml":
                "on: [issues]\npermissions:\n  contents: read\njobs:\n  triage:\n    steps:\n      - run: claude -p triage\n",
            ".github/workflows/push.yml": "on: [push]\njobs:\n  review:\n    steps:\n      - run: claude -p review\n",
        })
        self.assertEqual({(".github/workflows/agent.yml", "S4-CI-AGENT"),
                          (".github/workflows/default-token.yml", "S4-CI-AGENT")}, found)

    def test_destructive_script_without_a_warning_line_is_flagged(self):
        found = self.found({
            "scripts/reset.sh": '#!/bin/sh\npsql -c "DROP DATABASE app"\n',
            "scripts/drop.sh": '#!/bin/sh\necho "WARNING: DATABASE_URL host is $H; this DROPS all tables"\npsql -c "DROP TABLE t"\n',
            "scripts/deploy.ps1": "az deployment group create -g $rg\n",
            "scripts/t1.sh": "psql -c 'TRUNCATE TABLE users'\n",
            "scripts/t2.sh": "psql -c 'TRUNCATE public.orders'\n",
            "scripts/t3.sh": 'psql -c \'TRUNCATE TABLE "Order Items"\'\n',
            "scripts/t4.ps1": "sqlcmd -Q 'TRUNCATE TABLE [dbo].[Users]'\n",
            "scripts/t5.py": 'run("TRUNCATE `db`.`t`")\n',
            "scripts/fmt.py": "# truncate long lines before printing\n",
        })
        self.assertEqual({(rel, "S5-NO-WARNING") for rel in ("scripts/reset.sh", "scripts/deploy.ps1", "scripts/t1.sh",
                          "scripts/t2.sh", "scripts/t3.sh", "scripts/t4.ps1", "scripts/t5.py")}, found)

    def test_strict_exit_codes_and_env_files_are_never_read(self):
        root = self.make_repo({"tests/.env.test": "DATABASE_URL=postgres://u:p@prod-db.example.com/app\n"})
        self.assertEqual((0, "0 finding(s)\n"), self.run_main("--root", root, "--strict"))
        Path(root, "scripts").mkdir()
        Path(root, "scripts/nuke.sh").write_text("#!/bin/sh\nterraform destroy\n", encoding="utf-8")
        self.assertEqual(1, self.run_main("--root", root, "--strict")[0])
        self.assertEqual(0, self.run_main("--root", root)[0])
        self.assertEqual(2, self.run_main("--root", str(Path(root, "missing")))[0])


if __name__ == "__main__":
    unittest.main()
