#!/usr/bin/env python3
"""Validate both DevFlow host packages and their shared portable payload."""

import glob
import json
import os
import re
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
if len(skills) != 22:
    err(f"expected 22 skills, found {len(skills)}")
if len(agents) != 12:
    err(f"expected 12 Claude role agents, found {len(agents)}")
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

# The bridge dispatches the same roles the agent files define; a rename on either
# side silently breaks cross-provider dispatch, so pin them together. Parse the two
# sets SEPARATELY: unioning them would let a role move from read-only to write
# without tripping anything, which is exactly the change most worth catching.
bridge = os.path.join(PLUGIN, "scripts", "flow-agent.py")
role_sets = {}
if os.path.isfile(bridge):
    with open(bridge, encoding="utf-8") as stream:
        source = stream.read()
    # Match the whole brace literal, not the first line of it: these sets wrap as they
    # grow, and a line-based read would silently see a truncated set.
    for key in ("READ_ONLY_ROLES", "WRITE_ROLES"):
        m = re.search(rf"^{key}\s*=\s*\{{([^}}]*)\}}", source, re.M | re.S)
        if m:
            role_sets[key] = {chunk.strip().strip('"\'') for chunk in m.group(1).split(",")
                              if chunk.strip()}
    roles = role_sets.get("READ_ONLY_ROLES", set()) | role_sets.get("WRITE_ROLES", set())
    expected = {os.path.splitext(os.path.basename(p))[0].removeprefix("flow-") for p in agents}
    if roles != expected:
        err(f"bridge roles {sorted(roles)} do not match agent files {sorted(expected)}")
    overlap = role_sets.get("READ_ONLY_ROLES", set()) & role_sets.get("WRITE_ROLES", set())
    if overlap:
        err(f"roles in both READ_ONLY_ROLES and WRITE_ROLES: {sorted(overlap)}")

    # A read-only role that can Write or Edit is read-only in name only. The bridge
    # sandboxes it on the cross-provider path (`--sandbox read-only`), but a natively
    # spawned agent gets exactly the tools its frontmatter lists — so the frontmatter
    # is the only thing enforcing this, and nothing was checking the frontmatter.
    WRITE_TOOLS = {"write", "edit", "notebookedit", "multiedit"}
    for path in agents:
        role = os.path.splitext(os.path.basename(path))[0].removeprefix("flow-")
        if role not in role_sets.get("READ_ONLY_ROLES", set()):
            continue
        tools = {t.strip().lower() for t in (frontmatter(path).get("tools") or "").split(",")}
        offenders = sorted(tools & WRITE_TOOLS)
        if offenders:
            err(f"{os.path.relpath(path, ROOT)}: read-only role declares write tools {offenders}")

    # references/hosts.md restates both lists in prose — a third copy that drifts silently.
    hosts = os.path.join(PLUGIN, "references", "hosts.md")
    if os.path.isfile(hosts) and role_sets:
        with open(hosts, encoding="utf-8") as stream:
            hosts_text = stream.read()
        # The prose wraps, so "Write\nroles:" is one phrase across two lines.
        for key, label, pattern in (
            ("READ_ONLY_ROLES", "Read-only roles", r"Read-only\s+roles"),
            ("WRITE_ROLES", "Write roles", r"Write\s+roles"),
        ):
            m = re.search(rf"{pattern}:\s*([^.]+)", hosts_text)
            if not m:
                err(f"references/hosts.md: missing the '{label}' list")
            else:
                listed = {c.strip().strip("`") for c in m.group(1).split(",") if c.strip()}
                if listed != role_sets.get(key, set()):
                    err(f"references/hosts.md '{label}' {sorted(listed)} "
                        f"does not match {key} {sorted(role_sets.get(key, set()))}")

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
    # Skills and agents load doctrine by {devflow_root}-relative path. A pointer to a
    # file that does not exist fails at runtime inside a subagent, where it reads as
    # the agent being unhelpful rather than as a broken link — so resolve them here.
    # `*` and a bare directory are legitimate (glob placeholders, directory references).
    for ref in re.findall(r"\{devflow_root\}/([A-Za-z0-9_./*-]+)", text):
        if "*" in ref or ref.endswith("/"):
            continue
        if not os.path.exists(os.path.join(PLUGIN, ref)):
            err(f"{os.path.relpath(path, ROOT)}: dangling reference {{devflow_root}}/{ref}")
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
