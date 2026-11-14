"""The mapper writes MAP.md "per the template": its section list must match the template's headings.

If a section is added to templates/codebase-map.md but not to flow-mapper.md's list (or the
reverse), the mapper silently stops filling it and the planner, /flow-uat and the verifier read
an empty or missing section.
"""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "plugins/devflow/templates/codebase-map.md"
MAPPER = ROOT / "plugins/devflow/agents/flow-mapper.md"


def template_sections():
    return re.findall(r"(?m)^## (.+?)\s*$", TEMPLATE.read_text(encoding="utf-8"))


def mapper_sections():
    text = MAPPER.read_text(encoding="utf-8")
    m = re.search(r"Write `codebase/MAP\.md` per the template path given \(cap 6KB\): (.+?)\. On refresh", text)
    if not m:
        raise AssertionError("flow-mapper.md no longer has the 'Write codebase/MAP.md per the template' sentence")
    listed = m.group(1)
    omit = re.search(r"\(omit (.+?) when empty\)\s*$", listed)
    listed = re.sub(r"\s*\([^)]*\)", "", listed)
    names = [s.strip() for s in listed.split(" / ")]
    omitted = [s.strip() for s in omit.group(1).split(" / ")] if omit else []
    return names, omitted


class MapperTemplateContractTest(unittest.TestCase):
    def test_mapper_lists_every_template_section_in_order(self):
        names, _ = mapper_sections()
        self.assertEqual(names, template_sections())

    def test_trust_sections_present_and_omitted_when_empty(self):
        names, omitted = mapper_sections()
        for section in ("Features", "Do not copy"):
            self.assertIn(section, names)
            self.assertIn(section, omitted)

    def test_omitted_sections_exist_in_template(self):
        _, omitted = mapper_sections()
        self.assertTrue(set(omitted) <= set(template_sections()), omitted)


if __name__ == "__main__":
    unittest.main()
