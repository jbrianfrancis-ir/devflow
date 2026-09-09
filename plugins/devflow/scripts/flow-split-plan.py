#!/usr/bin/env python3
"""Split one over-cap plan in a phase directory into two, renumbering the tail.

Inserts the new plan immediately after the source plan: every existing plan numbered
higher than the source shifts up by one (filename, `plan:` field, and every `NN-MM`
reference in any plan's frontmatter or prose that names a shifted plan). All-or-nothing —
nothing is written unless the computed result is provably free of dangling references.

Stdlib only (ARCHITECTURE.md: Python 3.9+, no dependencies). Plan frontmatter is a small,
known shape (see plan-format.md), so this parses only the fields it needs with
line-oriented code — not a general YAML parser.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

PLAN_FILENAME_RE = re.compile(r"^(\d+)-(\d+)-PLAN\.md$")
NN_MM_RE = re.compile(r"\b(\d{2,})-(\d{2,})\b")
LIST_ITEM_RE = re.compile(r"^(\s*)-\s?(.*)$")
KEY_RE = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")
PLAN_FIELD_RE = re.compile(r"(?m)^plan:\s*\d+\s*$")
TASK_RE = re.compile(r"<task\b[^>]*>.*?</task>", re.S)
FILES_TAG_RE = re.compile(r"<files>(.*?)</files>", re.S)
NAME_TAG_RE = re.compile(r"(<name>\s*Task )\d+(\s*:)")
TASKS_BLOCK_RE = re.compile(r"<tasks>.*?</tasks>", re.S)
OBJECTIVE_RE = re.compile(r"<objective>.*?</objective>", re.S)
CONTEXT_RE = re.compile(r"<context>.*?</context>", re.S)


class PlanError(Exception):
    """Fail-closed: an unreadable plan, unparseable frontmatter, or a failed git mv."""


# --- frontmatter: small, known shape, line-oriented (no general YAML parser) ----------

def split_frontmatter(text: str) -> tuple[str, str, str]:
    """Return (preamble, frontmatter_text, body). `preamble` is everything before the
    opening '---' — the HTML path comment templates/plan.md puts on line 1, blank lines,
    anything — so a real plan's leading comment is never mistaken for a parse failure."""
    lines = text.splitlines(keepends=True)
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            start = i
            break
    if start is None:
        raise PlanError("missing frontmatter opening '---'")
    end = None
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise PlanError("missing frontmatter closing '---'")
    return "".join(lines[:start]), "".join(lines[start + 1:end]), "".join(lines[end + 1:])


def parse_yaml_lite(fm_text: str) -> dict:
    lines = fm_text.splitlines()
    pos = 0

    def parse_block(indent: int) -> dict:
        nonlocal pos
        result: dict = {}
        while pos < len(lines):
            line = lines[pos]
            if not line.strip():
                pos += 1
                continue
            m = KEY_RE.match(line)
            if not m or len(m.group(1)) != indent:
                break
            key, val = m.group(2), m.group(3).strip()
            pos += 1
            if val == "":
                if pos < len(lines) and (lm := LIST_ITEM_RE.match(lines[pos])) and \
                        lines[pos].strip() and len(lm.group(1)) >= indent:
                    items = []
                    while pos < len(lines):
                        lm = LIST_ITEM_RE.match(lines[pos])
                        if not lm or not lines[pos].strip() or len(lm.group(1)) < indent:
                            break
                        items.append(lm.group(2))
                        pos += 1
                    result[key] = items
                elif pos < len(lines) and (km := KEY_RE.match(lines[pos])) and \
                        lines[pos].strip() and len(km.group(1)) > indent:
                    result[key] = parse_block(len(km.group(1)))
                else:
                    result[key] = []
            elif val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                result[key] = [x.strip() for x in inner.split(",")] if inner else []
            else:
                result[key] = val
        return result

    return parse_block(0)


def dequote(item: str) -> str:
    item = item.strip()
    if len(item) >= 2 and item[0] == '"' and item[-1] == '"':
        return item[1:-1].replace('\\"', '"')
    return item


def enquote(item: str) -> str:
    return '"' + item.replace('"', '\\"') + '"'


def format_inline(key: str, items: list[str]) -> str:
    return f"{key}: [{', '.join(items)}]\n"


