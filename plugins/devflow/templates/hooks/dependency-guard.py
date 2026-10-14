#!/usr/bin/env python3
"""PreToolUse (Bash|Edit|Write|MultiEdit) guard: stop a new or changed dependency until a human
approves it, hardening autonomy.md's "dependency added/changed" human gate so it holds even if an
agent ignores its written instructions.

Two triggers:
- An Edit/Write/MultiEdit to a dependency manifest or lockfile (MANIFESTS below) whose result adds
  a dependency or changes one's version. The guard computes the file before and after the edit and
  compares (name, version) entries, so an unrelated edit to the same file (a script, a comment)
  passes. Removing a dependency is not flagged.
- A Bash command that adds packages (`npm install <pkg>`, `uv add`, `dotnet add package`, ...).
  The guard cannot know what the resolver will pick, so naming a package is enough.

A hit is a human gate, never an auto-proceed: the guard returns `permissionDecision: "ask"`, so
Claude Code prompts the human with the package names. In `bypassPermissions` mode no prompt is
guaranteed, so it blocks (exit 2) instead. A manifest the guard cannot parse after the edit is
could-not-check, and gets the same gate.

This is a best-effort backstop layered on top of the still-primary agent-instruction control, so
on an internal error (bad stdin, unexpected exception) it fails open (exit 0) with a clear warning
on stderr, never a silent pass.
"""
import fnmatch
import json
import os
import re
import shlex
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hook_common as common  # noqa: E402

GATE_HINT = (
    "New or changed dependencies are a human gate (autonomy.md). Approve only after checking each "
    "package is the intended one, and record the answer in .planning/DECISIONS.md."
)


def warn(message):
    print(f"dependency-guard: {message}", file=sys.stderr)


class CouldNotParse(Exception):
    pass


# --- parsers: file text -> set of (name, version-or-spec) ----------------------------------

NPM_SECTIONS = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")


def load_json(text):
    if not text.strip():
        return {}
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise CouldNotParse(str(exc))
    if not isinstance(data, dict):
        raise CouldNotParse("top level is not an object")
    return data


def parse_package_json(text):
    data = load_json(text)
    return {(name, str(spec)) for section in NPM_SECTIONS
            for name, spec in (data.get(section) or {}).items()}


def parse_package_lock(text):
    data = load_json(text)
    entries = set()
    for key, info in (data.get("packages") or {}).items():
        if key and isinstance(info, dict):
            entries.add((key.rsplit("node_modules/", 1)[-1], str(info.get("version"))))

    def walk(deps):  # lockfileVersion 1
        for name, info in (deps or {}).items():
            if isinstance(info, dict):
                entries.add((name, str(info.get("version"))))
                walk(info.get("dependencies"))
    walk(data.get("dependencies"))
    return entries


PNPM_KEY_RE = re.compile(r"^  ['\"]?/?((?:@[^/\s'\"]+/)?[^@\s'\"(/]+)[@/]([^:'\"(\s/_]+)")


def parse_pnpm_lock(text):
    entries = set()
    section = None
    for line in text.splitlines():
        if line and not line[0].isspace():
            section = line.rstrip(":").strip()
            continue
        if section in ("packages", "snapshots"):
            match = PNPM_KEY_RE.match(line)
            if match:
                entries.add((match.group(1), match.group(2)))
    return entries


YARN_VERSION_RE = re.compile(r"^\s+version:?\s+\"?([^\"\s]+)\"?")


def parse_yarn_lock(text):
    entries = set()
    names = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace() and line.rstrip().endswith(":"):
            names = []
            for spec in line.rstrip().rstrip(":").split(","):
                spec = spec.strip().strip("\"'")
                at = spec.rfind("@")
                if at > 0 and spec != "__metadata":
                    names.append(spec[:at])
            continue
        version = YARN_VERSION_RE.match(line)
        if version:
            entries.update((name, version.group(1)) for name in names)
            names = []
    return entries


PEP508_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*(.*)$")


def pep508(requirement):
    match = PEP508_NAME_RE.match(requirement)
    if not match:
        return None
    return match.group(1).lower().replace("_", "-"), match.group(2).strip()


def parse_requirements(text):
    entries = set()
    for raw in text.splitlines():
        line = re.split(r"\s#", raw, maxsplit=1)[0].strip()
        if not line or line.startswith(("#", "-")):
            continue
        if "://" in line:
            egg = re.search(r"#egg=([A-Za-z0-9._-]+)", raw)
            entries.add((egg.group(1) if egg else line, line))
            continue
        entry = pep508(line)
        if entry:
            entries.add(entry)
    return entries


