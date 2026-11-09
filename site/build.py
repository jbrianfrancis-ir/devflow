#!/usr/bin/env python3
"""Build the DevFlow website into site/public/ from files already in this repo.

    python3 site/build.py            # write site/public/
    python3 site/build.py --check    # exit 1 if site/public/ is not what a build would write

Stdlib only. The output is static HTML/CSS plus copied images; nothing here runs in a browser
except a few lines of progressive enhancement, so site/public/ can be served by any static host.

Sources, each with one owner so the site cannot drift from the repo:
- command reference: plugins/devflow/skills/*/SKILL.md frontmatter (name, description,
  disable-model-invocation), grouped by the "Loop" column of README.md's Commands table;
- install commands: the fenced blocks under README.md's "### Claude Code" and
  "### Codex CLI, app, or IDE" headings;
- terminal captures: site/captures/*.txt (raw stdout) and site/captures/runs.json (the command,
  timestamps and exit code of each run);
- the SDLC vs DevFlow chart: docs/assets/sdlc-vs-devflow.{png,svg}, copied byte for byte.
A missing or unparseable source raises; the build never writes a page with a gap in it.
"""

import html
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

SITE = Path(__file__).resolve().parent
ROOT = SITE.parent
OUT = SITE / "public"
TEMPLATES = SITE / "templates"
CAPTURES = SITE / "captures"
SKILLS = ROOT / "plugins" / "devflow" / "skills"
README = ROOT / "README.md"
CHART = ("sdlc-vs-devflow.png", "sdlc-vs-devflow.svg")
REPO = "https://github.com/jbrianfrancis-ir/devflow"

# Page order is nav order. slug -> (file name, nav label).
PAGES = [
    ("index", "index.html", "Overview"),
    ("start", "start.html", "Install"),
    ("first-workflow", "first-workflow.html", "First workflow"),
    ("concepts", "concepts.html", "Concepts"),
    ("commands", "commands.html", "Commands"),
    ("feedback", "feedback.html", "Feedback"),
]

FLOW_LINE = re.compile(r"^`?FLOW: (CONTINUE|GATE|BLOCKED|DONE)\b")  # some runs print it in backticks
PLACEHOLDER = re.compile(r"\{\{([a-z]+):?([A-Za-z0-9_.-]*)\}\}")


class BuildError(Exception):
    pass


# --- sources -----------------------------------------------------------------

def frontmatter(path):
    """name/description/disable-model-invocation from a SKILL.md, folding `>-` blocks."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise BuildError(f"{path}: no frontmatter")
    end = text.find("\n---", 3)
    if end == -1:
        raise BuildError(f"{path}: unterminated frontmatter")
    values, key = {}, None
    for line in text[4:end].splitlines():
        if line.startswith((" ", "\t")) and key:
            values[key] = (values[key] + " " + line.strip()).strip()
        elif ":" in line:
            key, _, value = line.partition(":")
            key, value = key.strip(), value.strip()
            values[key] = "" if value in (">-", ">", "|", "|-") else value
    return values


def skills():
    found = []
    for path in sorted(SKILLS.glob("*/SKILL.md")):
        fm = frontmatter(path)
        name = path.parent.name
        if fm.get("name") != name or not fm.get("description"):
            raise BuildError(f"{path}: frontmatter name/description missing or wrong")
        found.append({
            "name": name,
            "description": fm["description"],
            "explicit_only": fm.get("disable-model-invocation") == "true",
            "source": path.relative_to(ROOT).as_posix(),
        })
    if not found:
        raise BuildError(f"no skills found under {SKILLS}")
    return found


def readme_groups():
    """skill name -> group label, from README.md's '## Commands' table (Loop column)."""
    text = README.read_text(encoding="utf-8")
    _, found, section = text.partition("\n## Commands\n")
    if not found:
        raise BuildError("README.md has no '## Commands' section")
    section = section.split("\n## ", 1)[0]
    groups = {}
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        m = re.match(r"`/([a-z-]+)", cells[1])
        if m:
            groups[m.group(1)] = cells[0]
    if not groups:
        raise BuildError("README.md Commands table has no rows")
    return groups


