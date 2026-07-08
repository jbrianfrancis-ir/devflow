#!/usr/bin/env python3
"""Validate the DevFlow plugin: JSON manifests + skill/agent frontmatter.

Zero dependencies (stdlib only). Run locally with `python3 scripts/validate-plugin.py`;
CI runs the same. Exits non-zero on any error.
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
errors = []


def err(msg):
    errors.append(msg)


def load_json(rel):
    full = os.path.join(ROOT, rel)
    if not os.path.isfile(full):
        err(f"{rel}: missing")
        return None
    try:
        with open(full) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        err(f"{rel}: invalid JSON — {e}")
        return None


def frontmatter(path):
    """Top-level scalar keys from a `---` fenced YAML header (flat frontmatter only)."""
    with open(path) as f:
        text = f.read()
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fm = {}
    for line in text[3:end].strip("\n").splitlines():
        if line and not line.startswith((" ", "\t", "#")) and ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


# 1. plugin.json
plugin = load_json(".claude-plugin/plugin.json")
if plugin:
    for k in ("name", "version", "description", "skills", "agents"):
        if k not in plugin:
            err(f"plugin.json: missing key '{k}'")

# 2. marketplace.json
mkt = load_json(".claude-plugin/marketplace.json")
if mkt:
    plugins = mkt.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        err("marketplace.json: 'plugins' must be a non-empty array")
    else:
        for p in plugins:
            for k in ("name", "source", "version"):
                if k not in p:
                    err(f"marketplace.json: plugin entry missing '{k}'")

# 3. skills — frontmatter name must match the directory
skills = sorted(glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")))
if not skills:
    err("no skills found under skills/*/SKILL.md")
for path in skills:
    rel = os.path.relpath(path, ROOT)
    d = os.path.basename(os.path.dirname(path))
    fm = frontmatter(path)
    if fm is None:
        err(f"{rel}: missing or malformed frontmatter")
        continue
    if not fm.get("name"):
        err(f"{rel}: frontmatter missing 'name'")
    elif fm["name"] != d:
        err(f"{rel}: name '{fm['name']}' != directory '{d}'")
    if not fm.get("description"):
        err(f"{rel}: frontmatter missing 'description'")

# 4. agents — frontmatter name must match the filename; tools required
agents = sorted(glob.glob(os.path.join(ROOT, "agents", "*.md")))
if not agents:
    err("no agents found under agents/*.md")
for path in agents:
    rel = os.path.relpath(path, ROOT)
    name = os.path.splitext(os.path.basename(path))[0]
    fm = frontmatter(path)
    if fm is None:
        err(f"{rel}: missing or malformed frontmatter")
        continue
    if fm.get("name") != name:
        err(f"{rel}: name '{fm.get('name')}' != filename '{name}'")
    if not fm.get("description"):
        err(f"{rel}: frontmatter missing 'description'")
    if not fm.get("tools"):
        err(f"{rel}: frontmatter missing 'tools'")

if errors:
    print("Plugin validation FAILED:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
print(f"Plugin OK: {len(skills)} skills, {len(agents)} agents, manifests valid.")
