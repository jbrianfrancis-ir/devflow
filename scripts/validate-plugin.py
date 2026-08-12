#!/usr/bin/env python3
"""Validate both DevFlow host packages and their shared portable payload."""

import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(ROOT, "plugins", "devflow")
errors = []


def err(message):
    errors.append(message)


def load_json(rel):
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        err(f"{rel}: missing")
        return None
    try:
        with open(path, encoding="utf-8") as stream:
            return json.load(stream)
    except json.JSONDecodeError as exc:
        err(f"{rel}: invalid JSON — {exc}")
        return None


def frontmatter(path):
    with open(path, encoding="utf-8") as stream:
        text = stream.read()
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    values = {}
    for line in text[3:end].strip("\n").splitlines():
        if line and not line.startswith((" ", "\t", "#")) and ":" in line:
            key, _, value = line.partition(":")
            values[key.strip()] = value.strip()
    return values


claude = load_json("plugins/devflow/.claude-plugin/plugin.json")
codex = load_json("plugins/devflow/.codex-plugin/plugin.json")
for host, manifest in (("Claude", claude), ("Codex", codex)):
    if manifest:
        for key in ("name", "version", "description"):
            if not manifest.get(key):
                err(f"{host} manifest: missing {key}")
        if manifest.get("name") != "devflow":
            err(f"{host} manifest: name must be devflow")
if claude and codex and claude.get("version") != codex.get("version"):
    err("Claude and Codex manifest versions differ")
if codex and codex.get("skills") != "./skills/":
    err("Codex manifest: skills must point to ./skills/")
if claude and any(key in claude for key in ("skills", "agents")):
    err("Claude manifest: default skills/agents directories must not be redeclared")

claude_market = load_json(".claude-plugin/marketplace.json")
codex_market = load_json(".agents/plugins/marketplace.json")
if claude_market:
    entries = claude_market.get("plugins") or []
    if len(entries) != 1 or entries[0].get("source") != "./plugins/devflow":
        err("Claude marketplace must point to ./plugins/devflow")
    elif claude and entries[0].get("version") != claude.get("version"):
        err("Claude marketplace version differs from plugin manifest")
if codex_market:
    entries = codex_market.get("plugins") or []
    source = entries[0].get("source", {}) if len(entries) == 1 else {}
    policy = entries[0].get("policy", {}) if len(entries) == 1 else {}
    if source != {"source": "local", "path": "./plugins/devflow"}:
        err("Codex marketplace must point to local ./plugins/devflow")
    if not {"installation", "authentication"}.issubset(policy):
        err("Codex marketplace entry is missing policy fields")

skills = sorted(glob.glob(os.path.join(PLUGIN, "skills", "*", "SKILL.md")))
agents = sorted(glob.glob(os.path.join(PLUGIN, "agents", "*.md")))
if len(skills) != 20:
    err(f"expected 20 skills, found {len(skills)}")
if len(agents) != 9:
    err(f"expected 9 Claude role agents, found {len(agents)}")
for path in skills:
    name = os.path.basename(os.path.dirname(path))
    fm = frontmatter(path)
    rel = os.path.relpath(path, ROOT)
    if not fm or fm.get("name") != name or not fm.get("description"):
        err(f"{rel}: invalid name/description frontmatter")
MODELS = {"opus", "sonnet", "haiku", "inherit"}
for path in agents:
    name = os.path.splitext(os.path.basename(path))[0]
    fm = frontmatter(path)
    rel = os.path.relpath(path, ROOT)
    if not fm or fm.get("name") != name or not fm.get("description") or not fm.get("tools"):
        err(f"{rel}: invalid agent frontmatter")
    elif fm.get("model") not in MODELS:
        err(f"{rel}: model must be one of {'/'.join(sorted(MODELS))}, got {fm.get('model')!r}")

# The bridge dispatches the same nine roles the agent files define; a rename on
# either side silently breaks cross-provider dispatch, so pin them together.
bridge = os.path.join(PLUGIN, "scripts", "flow-agent.py")
if os.path.isfile(bridge):
    with open(bridge, encoding="utf-8") as stream:
        source = stream.read()
    roles = set()
    for line in source.splitlines():
        if line.startswith(("READ_ONLY_ROLES", "WRITE_ROLES")):
            roles |= {chunk.strip().strip('"\'') for chunk in
                      line.partition("{")[2].partition("}")[0].split(",") if chunk.strip()}
    expected = {os.path.splitext(os.path.basename(p))[0].removeprefix("flow-") for p in agents}
    if roles != expected:
        err(f"bridge roles {sorted(roles)} do not match agent files {sorted(expected)}")

for path in glob.glob(os.path.join(PLUGIN, "**", "*"), recursive=True):
    if not os.path.isfile(path):
        continue
    try:
        with open(path, encoding="utf-8") as stream:
            text = stream.read()
    except UnicodeDecodeError:
        continue
    if "${CLAUDE_PLUGIN_ROOT}" in text:
        err(f"{os.path.relpath(path, ROOT)}: contains Claude-only plugin root")
if not os.path.isfile(os.path.join(PLUGIN, "references", "hosts.md")):
    err("portable host contract is missing")
if not os.path.isfile(os.path.join(PLUGIN, "scripts", "flow-agent.py")):
    err("cross-provider bridge is missing")

if errors:
    print("Plugin validation FAILED:")
    for message in errors:
        print(f"  - {message}")
    sys.exit(1)
print(f"Plugin OK: {len(skills)} shared skills, {len(agents)} Claude agents, both hosts valid.")