def format_block(key: str, items: list[str], indent: str = "") -> str:
    if not items:
        return f"{indent}{key}: []\n"
    out = [f"{indent}{key}:\n"]
    out.extend(f"{indent}  - {it}\n" for it in items)
    return "".join(out)


def format_must_haves(mh: dict) -> str:
    out = ["must_haves:\n"]
    out.append(format_block("truths", [enquote(t) for t in mh.get("truths", [])], "  "))
    if "backstop_truths" in mh:
        out.append(format_block("backstop_truths",
                                 [enquote(t) for t in mh.get("backstop_truths", [])], "  "))
    out.append(format_block("artifacts", mh.get("artifacts", []), "  "))
    out.append(format_block("key_links", [enquote(t) for t in mh.get("key_links", [])], "  "))
    return "".join(out)


MODELLED_KEYS = {"phase", "plan", "wave", "depends_on", "files_modified", "autonomous",
                  "requirements", "must_haves"}


def format_extra_field(key: str, value, indent: str = "") -> str:
    """Re-emit a key this tool does not model, in whatever shape parse_yaml_lite gave it
    back (scalar / inline-or-block list / nested block), so nothing unmodelled is lost."""
    if isinstance(value, dict):
        out = [f"{indent}{key}:\n"]
        for k, v in value.items():
            out.append(format_extra_field(k, v, indent + "  "))
        return "".join(out)
    if isinstance(value, list):
        return format_block(key, value, indent)
    return f"{indent}{key}: {value}\n"


def format_frontmatter(phase: str, plan_num: str, wave: str, depends_on: list[str],
                        files_modified: list[str], autonomous: str, requirements: list[str],
                        must_haves: dict, extra: dict | None = None) -> str:
    parts = [f"phase: {phase}\n", f"plan: {plan_num}\n", f"wave: {wave}\n",
              format_inline("depends_on", depends_on),
              format_block("files_modified", files_modified),
              f"autonomous: {autonomous}\n",
              format_inline("requirements", requirements),
              format_must_haves(must_haves)]
    # Unmodelled keys (e.g. `user_setup`: external setup — accounts, secrets — a human must
    # do before execution) are carried through verbatim in their original order. Silently
    # dropping user_setup would start a phase's execution without surfacing what the human
    # still has to configure, so any key this tool does not model must survive the split.
    for key, value in (extra or {}).items():
        parts.append(format_extra_field(key, value))
    return "---\n" + "".join(parts) + "---\n"


# --- plan discovery -------------------------------------------------------------------

def discover_plans(phase_dir: Path) -> tuple[str, int, dict[int, Path]]:
    plans: dict[int, Path] = {}
    prefixes: set[str] = set()
    widths: set[int] = set()
    for path in sorted(phase_dir.iterdir()):
        m = PLAN_FILENAME_RE.match(path.name)
        if not m:
            continue
        prefixes.add(m.group(1))
        widths.add(len(m.group(2)))
        plans[int(m.group(2))] = path
    if not plans:
        raise PlanError(f"no NN-MM-PLAN.md files found in {phase_dir}")
    if len(prefixes) != 1:
        raise PlanError(f"inconsistent phase prefixes in filenames: {sorted(prefixes)}")
    if len(widths) != 1:
        raise PlanError(f"inconsistent plan-number width in filenames: {sorted(widths)}")
    return next(iter(prefixes)), next(iter(widths)), plans


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PlanError(f"could not read {path}: {exc}") from exc


# --- task extraction/renumbering --------------------------------------------------------

def extract_tasks(body: str) -> tuple[str, list[dict]]:
    tm = TASKS_BLOCK_RE.search(body)
    if not tm:
        raise PlanError("plan body has no <tasks>...</tasks> block")
    tasks_block = tm.group(0)
    tasks = []
    for match in TASK_RE.finditer(tasks_block):
        block = match.group(0)
        files_m = FILES_TAG_RE.search(block)
        files = [f.strip() for f in files_m.group(1).split(",")] if files_m else []
        tasks.append({"text": block, "files": [f for f in files if f]})
    if not tasks:
        raise PlanError("plan body has no <task> entries inside <tasks>")
    return tasks_block, tasks


def renumber(task_text: str, new_index: int) -> str:
    return NAME_TAG_RE.sub(rf"\g<1>{new_index}\g<2>", task_text, count=1)


