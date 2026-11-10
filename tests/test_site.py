"""The website under site/: generated from repo sources, committed in sync, links resolve.

The command reference is generated from plugins/devflow/skills/*/SKILL.md by site/build.py,
so a skill added, renamed or removed without a rebuild fails here instead of shipping a stale
page. site/ holds no Markdown, so it never counts toward the prompt-lines budget.
"""
import importlib.util
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
PUBLIC = SITE / "public"


def load_build():
    spec = importlib.util.spec_from_file_location("site_build", SITE / "build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CommandReferenceTest(unittest.TestCase):
    def test_every_skill_has_an_entry_in_the_generated_reference(self):
        html = load_build().render_commands()
        skills = sorted(p.parent.name for p in (ROOT / "plugins/devflow/skills").glob("*/SKILL.md"))
        self.assertTrue(skills)
        for name in skills:
            self.assertIn(f'id="cmd-{name}"', html, f"{name} missing from the command reference")
        self.assertEqual(len(skills), html.count('<article class="cmd"'))

    def test_committed_reference_page_has_every_skill(self):
        page = (PUBLIC / "commands.html").read_text(encoding="utf-8")
        for path in (ROOT / "plugins/devflow/skills").glob("*/SKILL.md"):
            self.assertIn(f'id="cmd-{path.parent.name}"', page)

    def test_explicit_only_skills_are_marked(self):
        build = load_build()
        html = build.render_commands()
        for skill in build.skills():
            entry = html.split(f'id="cmd-{skill["name"]}"', 1)[1].split("</article>", 1)[0]
            self.assertEqual(skill["explicit_only"], "Explicit-only" in entry, skill["name"])


class CommittedOutputTest(unittest.TestCase):
    def test_public_matches_a_fresh_build(self):
        result = subprocess.run([sys.executable, str(SITE / "build.py"), "--check"],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_chart_is_a_byte_copy_of_docs_assets(self):
        for name in ("sdlc-vs-devflow.png", "sdlc-vs-devflow.svg"):
            self.assertEqual((ROOT / "docs/assets" / name).read_bytes(),
                             (PUBLIC / "assets" / name).read_bytes(), name)

    def test_no_markdown_under_site(self):
        # budget-count.sh counts every tracked *.md outside .planning/; site/ must add none.
        self.assertEqual([], sorted(str(p) for p in SITE.rglob("*.md")))


class LookTest(unittest.TestCase):
    """The dark product look: shared top nav and dark scheme on every page, home headline kept."""

    HEADLINE = "A development process for coding agents."

    def pages(self):
        pages = {p.name: p.read_text(encoding="utf-8") for p in PUBLIC.glob("*.html")}
        self.assertEqual({file for _, file, _ in load_build().PAGES}, set(pages))
        return pages

    def test_stylesheet_is_dark(self):
        css = (PUBLIC / "assets/site.css").read_text(encoding="utf-8")
        self.assertIn("color-scheme: dark;", css)
        self.assertNotIn("color-scheme: light;", css.split("@media print", 1)[0])
        self.assertNotIn(".rail", css)
        self.assertIn(":focus-visible", css)
        self.assertIn("prefers-reduced-motion", css)

    def test_every_page_has_skip_link_dark_scheme_and_top_nav(self):
        build = load_build()
        for name, page in self.pages().items():
            self.assertIn('<meta name="color-scheme" content="dark">', page, name)
            self.assertIn('<a class="skip" href="#main">', page, name)
            self.assertIn('<main id="main"', page, name)
            self.assertNotIn('class="rail"', page, name)
            top = page.split('<header class="top">', 1)[1].split("</header>", 1)[0]
            for _, file, label in build.PAGES:
                self.assertIn(f'href="{file}"', top, f"{name}: nav lacks {label}")
            self.assertEqual(1, top.count('aria-current="page"'), name)
            self.assertIn(f'href="{build.REPO}">GitHub</a>', top, name)
            self.assertIn('<a class="pill" href="start.html">Install</a>', top, name)

    def test_home_keeps_headline_and_copyable_install(self):
        index = self.pages()["index.html"]
        self.assertIn(f"<h1>{self.HEADLINE}</h1>", index)
        self.assertNotIn("from first requirements through release", index)
        self.assertNotIn("Plans on disk", index)
        hero = index.split('<section class="hero">', 1)[1].split("</section>", 1)[0]
        install = load_build().readme_block("### Claude Code")
        self.assertIn(f'<pre class="code" tabindex="0">{install}</pre>', hero)
        # The copy button is progressive enhancement: hidden until the script finds a clipboard.
        self.assertIn('<button type="button" class="copy" hidden', hero)
        self.assertIn('href="start.html">Install DevFlow</a>', hero)
        self.assertIn('href="first-workflow.html">Read a real run, start to finish</a>', hero)

    def test_command_surface_names_real_commands(self):
        hero = self.pages()["index.html"].split('<aside class="surface"', 1)[1].split("</aside>", 1)[0]
        shown = re.findall(r"<code>/(flow-[a-z-]+)</code>", hero)
        self.assertEqual(["flow-new", "flow-plan", "flow-execute", "flow-status", "flow-pr"], shown)
        for name in shown:
            self.assertTrue((ROOT / "plugins/devflow/skills" / name / "SKILL.md").is_file(), name)


class LinksTest(unittest.TestCase):
    ATTR = re.compile(r'(?:href|src)="([^"]+)"')

    def test_relative_links_resolve_and_fragments_exist(self):
        pages = sorted(PUBLIC.glob("*.html"))
        self.assertTrue(pages)
        ids = {p.name: set(re.findall(r'id="([^"]+)"', p.read_text(encoding="utf-8"))) for p in pages}
        for page in pages:
            for target in self.ATTR.findall(page.read_text(encoding="utf-8")):
                if re.match(r"^[a-z]+:", target):
                    continue
                path, _, frag = target.partition("#")
                file = path or page.name
                self.assertTrue((PUBLIC / file).is_file(), f"{page.name}: {target} does not exist")
                if frag:
                    self.assertIn(frag, ids.get(file, set()), f"{page.name}: #{frag} not in {file}")

    def test_no_root_absolute_internal_links(self):
        # GitHub Pages serves this repo under /devflow/, so "/x" would 404 at the domain root.
        url = re.compile(r'''(?:href|src)\s*=\s*["']([^"']*)["']|url\(\s*["']?([^"')]*)''')
        files = sorted(PUBLIC.rglob("*.html")) + sorted(PUBLIC.rglob("*.css"))
        self.assertTrue(files)
        for f in files:
            for a, b in url.findall(f.read_text(encoding="utf-8")):
                target = (a or b).strip()
                self.assertFalse(target.startswith("/") and not target.startswith("//"),
                                 f"{f.relative_to(PUBLIC)}: root-absolute {target!r}")

    def test_every_image_has_alt_text(self):
        for page in PUBLIC.glob("*.html"):
            for tag in re.findall(r"<img\b[^>]*>", page.read_text(encoding="utf-8")):
                self.assertRegex(tag, r'alt="[^"]+"', f"{page.name}: {tag}")


if __name__ == "__main__":
    unittest.main()