# Just enough TOML for dependency tables, stdlib-only on 3.9+ (tomllib is 3.11+): yields
# (table, key, raw_value) per assignment, joining multi-line arrays and inline tables.
TOML_HEADER_RE = re.compile(r"^\s*(\[\[?)\s*([^\]]+?)\s*\]\]?\s*(#.*)?$")
TOML_ASSIGN_RE = re.compile(r"^\s*(\"[^\"]*\"|'[^']*'|[A-Za-z0-9_.-]+)\s*=\s*(.*)$")
TOML_STRING_RE = re.compile(r"\"((?:[^\"\\]|\\.)*)\"|'([^']*)'")


def bracket_depth(value):
    stripped = TOML_STRING_RE.sub("", value).split("#", 1)[0]
    return (stripped.count("[") + stripped.count("{")
            - stripped.count("]") - stripped.count("}"))


def iter_toml(text):
    table, array_table = "", False
    pending = None
    for line in text.splitlines():
        if pending is not None:
            pending[2] += "\n" + line
            pending[3] += bracket_depth(line)
            if pending[3] <= 0:
                yield pending[0], pending[1], pending[2], array_table
                pending = None
            continue
        header = TOML_HEADER_RE.match(line)
        if header:
            table = ".".join(part.strip().strip("\"'") for part in header.group(2).split("."))
            array_table = header.group(1) == "[["
            yield table, None, None, array_table  # table start marker
            continue
        assign = TOML_ASSIGN_RE.match(line)
        if not assign:
            continue
        key, value = assign.group(1).strip("\"'"), assign.group(2).strip()
        depth = bracket_depth(value)
        if depth > 0:
            pending = [table, key, value, depth]
            continue
        yield table, key, value, array_table


def toml_strings(value):
    return [a if a or not b else b for a, b in TOML_STRING_RE.findall(value)]


def toml_scalar(value):
    strings = toml_strings(value)
    return strings[0] if len(strings) == 1 and value.lstrip()[:1] in "\"'" else value.strip()


def parse_pyproject(text):
    entries = set()
    for table, key, value, _ in iter_toml(text):
        if key is None:
            continue
        array_of_reqs = (
            (table == "project" and key == "dependencies")
            or table in ("project.optional-dependencies", "dependency-groups")
            or (table == "tool.uv" and key == "dev-dependencies")
            or (table == "build-system" and key == "requires")
        )
        if array_of_reqs:
            entries.update(e for e in map(pep508, toml_strings(value)) if e)
        elif re.fullmatch(r"tool\.poetry\.(dev-dependencies|dependencies|group\.[^.]+\.dependencies)",
                          table):
            entries.add((key.lower(), toml_scalar(value)))
    return entries


def parse_key_value_tables(pattern):
    """Parser for TOML tables of `name = spec` (Pipfile, Cargo.toml). `[deps.name]` sub-tables
    (Cargo's long form) fold their keys into one spec for `name`."""
    table_re = re.compile(pattern)

    def parse(text):
        specs = {}
        for table, key, value, _ in iter_toml(text):
            if key is None:
                continue
            if table_re.fullmatch(table):
                specs[key] = toml_scalar(value)
                continue
            parent, _, name = table.rpartition(".")
            if parent and table_re.fullmatch(parent):
                specs[name] = (specs.get(name, "") + f" {key}={value}").strip()
        return set(specs.items())
    return parse


def parse_toml_package_list(text):
    """`[[package]]` name/version records (poetry.lock, uv.lock, Cargo.lock)."""
    entries = set()
    record = None
    for table, key, value, array_table in iter_toml(text):
        if key is None:
            if record and "name" in record:
                entries.add((record["name"], record.get("version", "")))
            record = {} if (table == "package" and array_table) else None
            continue
        if record is not None and table == "package" and key in ("name", "version"):
            record[key] = toml_scalar(value)
    if record and "name" in record:
        entries.add((record["name"], record.get("version", "")))
    return entries


def parse_pipfile_lock(text):
    data = load_json(text)
    return {(name, str((info or {}).get("version")))
            for section in ("default", "develop")
            for name, info in (data.get(section) or {}).items()}


MSBUILD_ITEM_RE = re.compile(
    r"<(PackageReference|PackageVersion|GlobalPackageReference)\b([^>]*?)(/?)>", re.S)
MSBUILD_ATTR_RE = re.compile(r"(\w+)\s*=\s*\"([^\"]*)\"")
MSBUILD_VERSION_EL_RE = re.compile(r"<(Version|VersionOverride)>\s*([^<]*?)\s*</\1>")


def parse_msbuild(text):
    entries = set()
    for match in MSBUILD_ITEM_RE.finditer(text):
        attrs = dict(MSBUILD_ATTR_RE.findall(match.group(2)))
        name = attrs.get("Include") or attrs.get("Update")
        if not name:
            continue
        version = attrs.get("Version") or attrs.get("VersionOverride")
        if version is None and not match.group(3):
            close = text.find(f"</{match.group(1)}>", match.end())
            element = MSBUILD_VERSION_EL_RE.search(text, match.end(), close if close >= 0 else None)
            version = element.group(2) if element else None
        entries.add((name, version or ""))
    return entries