def build_tasks_section(task_texts: list[str]) -> str:
    return "<tasks>\n\n" + "\n\n".join(task_texts) + "\n\n</tasks>"


# --- rename map + reference rewriting ---------------------------------------------------

def compute_rename_map(prefix: str, numbers: list[int], src_num: int, width: int) -> dict[str, str]:
    mapping = {}
    for n in numbers:
        if n > src_num:
            old_id = f"{prefix}-{n:0{width}d}"
            new_id = f"{prefix}-{n + 1:0{width}d}"
            mapping[old_id] = new_id
    return mapping


def rewrite_refs(text: str, rename_map: dict[str, str]) -> str:
    return NN_MM_RE.sub(lambda m: rename_map.get(m.group(0), m.group(0)), text)


def rewrite_header_comment(text: str, old_name: str, new_name: str) -> str:
    lines = text.splitlines(keepends=True)
    if lines and lines[0].lstrip().startswith("<!--") and old_name in lines[0]:
        lines[0] = lines[0].replace(old_name, new_name)
    return "".join(lines)


# --- validation (all-or-nothing gate) ---------------------------------------------------

def validate(final: dict[str, dict]) -> list[str]:
    """final: id -> {"text": str, "wave": int, "depends_on": [ids]}. Returns problems;
    empty list means the result is safe to write."""
    problems = []
    ids = set(final)
    for pid, data in final.items():
        for token in {m.group(0) for m in NN_MM_RE.finditer(data["text"])}:
            if token not in ids:
                problems.append(f"{pid}: dangling reference to nonexistent plan {token}")
        for dep in data["depends_on"]:
            if dep not in ids:
                problems.append(f"{pid}: depends_on references nonexistent plan {dep}")
    for pid, data in final.items():
        if any(dep not in final for dep in data["depends_on"]):
            continue  # already reported above
        expected = 1 if not data["depends_on"] else max(final[d]["wave"] for d in data["depends_on"]) + 1
        if data["wave"] != expected:
            problems.append(f"{pid}: wave {data['wave']} violates wave = max(dependency wave) + 1 "
                             f"(expected {expected})")
    return problems


def extract_depends_on(text: str) -> list[str]:
    m = re.search(r"(?m)^depends_on:\s*\[([^\]]*)\]", text)
    if not m:
        return []
    inner = m.group(1).strip()
    return [x.strip() for x in inner.split(",")] if inner else []


def extract_wave(text: str) -> int:
    m = re.search(r"(?m)^wave:\s*(\d+)", text)
    if not m:
        raise PlanError("plan has no wave: field")
    return int(m.group(1))


# --- git ---------------------------------------------------------------------------------

def is_git_repo(phase_dir: Path) -> bool:
    result = subprocess.run(["git", "-C", str(phase_dir), "rev-parse", "--is-inside-work-tree"],
                             capture_output=True, text=True)
    return result.returncode == 0 and result.stdout.strip() == "true"


def git_mv(repo_dir: Path, src: Path, dst: Path) -> None:
    result = subprocess.run(["git", "-C", str(repo_dir), "mv", str(src), str(dst)],
                             capture_output=True, text=True)
    if result.returncode != 0:
        raise PlanError(f"git mv {src} -> {dst} failed: {result.stderr.strip()}")


# --- main ----------------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase_dir", help="directory containing NN-MM-PLAN.md files")
    parser.add_argument("plan", help="plan number to split, e.g. 02 (or the full id 01-02)")
    parser.add_argument("--after", type=int, required=True, metavar="K",
                        help="tasks 1..K stay on the source plan; tasks K+1..N move to the new plan")
    parser.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    return parser.parse_args()


def resolve_plan_arg(raw: str) -> int:
    tail = raw.rsplit("-", 1)[-1] if "-" in raw else raw
    if not tail.isdigit():
        raise PlanError(f"unrecognised plan id: {raw!r}")
    return int(tail)


