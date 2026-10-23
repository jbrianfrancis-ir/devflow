"""Tests for flow-second-opinion.py — scope guard, argument parsing, tool-output parsing,
report rendering, trial-log rows, and an end-to-end run against fake gh/codex/grok.

The pure parts are tested by importing the script. The end-to-end cases put fake `gh`,
`codex` and `grok` executables first on PATH and point the fake `gh repo clone` at a local
fixture repo, so nothing reaches GitHub or a model. Global git config is masked.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/devflow/scripts/flow-second-opinion.py"

spec = importlib.util.spec_from_file_location("flow_second_opinion", SCRIPT)
sor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sor)

ALLOW = sor.parse_allowlist("jbrianfrancis-ir/devflow\njbrianfrancis-ir/ralph-tui fork-ok\n")
NOT_FORK = {"fork": False, "owner": {"login": "jbrianfrancis-ir"}}


class ParsePrRef(unittest.TestCase):
    def test_url_and_short_forms(self):
        self.assertEqual(sor.parse_pr_ref("https://github.com/jbrianfrancis-ir/devflow/pull/60"),
                         ("jbrianfrancis-ir", "devflow", 60))
        self.assertEqual(sor.parse_pr_ref("https://github.com/o/r/pull/3/files"), ("o", "r", 3))
        self.assertEqual(sor.parse_pr_ref("o/r#12"), ("o", "r", 12))

    def test_rejects_non_pr(self):
        for bad in ("https://github.com/o/r/issues/3", "o/r", "", "https://evil.example/o/r/pull/1",
                    "https://github.com/o/r/pull/1; rm -rf /"):
            with self.assertRaises(sor.SetupError, msg=bad):
                sor.parse_pr_ref(bad)


class Allowlist(unittest.TestCase):
    def test_comments_case_and_fork_ok(self):
        got = sor.parse_allowlist("# trial\nJBrianFrancis-IR/DevFlow  # ok\n\nnot a slug\n"
                                  "o/r fork-ok\n")
        self.assertEqual(got, {"jbrianfrancis-ir/devflow": {"fork_ok": False},
                               "o/r": {"fork_ok": True}})


class ScopeGuard(unittest.TestCase):
    def reasons(self, owner, repo, info, allow=ALLOW, pr=None):
        return sor.scope_reasons(owner, repo, allow, info, pr)

    def test_allowlisted_non_fork_passes(self):
        self.assertEqual(self.reasons("jbrianfrancis-ir", "devflow", NOT_FORK, pr={}), [])

    def test_missing_allowlist_refuses_everything(self):
        self.assertTrue(self.reasons("jbrianfrancis-ir", "devflow", NOT_FORK, allow={}))

    def test_not_allowlisted_refused(self):
        self.assertTrue(any("not in the second-opinion allowlist" in r
                            for r in self.reasons("jbrianfrancis-ir", "replyquill", NOT_FORK)))

    def test_ir_fork_refused_even_if_allowlisted(self):
        allow = sor.parse_allowlist("jbrianfrancis-ir/SpecialProjects.StudentLoans fork-ok")
        info = {"fork": True, "owner": {"login": "jbrianfrancis-ir"},
                "parent": {"full_name": "InformativeResearch/SpecialProjects.StudentLoans"},
                "source": {"full_name": "InformativeResearch/SpecialProjects.StudentLoans"}}
        got = self.reasons("jbrianfrancis-ir", "SpecialProjects.StudentLoans", info, allow=allow)
        self.assertTrue(any("IR-named" in r for r in got))
        self.assertTrue(any("InformativeResearch repository" in r for r in got))

    def test_ir_owner_refused(self):
        allow = sor.parse_allowlist("informativeresearch/devflow")
        got = self.reasons("InformativeResearch", "devflow",
                           {"fork": False, "owner": {"login": "InformativeResearch"}}, allow=allow)
        self.assertTrue(got)

    def test_fork_refused_without_fork_ok(self):
        allow = sor.parse_allowlist("jbrianfrancis-ir/autoforge")
        info = {"fork": True, "owner": {"login": "jbrianfrancis-ir"},
                "parent": {"full_name": "AutoForgeAI/autoforge"},
                "source": {"full_name": "AutoForgeAI/autoforge"}}
        self.assertTrue(any("is a fork" in r for r in
                            self.reasons("jbrianfrancis-ir", "autoforge", info, allow=allow)))

    def test_non_ir_fork_with_fork_ok_passes(self):
        info = {"fork": True, "owner": {"login": "jbrianfrancis-ir"},
                "parent": {"full_name": "subsy/ralph-tui"}, "source": {"full_name": "subsy/ralph-tui"}}
        self.assertEqual(self.reasons("jbrianfrancis-ir", "ralph-tui", info), [])

    def test_fork_ok_still_refuses_ir_source(self):
        info = {"fork": True, "owner": {"login": "jbrianfrancis-ir"},
                "parent": {"full_name": "someone/ralph-tui"},
                "source": {"full_name": "InformativeResearch/ralph-tui"}}
        self.assertTrue(self.reasons("jbrianfrancis-ir", "ralph-tui", info))

    def test_unreadable_metadata_fails_closed(self):
        for info in (None, {}, {"owner": {"login": "jbrianfrancis-ir"}}):
            self.assertTrue(self.reasons("jbrianfrancis-ir", "devflow", info), info)

    def test_fork_flag_not_false_fails_closed(self):
        self.assertTrue(self.reasons("jbrianfrancis-ir", "devflow", {"fork": None}))

    def test_cross_repository_head_refused(self):
        pr = {"isCrossRepository": True, "headRepositoryOwner": {"login": "stranger"}}
        self.assertTrue(any("another repository" in r for r in
                            self.reasons("jbrianfrancis-ir", "devflow", NOT_FORK, pr=pr)))


class Args(unittest.TestCase):
    def test_defaults(self):
        args = sor.parse_args(["review", "o/r#1"])
        self.assertEqual(args.tools, ["codex", "grok"])
        self.assertFalse(args.post)
        self.assertEqual(args.timeout, sor.DEFAULT_TIMEOUT)

    def test_tool_subset_and_dedupe(self):
        self.assertEqual(sor.parse_args(["review", "o/r#1", "--tools", "grok, codex,grok"]).tools,
                         ["grok", "codex"])

    def test_bad_values(self):
        for argv in (["review", "o/r#1", "--tools", "claude"], ["review", "o/r#1", "--tools", ""],
                     ["review", "o/r#1", "--timeout", "5"], ["review", "o/r#1", "--head", "main"],
                     ["review", "o/r#1", "--max-turns", "0"]):
            with self.assertRaises(sor.SetupError, msg=argv):
                sor.parse_args(argv)


class Commands(unittest.TestCase):
    def test_codex_is_read_only_and_never_bypasses(self):
        cmd = sor.codex_command("/tmp/r", "/tmp/s", "/tmp/o", "p")
        joined = " ".join(cmd)
        self.assertIn("-s read-only", joined)
        self.assertIn('approval_policy="never"', joined)
        self.assertIn("--ephemeral", cmd)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", cmd)
        self.assertNotIn("workspace-write", joined)

    def test_grok_is_read_only_and_never_auto_approves(self):
        cmd = sor.grok_command("/tmp/r", "/tmp/p", "sid", 10)
        joined = " ".join(cmd)
        self.assertIn("--sandbox read-only", joined)
        self.assertIn("--permission-mode dontAsk", joined)
        for bad in ("--always-approve", "--yolo", "bypassPermissions", "acceptEdits"):
            self.assertNotIn(bad, joined)
        allows = [cmd[i + 1] for i, a in enumerate(cmd) if a == "--allow"]
        self.assertTrue(all(a in ("Read", "Grep") or a.startswith("Bash(git ") for a in allows))
        self.assertIn("Edit", [cmd[i + 1] for i, a in enumerate(cmd) if a == "--deny"])

    def test_tool_env_strips_github_tokens(self):
        env = sor.tool_env({"GH_TOKEN": "x", "GITHUB_TOKEN": "y", "GH_ENTERPRISE_TOKEN": "z",
                            "PATH": "/bin"}, "/tmp/empty")
        self.assertNotIn("GH_TOKEN", env)
        self.assertNotIn("GITHUB_TOKEN", env)
        self.assertNotIn("GH_ENTERPRISE_TOKEN", env)
        self.assertEqual(env["GH_CONFIG_DIR"], "/tmp/empty")
        self.assertEqual(env["GROK_WRITE_FILE"], "0")


REVIEW = {"summary": "One real bug.", "findings": [
    {"severity": "low", "category": "other", "file": "b.py", "line": 2, "title": "nit", "detail": "d"},
    {"severity": "HIGH", "category": "bug", "file": "a.py", "line": "7", "title": "off by one",
     "detail": "loop skips last"},
    {"severity": "bogus", "category": "?", "file": "", "line": -3, "title": "", "detail": ""},
]}


class Parsing(unittest.TestCase):
    def test_grok_json_with_usage_and_cost(self):
        out = json.dumps({"text": json.dumps(REVIEW), "stopReason": "end_turn", "sessionId": "s1",
                          "num_turns": 4, "usage": {"input_tokens": 100, "output_tokens": 20,
                                                    "cache_read_input_tokens": 5},
                          "total_cost_usd": 0.0123})
        review, usage, cost, sid = sor.parse_grok_output(out)
        self.assertEqual(len(review["findings"]), 3)
        self.assertEqual(usage["input_tokens"], 100)
        self.assertEqual(usage["turns"], 4)
        self.assertEqual(cost, 0.0123)
        self.assertEqual(sid, "s1")

    def test_grok_streamed_progress_objects_take_the_last(self):
        progress = {"summary": "Reading the diff.", "findings": []}
        text = json.dumps(progress) + json.dumps(progress) + json.dumps(REVIEW)
        review, *_ = sor.parse_grok_output(json.dumps({"text": text, "stopReason": "end_turn"}))
        self.assertEqual(review["summary"], "One real bug.")
        self.assertEqual(len(review["findings"]), 3)

    def test_grok_cancelled_run_has_no_review(self):
        text = json.dumps({"summary": "Reading the diff.", "findings": []})
        out = json.dumps({"text": text, "stopReason": "cancelled", "total_cost_usd": 0.5})
        review, _, cost, _ = sor.parse_grok_output(out)
        self.assertIsNone(review)
        self.assertEqual(cost, 0.5)
        self.assertEqual(sor.grok_stop_reason(out), "cancelled")

    def test_grok_denies_common_non_git_commands(self):
        cmd = sor.grok_command("/tmp/r", "/tmp/p", "sid", 10)
        denies = [cmd[i + 1] for i, a in enumerate(cmd) if a == "--deny"]
        for rule in ("Bash(python*)", "Bash(cd *)", "Bash(cat*)", "Bash(curl*)"):
            self.assertIn(rule, denies)
        self.assertFalse(any(d.startswith("Bash(git ") and d not in (
            "Bash(git push*)", "Bash(git commit*)") for d in denies))

    def test_grok_structured_output_key(self):
        review, *_ = sor.parse_grok_output(json.dumps({"structured_output": REVIEW}))
        self.assertEqual(review["summary"], "One real bug.")

    def test_fenced_json_in_text(self):
        review = sor.extract_review("Here:\n```json\n" + json.dumps(REVIEW) + "\n```\n")
        self.assertEqual(len(review["findings"]), 3)

    def test_garbage_is_none(self):
        self.assertIsNone(sor.extract_review("no json here"))
        self.assertEqual(sor.parse_grok_output(""), (None, None, None, None))

    def test_codex_events_usage(self):
        events = "\n".join([
            json.dumps({"type": "thread.started", "thread_id": "t"}),
            "not json",
            json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1000,
                        "cached_input_tokens": 400, "output_tokens": 50}}),
            json.dumps({"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 5}}),
        ])
        self.assertEqual(sor.parse_codex_events(events),
                         {"input_tokens": 1010, "cached_input_tokens": 400, "output_tokens": 55,
                          "reasoning_output_tokens": 0, "turns": 2})
        self.assertIsNone(sor.parse_codex_events("nothing"))

    def test_normalize_sorts_and_clamps(self):
        got = sor.normalize_findings(REVIEW["findings"] + ["junk"])
        self.assertEqual([f["severity"] for f in got], ["high", "low", "low"])
        self.assertEqual(got[0]["line"], 7)
        self.assertEqual(got[2]["line"], 0)
        self.assertEqual(got[2]["category"], "other")
        self.assertEqual(got[2]["file"], "?")


def ctx():
    return {"slug": "jbrianfrancis-ir/devflow", "number": 60,
            "url": "https://github.com/jbrianfrancis-ir/devflow/pull/60", "title": "feat: x",
            "base_ref": "main", "head": "671e108969b6f8489702f02df7199a500949d5fd",
            "base": "1e8aa54c384dd36dca971d8ebedf4b7d30b7ef98", "diffstat": "2 files changed",
            "ts": "2026-10-23T15:00:00-04:00", "report_path": "/home/u/.local/state/x.md",
            "log_path": "/home/u/.local/state/trial-log.jsonl"}


def results():
    return [
        {"tool": "codex", "version": "codex-cli 0.164.0", "status": "ok", "runtime_s": 61.2,
         "findings": sor.normalize_findings(REVIEW["findings"]), "summary": "One real bug.",
         "usage": {"input_tokens": 1000, "cached_input_tokens": 400, "output_tokens": 50},
         "cost_usd": None, "plan": "ChatGPT plan", "tree_clean": True, "note": ""},
        {"tool": "grok", "version": "grok 1.0.67", "status": "skipped", "runtime_s": None,
         "findings": [], "summary": "", "usage": None, "cost_usd": None, "plan": "",
         "tree_clean": None, "note": "grok is not authenticated (run `grok login --device-auth`)"},
    ]


class Report(unittest.TestCase):
    def test_header_table_and_findings(self):
        text = sor.render_report(ctx(), results())
        self.assertTrue(text.startswith("## second-opinion review (trial)\n"))
        self.assertIn("| codex | codex-cli 0.164.0 | ok | 61s | 3 | in 1,000, cached 400, out 50, "
                      "ChatGPT plan | unchanged |", text)
        self.assertIn("| grok | grok 1.0.67 | skipped | — | — | not reported | — |", text)
        self.assertIn("- **HIGH** (bug) `a.py:7` — off by one", text)
        self.assertIn("_skipped_: grok is not authenticated", text)
        self.assertIn("/home/u/.local/state/x.md", text)

    def test_comment_omits_local_paths_and_redacts(self):
        res = results()
        res[0]["findings"][0]["detail"] = "leaked ghp_" + "a" * 30
        text = sor.render_report(ctx(), res, for_comment=True)
        self.assertNotIn("/home/u/", text)
        self.assertNotIn("ghp_aaaa", text)
        self.assertIn("[REDACTED]", text)

    def test_comment_is_capped(self):
        res = results()
        res[0]["findings"] = [dict(res[0]["findings"][0], detail="x" * 1500)] * 60
        self.assertLessEqual(len(sor.render_report(ctx(), res, for_comment=True)),
                             sor.COMMENT_LIMIT)

    def test_violation_is_loud(self):
        res = results()
        res[0].update(status="read-only violation", tree_clean=False, note="changed")
        self.assertIn("**CHANGED**", sor.render_report(ctx(), res))


class TrialLog(unittest.TestCase):
    def test_rows_have_blank_triage_fields(self):
        rows = sor.log_rows(ctx(), results())
        self.assertEqual([r["tool"] for r in rows], ["codex", "grok"])
        self.assertEqual(rows[0]["findings"], 3)
        self.assertEqual(rows[0]["by_severity"]["high"], 1)
        self.assertIsNone(rows[1]["findings"])
        for row in rows:
            self.assertEqual(row["real_issue_claude_missed"], "")
            self.assertEqual(row["false_positive"], "")
            json.dumps(row)

    def test_scorecard(self):
        rows = sor.log_rows(ctx(), results())
        rows[0]["real_issue_claude_missed"] = 1
        rows[0]["false_positive"] = 2
        card = sor.scorecard(rows + sor.log_rows(ctx(), results()))
        self.assertEqual(card["codex"]["runs"], 2)
        self.assertEqual(card["codex"]["findings"], 6)
        self.assertEqual(card["codex"]["real_issue_claude_missed"], 1)
        self.assertEqual(card["codex"]["untriaged"], 1)
        self.assertEqual(card["codex"]["prs"], 1)
        self.assertEqual(card["grok"]["skipped"], 2)


FAKE_GH = r'''#!/usr/bin/env python3
import json, os, subprocess, sys
a = sys.argv[1:]
if a[:1] == ["api"] and "/pulls/" in a[1]:
    print(os.environ["FAKE_PR_JSON"]); sys.exit(0)
if a[:1] == ["api"]:
    print(os.environ["FAKE_REPO_JSON"]); sys.exit(0)
if a[:2] == ["repo", "clone"]:
    extra = a[a.index("--") + 1:] if "--" in a else []
    sys.exit(subprocess.call(["git", "clone", *extra, os.environ["FAKE_ORIGIN"], a[3]]))
if a[:2] == ["pr", "comment"]:
    open(os.environ["FAKE_POST_LOG"], "a").write(" ".join(a) + "\n"); sys.exit(0)
sys.exit(3)
'''

FAKE_CODEX = r'''#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
if a == ["--version"]:
    print("codex-cli 9.9.9"); sys.exit(0)
if a[:2] == ["login", "status"]:
    print("Logged in using ChatGPT"); sys.exit(0)
if a[:1] == ["exec"]:
    out = a[a.index("-o") + 1]
    repo = a[a.index("-C") + 1]
    if os.environ.get("FAKE_CODEX_MODE") == "mutate":
        os.chmod(repo, 0o755)
        open(os.path.join(repo, "sneaky.txt"), "w").write("x")
    open(out, "w").write(json.dumps({"summary": "ok", "findings": [
        {"severity": "medium", "category": "bug", "file": "app.py", "line": 2,
         "title": "t", "detail": "d"}]}))
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 9, "output_tokens": 1}}))
    sys.exit(0)
sys.exit(3)
'''

FAKE_GROK = r'''#!/usr/bin/env python3
import sys
a = sys.argv[1:]
if a == ["--version"]:
    print("grok 0.0.1"); sys.exit(0)
if a[:1] == ["models"]:
    print("You are not authenticated."); sys.exit(0)
sys.exit(3)
'''


def rest_pr(head, base, head_repo="jbrianfrancis-ir/devflow"):
    repo = lambda name: {"full_name": name, "owner": {"login": name.split("/")[0]}}
    return {"number": 7, "title": "feat", "state": "open",
            "html_url": "https://github.com/jbrianfrancis-ir/devflow/pull/7",
            "head": {"sha": head, "ref": "feature", "repo": repo(head_repo) if head_repo else None},
            "base": {"sha": base, "ref": "main", "repo": repo("jbrianfrancis-ir/devflow")}}


class RestPrInfo(unittest.TestCase):
    def test_same_repo(self):
        info = sor.pr_info_from_rest(rest_pr("a" * 40, "b" * 40))
        self.assertEqual((info["headRefOid"], info["baseRefOid"], info["baseRefName"]),
                         ("a" * 40, "b" * 40, "main"))
        self.assertFalse(info["isCrossRepository"])
        self.assertEqual(info["url"], "https://github.com/jbrianfrancis-ir/devflow/pull/7")

    def test_fork_head_and_deleted_head_are_cross_repo(self):
        self.assertTrue(sor.pr_info_from_rest(rest_pr("a", "b", "stranger/devflow"))
                        ["isCrossRepository"])
        self.assertTrue(sor.pr_info_from_rest(rest_pr("a", "b", None))["isCrossRepository"])

    def test_unusable_payloads(self):
        for data in (None, [], {}, {"head": {"sha": "a"}}, {"head": {}, "base": {"sha": "b"}}):
            self.assertIsNone(sor.pr_info_from_rest(data), data)


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        gitconfig = self.root / "gitconfig"
        gitconfig.write_text("")
        self.env = {**os.environ, "GIT_CONFIG_GLOBAL": str(gitconfig), "GIT_CONFIG_NOSYSTEM": "1",
                    "HOME": str(self.root / "home"), "XDG_CONFIG_HOME": str(self.root / "cfg"),
                    "XDG_STATE_HOME": str(self.root / "state")}
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        for name, body in (("gh", FAKE_GH), ("codex", FAKE_CODEX), ("grok", FAKE_GROK)):
            path = bin_dir / name
            path.write_text(body.replace("#!/usr/bin/env python3", "#!" + sys.executable, 1))
            path.chmod(0o755)
        self.env["PATH"] = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"
        origin = self.root / "origin"
        self.git("init", "-q", "-b", "main", str(origin), cwd=self.root)
        for key, value in (("user.name", "T"), ("user.email", "t@example.com"),
                           ("commit.gpgsign", "false")):
            self.git("config", key, value, cwd=origin)
        (origin / "app.py").write_text("a = 1\n")
        self.git("add", ".", cwd=origin)
        self.git("commit", "-qm", "base", cwd=origin)
        base = self.git("rev-parse", "HEAD", cwd=origin)
        self.git("checkout", "-qb", "feature", cwd=origin)
        (origin / "app.py").write_text("a = 1\nb = a / 0\n")
        self.git("commit", "-qam", "feature", cwd=origin)
        head = self.git("rev-parse", "HEAD", cwd=origin)
        self.git("update-ref", "refs/pull/7/head", head, cwd=origin)
        self.git("checkout", "-q", "main", cwd=origin)
        self.head, self.base = head, base
        (self.root / "cfg/devflow").mkdir(parents=True)
        (self.root / "cfg/devflow/second-opinion-allowlist").write_text("jbrianfrancis-ir/devflow\n")
        self.env.update(
            FAKE_ORIGIN=str(origin), FAKE_POST_LOG=str(self.root / "posts.log"),
            FAKE_REPO_JSON=json.dumps({"fork": False, "owner": {"login": "jbrianfrancis-ir"}}),
            FAKE_PR_JSON=json.dumps(rest_pr(head, base)))
        self.work = self.root / "work"
        self.work.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args, cwd):
        return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True,
                              env=getattr(self, "env", None), check=True).stdout.strip()

    def run_script(self, *args, **extra_env):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                              env={**self.env, **extra_env}, timeout=120)

    def test_review_writes_report_and_log_without_posting(self):
        proc = self.run_script("review", "jbrianfrancis-ir/devflow#7", "--work-root", str(self.work))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        summary = json.loads(proc.stdout)
        self.assertEqual(summary["head"], self.head)
        self.assertEqual(summary["base"], self.base)
        self.assertEqual(summary["post"], "not requested")
        tools = {t["tool"]: t for t in summary["tools"]}
        self.assertEqual(tools["codex"]["status"], "ok")
        self.assertTrue(tools["codex"]["tree_clean"])
        self.assertEqual(tools["codex"]["findings"], 1)
        self.assertEqual(tools["grok"]["status"], "skipped")
        report = Path(summary["report"]).read_text()
        self.assertIn("## second-opinion review (trial)", report)
        self.assertIn("`app.py:2`", report)
        rows = [json.loads(l) for l in Path(summary["log"]).read_text().splitlines()]
        self.assertEqual([r["tool"] for r in rows], ["codex", "grok"])
        self.assertFalse((self.root / "posts.log").exists())
        self.assertEqual(list(self.work.iterdir()), [], "throwaway checkout not removed")

    def test_post_adds_one_comment(self):
        proc = self.run_script("review", "jbrianfrancis-ir/devflow#7", "--work-root",
                               str(self.work), "--post", "--tools", "codex")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        posts = (self.root / "posts.log").read_text().splitlines()
        self.assertEqual(len(posts), 1)
        self.assertIn("pr comment 7 -R jbrianfrancis-ir/devflow --body-file", posts[0])

    def test_mutating_tool_is_a_violation_and_never_posts(self):
        proc = self.run_script("review", "jbrianfrancis-ir/devflow#7", "--work-root",
                               str(self.work), "--post", "--tools", "codex",
                               FAKE_CODEX_MODE="mutate")
        self.assertEqual(proc.returncode, 1, proc.stderr)
        summary = json.loads(proc.stdout)
        self.assertEqual(summary["tools"][0]["status"], "read-only violation")
        self.assertFalse(summary["tools"][0]["tree_clean"])
        self.assertTrue(summary["post"].startswith("refused"))
        self.assertFalse((self.root / "posts.log").exists())

    def test_scope_refuses_fork_before_cloning(self):
        proc = self.run_script(
            "review", "jbrianfrancis-ir/devflow#7", "--work-root", str(self.work), "--post",
            FAKE_REPO_JSON=json.dumps({"fork": True, "owner": {"login": "jbrianfrancis-ir"},
                                       "parent": {"full_name": "InformativeResearch/devflow"},
                                       "source": {"full_name": "InformativeResearch/devflow"}}))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("REFUSED", proc.stderr)
        self.assertEqual(list(self.work.iterdir()), [])
        self.assertFalse((self.root / "state").exists())

    def test_scope_subcommand(self):
        proc = self.run_script("scope", "jbrianfrancis-ir/replyquill#1")
        self.assertEqual(proc.returncode, 1)
        self.assertFalse(json.loads(proc.stdout)["allowed"])
        proc = self.run_script("scope", "jbrianfrancis-ir/devflow#7")
        self.assertEqual(proc.returncode, 0, proc.stdout)


if __name__ == "__main__":
    unittest.main()