def parse_nuget_lock(text):
    data = load_json(text)
    return {(name, str((info or {}).get("resolved")))
            for framework in (data.get("dependencies") or {}).values()
            for name, info in (framework or {}).items()}


GO_REQUIRE_RE = re.compile(r"^\s*(?:require\s+)?(\S+)\s+(v\S+)")


def parse_go_mod(text):
    entries = set()
    in_block = False
    for raw in text.splitlines():
        line = raw.split("//", 1)[0].strip()
        if line.startswith("require ("):
            in_block = True
            continue
        if in_block and line == ")":
            in_block = False
            continue
        if in_block or line.startswith("require "):
            match = GO_REQUIRE_RE.match(line)
            if match:
                entries.add((match.group(1), match.group(2)))
    return entries


def parse_go_sum(text):
    entries = set()
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            entries.add((parts[0], parts[1].split("/", 1)[0]))
    return entries


# The one manifest table: filename glob -> parser. `.planning/config.json`'s
# `dependency_manifests` (a glob list) replaces the glob list; a configured glob with no parser
# here gates on any content change, since its entries cannot be itemized.
MANIFESTS = (
    ("package.json", parse_package_json),
    ("package-lock.json", parse_package_lock),
    ("pnpm-lock.yaml", parse_pnpm_lock),
    ("yarn.lock", parse_yarn_lock),
    ("requirements*.txt", parse_requirements),
    ("pyproject.toml", parse_pyproject),
    ("poetry.lock", parse_toml_package_list),
    ("uv.lock", parse_toml_package_list),
    ("Pipfile", parse_key_value_tables(r"packages|dev-packages")),
    ("Pipfile.lock", parse_pipfile_lock),
    ("*.csproj", parse_msbuild),
    ("Directory.Packages.props", parse_msbuild),
    ("packages.lock.json", parse_nuget_lock),
    ("Cargo.toml", parse_key_value_tables(
        r"(workspace\.|target\.[^\]]+\.)?(dependencies|dev-dependencies|build-dependencies)")),
    ("Cargo.lock", parse_toml_package_list),
    ("go.mod", parse_go_mod),
    ("go.sum", parse_go_sum),
)


def manifest_globs(cwd):
    config = common.read_planning_config(cwd, warn) or {}
    configured = config.get("dependency_manifests")
    if isinstance(configured, list) and all(isinstance(g, str) for g in configured):
        return configured
    return [glob for glob, _ in MANIFESTS]


def matching_glob(path, globs):
    name = os.path.basename(path)
    for glob in globs:
        target = os.path.normpath(path) if "/" in glob else name
        if fnmatch.fnmatch(target, glob):
            return glob
    return None


def parser_for(path):
    name = os.path.basename(path)
    for glob, parser in MANIFESTS:
        if fnmatch.fnmatch(name, glob):
            return parser
    return None


# --- file edits ---------------------------------------------------------------------------

def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as stream:
            return stream.read()
    except FileNotFoundError:
        return ""


def apply_edit(text, edit):
    """Apply one Edit/MultiEdit step, or None when old_string is absent (the tool will fail)."""
    old = edit.get("old_string") or ""
    new = edit.get("new_string") or ""
    if not old:
        return new if not text else None
    if old not in text:
        return None
    return text.replace(old, new) if edit.get("replace_all") else text.replace(old, new, 1)


def after_text(tool_input, before):
    if "content" in tool_input:
        return tool_input.get("content") or ""
    edits = tool_input.get("edits")
    steps = edits if isinstance(edits, list) else [tool_input]
    text = before
    for step in steps:
        text = apply_edit(text, step)
        if text is None:
            return None
    return text


def describe_changes(before_entries, after_entries):
    before_versions = {}
    for name, version in before_entries:
        before_versions.setdefault(name, set()).add(version)
    added, changed = [], []
    for name, version in sorted(after_entries - before_entries):
        if name in before_versions:
            old = ", ".join(sorted(before_versions[name]))
            changed.append(f"{name} {old} -> {version}")
        else:
            added.append(f"{name} {version}".strip())
    return added, changed