def readme_block(heading):
    """First fenced block after a README heading line, verbatim."""
    text = README.read_text(encoding="utf-8")
    m = re.search(rf"^{re.escape(heading)}\n+```[a-z]*\n(.*?)\n```", text, re.M | re.S)
    if not m:
        raise BuildError(f"README.md: no fenced block under {heading!r}")
    return m.group(1)


def runs():
    path = CAPTURES / "runs.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for name, run in data["runs"].items():
        if not (CAPTURES / f"{name}.txt").is_file():
            raise BuildError(f"runs.json names {name} but site/captures/{name}.txt is missing")
        for key in ("command", "started", "finished", "exit"):
            if key not in run:
                raise BuildError(f"runs.json {name}: missing {key}")
    return data


# --- rendering ---------------------------------------------------------------

def esc(text):
    return html.escape(text, quote=True)


def inline(text):
    """Escape, then turn `code` spans into <code>. Used for frontmatter descriptions."""
    parts = esc(text).split("`")
    return "".join(f"<code>{p}</code>" if i % 2 else p for i, p in enumerate(parts))


def terminal_lines(text):
    out = []
    for line in text.rstrip("\n").split("\n"):
        m = FLOW_LINE.match(line)
        if m:
            out.append(f'<span class="flow flow-{m.group(1).lower()}">{esc(line)}</span>')
        else:
            out.append(esc(line))
    return "\n".join(out)


def render_capture(name, data):
    run = data["runs"][name]
    body = (CAPTURES / f"{name}.txt").read_text(encoding="utf-8")
    label = esc(run.get("label", name))
    return (
        f'<figure class="term" aria-labelledby="cap-{name}">\n'
        f'<figcaption id="cap-{name}"><span class="term-title">{label}</span>'
        f'<span class="term-meta">exit {esc(str(run["exit"]))} · {esc(run["duration"])}</span></figcaption>\n'
        f'<pre class="term-cmd"><span class="prompt" aria-hidden="true">$ </span>{esc(run["command"])}</pre>\n'
        f'<pre class="term-out" tabindex="0">{terminal_lines(body)}</pre>\n'
        f"</figure>"
    )


def render_flow_lines(data):
    """Every FLOW: line from the captures, in run order — the home page's evidence strip."""
    rows = []
    for name in data["runs"]:
        for line in (CAPTURES / f"{name}.txt").read_text(encoding="utf-8").splitlines():
            m = FLOW_LINE.match(line)
            if m:
                cmd = data["runs"][name]["short"]
                rows.append(
                    f'<li><span class="ledger-cmd">{esc(cmd)}</span>'
                    f'<code class="flow flow-{m.group(1).lower()}">{esc(line)}</code></li>'
                )
    if not rows:
        raise BuildError("no FLOW: line found in any capture")
    return '<ol class="ledger" role="list">\n' + "\n".join(rows) + "\n</ol>"


def render_commands():
    groups = readme_groups()
    found = skills()
    names = {s["name"] for s in found}
    missing = sorted(names - groups.keys())
    extra = sorted(groups.keys() - names)
    if missing or extra:
        raise BuildError(f"README Commands table vs skills: missing {missing}, unknown {extra}")
    order = list(dict.fromkeys(groups[s] for s in groups))  # README order of first appearance
    by_name = {s["name"]: s for s in found}
    by_group = {g: [by_name[n] for n in groups if groups[n] == g] for g in order}  # README row order
    toc, sections = [], []
    for g in order:
        gid = "group-" + re.sub(r"[^a-z0-9]+", "-", g.lower()).strip("-")
        toc.append(f'<li><a href="#{gid}">{esc(g)}</a> <span class="count">{len(by_group[g])}</span></li>')
        items = []
        for s in by_group[g]:
            badge = ('<p class="badge">Explicit-only: the host will not let the model start it. '
                     "A person types it.</p>") if s["explicit_only"] else ""
            items.append(
                f'<article class="cmd" id="cmd-{s["name"]}">\n'
                f'<h3><code>/{s["name"]}</code></h3>\n'
                f'<p class="cmd-alt">Codex: <code>${s["name"]}</code> · '
                f'<a href="{REPO}/blob/main/{s["source"]}">source</a></p>\n'
                f"{badge}\n<p>{inline(s['description'])}</p>\n</article>"
            )
        sections.append(
            f'<section class="cmd-group" aria-labelledby="{gid}">\n'
            f'<h2 id="{gid}">{esc(g)}</h2>\n' + "\n".join(items) + "\n</section>"
        )
    return (
        f'<p class="lede-small">{len(found)} commands, generated from each skill\'s '
        f"<code>SKILL.md</code> frontmatter. Groups follow the README's Commands table.</p>\n"
        f'<nav aria-label="Command groups"><ul class="toc" role="list">{"".join(toc)}</ul></nav>\n'
        + "\n".join(sections)
    )