def main() -> int:
    args = parse_args()
    phase_dir = Path(args.phase_dir).resolve()
    if not phase_dir.is_dir():
        print(f"error: {phase_dir} is not a directory", file=sys.stderr)
        return 2

    try:
        prefix, width, plans = discover_plans(phase_dir)
        src_num = resolve_plan_arg(args.plan)
        if src_num not in plans:
            raise PlanError(f"plan {src_num} not found among {sorted(plans)}")
        src_path = plans[src_num]
        src_text = read_text(src_path)
        src_preamble, src_fm_text, src_body = split_frontmatter(src_text)
        src_data = parse_yaml_lite(src_fm_text)
        extra_fields = {k: v for k, v in src_data.items() if k not in MODELLED_KEYS}

        tasks_block, tasks = extract_tasks(src_body)
        if not (0 < args.after < len(tasks)):
            raise PlanError(f"--after must be between 1 and {len(tasks) - 1} "
                            f"(plan {src_num} has {len(tasks)} tasks)")
        staying_tasks, moving_tasks = tasks[:args.after], tasks[args.after:]
        staying_files = {f for t in staying_tasks for f in t["files"]}
        moving_files = {f for t in moving_tasks for f in t["files"]}
        moved_only = moving_files - staying_files

        warnings: list[str] = []

        orig_files = src_data.get("files_modified", [])
        new_files, kept_files = [], []
        for f in orig_files:
            if f in moved_only:
                new_files.append(f)
                continue
            kept_files.append(f)
            if f in moving_files and f in staying_files:
                warnings.append(f"files_modified entry {f!r}: touched by both staying and "
                                "moved tasks — left on source")
            elif f not in staying_files and f not in moving_files:
                warnings.append(f"files_modified entry {f!r}: not attributable to any task "
                                "— left on source")

        def split_list(items: list[str], path_like: bool) -> tuple[list[str], list[str]]:
            new_items, kept_items = [], []
            for raw in items:
                text = dequote(raw)
                if path_like:
                    hit_moved, hit_staying = text in moved_only, text in staying_files
                else:
                    hit_moved = any(f in text for f in moved_only)
                    hit_staying = any(f in text for f in staying_files)
                if hit_moved and not hit_staying:
                    new_items.append(text)
                else:
                    kept_items.append(text)
                    if hit_moved and hit_staying:
                        warnings.append(f"must_haves entry {text!r}: references both staying "
                                        "and moved files — left on source")
                    elif not hit_moved and not hit_staying:
                        warnings.append(f"must_haves entry {text!r}: not attributable to "
                                        "moved or staying files — left on source")
            return new_items, kept_items

        mh = src_data.get("must_haves", {})
        new_truths, kept_truths = split_list(mh.get("truths", []), path_like=False)
        new_backstop, kept_backstop = split_list(mh.get("backstop_truths", []), path_like=False) \
            if "backstop_truths" in mh else ([], [])
        new_artifacts, kept_artifacts = split_list(mh.get("artifacts", []), path_like=True)
        new_links, kept_links = split_list(mh.get("key_links", []), path_like=False)

        new_mh = {"truths": new_truths, "artifacts": new_artifacts, "key_links": new_links}
        kept_mh = {"truths": kept_truths, "artifacts": kept_artifacts, "key_links": kept_links}
        if "backstop_truths" in mh:
            new_mh["backstop_truths"] = new_backstop
            kept_mh["backstop_truths"] = kept_backstop

        new_num = src_num + 1
        fmt = lambda n: f"{n:0{width}d}"
        new_id = f"{prefix}-{fmt(new_num)}"
        src_id = f"{prefix}-{fmt(src_num)}"

        new_task_texts = [renumber(t["text"], i + 1) for i, t in enumerate(moving_tasks)]
        new_tasks_section = build_tasks_section(new_task_texts)
        kept_tasks_section = build_tasks_section([t["text"] for t in staying_tasks])

        obj_m = OBJECTIVE_RE.search(src_body)
        ctx_m = CONTEXT_RE.search(src_body)
        objective = obj_m.group(0) if obj_m else "<objective>Split from " + src_id + ".</objective>"
        context = ctx_m.group(0) if ctx_m else "<context></context>"

        new_body = "\n" + objective + "\n\n" + context + "\n\n" + new_tasks_section + "\n"
        new_fm = format_frontmatter(
            phase=src_data.get("phase", ""), plan_num=fmt(new_num), wave=src_data.get("wave", "1"),
            depends_on=src_data.get("depends_on", []), files_modified=new_files,
            autonomous=src_data.get("autonomous", "true"),
            requirements=src_data.get("requirements", []), must_haves=new_mh,
            extra=extra_fields)
        new_path = phase_dir / f"{prefix}-{fmt(new_num)}-PLAN.md"
        # The new plan is a fresh file: give it the source's own preamble (HTML path
        # comment) rewritten to name its own filename, or no preamble if the source had
        # none — a plan with no preamble must still split cleanly.
        new_preamble = rewrite_header_comment(src_preamble, src_path.name, new_path.name)
        new_text = new_preamble + new_fm + new_body

        src_body_out = src_body[:TASKS_BLOCK_RE.search(src_body).start()] + kept_tasks_section + \
            src_body[TASKS_BLOCK_RE.search(src_body).end():]
        src_fm_out = format_frontmatter(
            phase=src_data.get("phase", ""), plan_num=fmt(src_num), wave=src_data.get("wave", "1"),
            depends_on=src_data.get("depends_on", []), files_modified=kept_files,
            autonomous=src_data.get("autonomous", "true"),
            requirements=src_data.get("requirements", []), must_haves=kept_mh,
            extra=extra_fields)
        src_text_out = src_preamble + src_fm_out + src_body_out

        rename_map = compute_rename_map(prefix, list(plans), src_num, width)

        # final[id] -> {"text", "wave", "depends_on", "write_path", "old_path"}
        final: dict[str, dict] = {}

        src_text_out = rewrite_refs(src_text_out, rename_map)
        final[src_id] = {"text": src_text_out, "wave": extract_wave(src_text_out),
                          "depends_on": extract_depends_on(src_text_out),
                          "write_path": src_path, "old_path": src_path}

        new_text = rewrite_refs(new_text, rename_map)
        final[new_id] = {"text": new_text, "wave": extract_wave(new_text),
                          "depends_on": extract_depends_on(new_text),
                          "write_path": new_path, "old_path": None}

        for num, path in plans.items():
            if num == src_num:
                continue
            text = read_text(path)
            split_frontmatter(text)  # fail-closed on unparseable frontmatter; preamble kept as-is
            if num > src_num:
                text = PLAN_FIELD_RE.sub(f"plan: {fmt(num + 1)}", text, count=1)
                target_path = phase_dir / f"{prefix}-{fmt(num + 1)}-PLAN.md"
                text = rewrite_header_comment(text, path.name, target_path.name)
            else:
                target_path = path
            text = rewrite_refs(text, rename_map)
            pid = f"{prefix}-{fmt(num if num <= src_num else num + 1)}"
            final[pid] = {"text": text, "wave": extract_wave(text),
                          "depends_on": extract_depends_on(text),
                          "write_path": target_path, "old_path": path}

        problems = validate(final)
        if problems:
            print("refusing to write: split would leave dangling references", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            return 2

        for w in warnings:
            print(f"warning: {w}")

        if args.dry_run:
            print(f"dry run: would split {src_id} after task {args.after} into {src_id} + {new_id}")
            for pid, data in sorted(final.items()):
                action = "create" if data["old_path"] is None else (
                    "rename+rewrite" if data["old_path"] != data["write_path"] else
                    ("rewrite" if data["text"] != read_text(data["old_path"]) else "unchanged"))
                print(f"  {pid}: {action} -> {data['write_path']} "
                      f"({len(data['text'].encode('utf-8'))} bytes)")
            return 0

        # Rename existing tail files highest-number-first so targets never collide.
        renamed: list[tuple[Path, Path]] = []
        in_git = is_git_repo(phase_dir)
        try:
            for num in sorted((n for n in plans if n > src_num), reverse=True):
                old_path = plans[num]
                target_path = phase_dir / f"{prefix}-{fmt(num + 1)}-PLAN.md"
                if in_git:
                    git_mv(phase_dir, old_path, target_path)
                else:
                    old_path.rename(target_path)
                renamed.append((old_path, target_path))
        except PlanError:
            for old_path, target_path in reversed(renamed):
                if in_git:
                    git_mv(phase_dir, target_path, old_path)
                else:
                    target_path.rename(old_path)
            raise

        for pid, data in sorted(final.items()):
            tmp = data["write_path"].with_suffix(data["write_path"].suffix + ".tmp")
            tmp.write_text(data["text"], encoding="utf-8")
            tmp.replace(data["write_path"])

        print(f"split {src_id} after task {args.after}: {src_id} + {new_id} written")
        for pid, data in sorted(final.items()):
            print(f"  {pid}: {data['write_path']} "
                  f"({len(data['text'].encode('utf-8'))} bytes)")
        return 0

    except PlanError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