def check_file_edit(tool_input, cwd):
    file_path = tool_input.get("file_path")
    if not file_path:
        return None
    absolute = file_path if os.path.isabs(file_path) else os.path.join(cwd, file_path)
    try:
        relative = os.path.relpath(absolute, cwd)
    except ValueError:
        relative = file_path
    if matching_glob(relative, manifest_globs(cwd)) is None:
        return None

    before = read_text(absolute)
    after = after_text(tool_input, before)
    if after is None or after == before:
        return None

    parser = parser_for(absolute)
    if parser is None:
        return f"{relative} is a configured dependency manifest and this edit changes it."
    try:
        after_entries = parser(after)
    except CouldNotParse as exc:
        return (f"{relative} could not be parsed after this edit ({exc}), so new or changed "
                "dependencies could not be ruled out (could-not-check).")
    try:
        before_entries = parser(before)
    except CouldNotParse:
        before_entries = set()
    added, changed = describe_changes(before_entries, after_entries)
    if not added and not changed:
        return None
    parts = []
    if added:
        parts.append("adds " + "; ".join(added))
    if changed:
        parts.append("changes " + "; ".join(changed))
    return f"{relative}: this edit " + " and ".join(parts) + "."


# --- Bash package-add commands --------------------------------------------------------------

SEGMENT_SPLIT_RE = re.compile(r"&&|\|\||[;|&\n]")
ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
WRAPPERS = {"sudo", "command", "exec", "env", "time", "nohup"}
PIP_VALUE_FLAGS = {"-r", "--requirement", "-c", "--constraint", "-e", "--editable", "-i",
                   "--index-url", "--extra-index-url", "-t", "--target", "-f", "--find-links",
                   "--prefix", "--root", "--python"}
PIP_NOT_PACKAGES = re.compile(r"^(\.|\.\.|\.?\.?/.*|.*\.txt)$")


def package_args(args, value_flags=frozenset()):
    packages, skip = [], False
    for arg in args:
        if skip:
            skip = False
            continue
        if arg.startswith("-"):
            skip = arg in value_flags
            continue
        packages.append(arg)
    return packages


def pip_packages(args):
    return [a for a in package_args(args, PIP_VALUE_FLAGS) if not PIP_NOT_PACKAGES.match(a)]


def packages_added_by(tokens):
    """Package names a single command adds, or [] if it is not a package-add command."""
    while tokens and (ENV_ASSIGN_RE.match(tokens[0]) or tokens[0] in WRAPPERS):
        tokens = tokens[1:]
    if not tokens:
        return []
    tool, rest = os.path.basename(tokens[0]), tokens[1:]
    sub = rest[0] if rest else ""
    if tool in ("python", "python3") and rest[:2] == ["-m", "pip"]:
        tool, rest = "pip", rest[2:]
        sub = rest[0] if rest else ""
    if tool in ("npm", "pnpm") and sub in ("install", "i", "add"):
        return package_args(rest[1:])
    if tool == "yarn" and sub == "add":
        return package_args(rest[1:])
    if tool == "yarn" and rest[:2] == ["global", "add"]:
        return package_args(rest[2:])
    if tool in ("pip", "pip3") and sub == "install":
        return pip_packages(rest[1:])
    if tool == "uv" and sub == "add":
        return package_args(rest[1:])
    if tool == "uv" and rest[:2] == ["pip", "install"]:
        return pip_packages(rest[2:])
    if tool in ("poetry", "cargo") and sub == "add":
        return package_args(rest[1:])
    if tool == "pipenv" and sub == "install":
        return pip_packages(rest[1:])
    if tool == "go" and sub == "get":
        return package_args(rest[1:])
    if tool == "dotnet" and sub == "add" and "package" in rest:
        after = rest[rest.index("package") + 1:]
        names = package_args(after, {"-v", "--version", "-s", "--source", "-f", "--framework"})
        version = next((after[i + 1] for i, a in enumerate(after[:-1])
                        if a in ("-v", "--version")), None)
        return [f"{names[0]} {version}" if version else names[0]] if names else []
    return []


def check_bash(command):
    packages = []
    for segment in SEGMENT_SPLIT_RE.split(command):
        try:
            tokens = shlex.split(segment)
        except ValueError:
            tokens = segment.split()
        packages.extend(packages_added_by(tokens))
    if not packages:
        return None
    return "this command adds packages: " + ", ".join(packages) + "."


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as exc:
        warn(f"could not parse stdin JSON: {exc}")
        return 0

    tool_input = payload.get("tool_input") or {}
    cwd = payload.get("cwd") or os.getcwd()
    if "command" in tool_input:
        finding = check_bash(tool_input.get("command") or "")
    else:
        finding = check_file_edit(tool_input, cwd)
    if finding is None:
        return 0

    reason = f"Dependency gate: {finding} {GATE_HINT}"
    if payload.get("permission_mode") == "bypassPermissions":
        # No permission prompt is guaranteed in this mode, so "ask" could auto-proceed.
        print(f"Blocked: {reason} Make the change yourself or rerun outside bypassPermissions.",
              file=sys.stderr)
        return 2
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": reason,
    }}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail open, loud — never a silent pass
        warn(f"unexpected error: {exc}")
        sys.exit(0)