def page_meta(text, path):
    m = re.match(r"<!--\n(.*?)\n-->\n", text, re.S)
    if not m:
        raise BuildError(f"{path}: missing meta comment")
    meta = dict(line.split(": ", 1) for line in m.group(1).splitlines())
    for key in ("title", "description"):
        if key not in meta:
            raise BuildError(f"{path}: meta has no {key}")
    return meta, text[m.end():]


def fill(body, data, path):
    def repl(m):
        kind, arg = m.group(1), m.group(2)
        if kind == "capture":
            if arg not in data["runs"]:
                raise BuildError(f"{path}: unknown capture {arg}")
            return render_capture(arg, data)
        if kind == "install":
            heading = {"claude": "### Claude Code", "codex": "### Codex CLI, app, or IDE"}[arg]
            return f'<pre class="code" tabindex="0">{esc(readme_block(heading))}</pre>'
        if kind == "flowlines":
            return render_flow_lines(data)
        if kind == "commands":
            return render_commands()
        if kind == "repo":
            return REPO
        if kind == "captured":
            return esc(data[arg])
        raise BuildError(f"{path}: unknown placeholder {m.group(0)}")
    return PLACEHOLDER.sub(repl, body)


def nav(current):
    items = []
    for i, (slug, file, label) in enumerate(PAGES):
        here = ' aria-current="page"' if slug == current else ""
        items.append(f'<li><a href="{file}"{here}><span class="num">{i:02d}</span>{esc(label)}</a></li>')
    return "\n".join(items)


def build(out):
    layout = (TEMPLATES / "layout.html").read_text(encoding="utf-8")
    data = runs()
    out.mkdir(parents=True, exist_ok=True)
    for slug, file, _ in PAGES:
        path = TEMPLATES / "pages" / f"{slug}.html"
        meta, body = page_meta(path.read_text(encoding="utf-8"), path)
        page = (layout
                .replace("{{title}}", esc(meta["title"]))
                .replace("{{description}}", esc(meta["description"]))
                .replace("{{slug}}", slug)
                .replace("{{nav}}", nav(slug))
                .replace("{{content}}", fill(body, data, path))
                .replace("{{repo}}", REPO))
        if "{{" in page:
            raise BuildError(f"{file}: unreplaced placeholder near {page[page.index('{{'):][:40]!r}")
        (out / file).write_text(page, encoding="utf-8")
    assets = out / "assets"
    assets.mkdir(exist_ok=True)
    shutil.copyfile(TEMPLATES / "site.css", assets / "site.css")
    for name in CHART:
        shutil.copyfile(ROOT / "docs" / "assets" / name, assets / name)


def snapshot(directory):
    return {p.relative_to(directory).as_posix(): p.read_bytes()
            for p in sorted(directory.rglob("*")) if p.is_file()}


def main(argv):
    try:
        if argv[1:] == ["--check"]:
            with tempfile.TemporaryDirectory() as tmp:
                build(Path(tmp))
                fresh, committed = snapshot(Path(tmp)), snapshot(OUT) if OUT.is_dir() else {}
            stale = sorted(k for k in fresh.keys() | committed.keys()
                           if fresh.get(k) != committed.get(k))
            if stale:
                print("site/public is stale; run python3 site/build.py. Differs: " + ", ".join(stale))
                return 1
            print(f"site/public up to date ({len(fresh)} files)")
            return 0
        if argv[1:]:
            print(__doc__)
            return 2
        if OUT.is_dir():
            shutil.rmtree(OUT)
        build(OUT)
        print(f"wrote {OUT.relative_to(ROOT)}")
        return 0
    except (BuildError, OSError, KeyError, ValueError) as exc:
        print(f"build failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
