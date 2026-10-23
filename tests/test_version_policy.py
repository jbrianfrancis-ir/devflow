"""Tests for the major-only version rule (conventions.md -> Dependency versions).

ARCHITECTURE.md records a framework's major version only; the exact version lives in the
manifests and lockfiles. These read the shipped plugin content, because the failure this
guards against is wording: a template that seeds `13.5.1` into a new project's
ARCHITECTURE.md, or a prompt that tells an agent to "update ARCHITECTURE.md to match" a
patch bump, makes every routine minor/patch update a doc edit plus a drift warning.
"""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "devflow"
MINOR_OR_PATCH = re.compile(r"\b\d+\.\d+")
# "update/bump ... ARCHITECTURE.md ... to match" within one clause.
BUMP_DOC_TO_MATCH = re.compile(
    r"(update|bump)[^.\n;]{0,80}ARCHITECTURE\.md[^.\n;]{0,60}\bto match\b", re.I)
NEGATION = re.compile(r"\b(not|never|no)\b[^.\n]{0,40}$", re.I)


def read(path):
    return path.read_text(encoding="utf-8")


def table_rows(text, heading):
    section = re.split(rf"(?m)^{re.escape(heading)}$", text, maxsplit=1)[1].split("\n## ", 1)[0]
    return [line for line in section.splitlines() if line.startswith("|")]


class ArchitectureTemplateTest(unittest.TestCase):
    def setUp(self):
        self.text = read(PLUGIN / "templates" / "architecture.md")

    def test_version_columns_are_labelled_major(self):
        for heading in ("## Stack", "## Frameworks & libraries"):
            header = table_rows(self.text, heading)[0]
            self.assertIn("| Major |", header, f"{heading} table header: {header}")
            self.assertNotIn("| Version |", header)

    def test_example_rows_carry_no_minor_or_patch(self):
        for heading in ("## Stack", "## Frameworks & libraries"):
            for row in table_rows(self.text, heading)[2:]:
                # `13.x` / `10` are majors; any `N.N` (10.0, 13.5.1) is a minor or patch pin.
                self.assertIsNone(MINOR_OR_PATCH.search(row), f"{heading}: {row}")


class NoDocBumpInstructionTest(unittest.TestCase):
    """No shipped prompt may tell an agent to edit ARCHITECTURE.md to match a version bump."""

    def test_no_update_architecture_to_match(self):
        offenders = []
        for path in sorted(PLUGIN.rglob("*.md")):
            text = read(path)
            for match in BUMP_DOC_TO_MATCH.finditer(text):
                before = text[max(0, match.start() - 60):match.start()]
                if NEGATION.search(before):
                    continue  # "do not bump ARCHITECTURE.md to match" is the rule, not a breach
                line = text.count("\n", 0, match.start()) + 1
                offenders.append(f"{path.relative_to(ROOT)}:{line}: {match.group(0)}")
        self.assertEqual(offenders, [])

    def test_no_install_exactly_the_pinned_versions(self):
        for path in sorted(PLUGIN.rglob("*.md")):
            self.assertNotRegex(read(path), r"exactly the (pinned )?versions it pins|"
                                            r"install/reference exactly the pinned versions",
                                str(path.relative_to(ROOT)))


class ConventionsRuleTest(unittest.TestCase):
    def setUp(self):
        text = read(PLUGIN / "references" / "conventions.md")
        self.section = text.partition("## Dependency versions")[2].split("\n## ", 1)[0]

    def test_records_major_only_and_names_the_manifests(self):
        self.assertIn("records the major version only", self.section)
        for manifest in ("*.csproj", "Directory.Packages.props", "global.json", "package.json"):
            self.assertIn(manifest, self.section)

    def test_minor_patch_is_routine_and_major_is_the_only_event(self):
        flat = " ".join(self.section.split())
        self.assertIn("Within-major (minor/patch) changes are routine", flat)
        self.assertIn("No doc edit, no deviation entry, no drift finding, no warning", flat)
        self.assertIn("A major change is the only version event", flat)
        self.assertIn("`checkpoint:decision`", flat)

    def test_applies_beyond_aspire(self):
        for framework in (".NET", "EF Core", "Node", "React", "TypeScript"):
            self.assertIn(framework, self.section)


class PointerBlockTest(unittest.TestCase):
    def test_root_pointer_matches_template(self):
        block = re.compile(r"<!-- BEGIN DEVFLOW -->.*?<!-- END DEVFLOW -->", re.S)
        template = block.search(read(PLUGIN / "templates" / "agent-pointer.md")).group(0)
        for name in ("CLAUDE.md", "AGENTS.md"):
            self.assertEqual(block.search(read(ROOT / name)).group(0), template, name)
        self.assertIn("major versions it", template)


if __name__ == "__main__":
    unittest.main()
