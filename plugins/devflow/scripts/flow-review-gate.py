#!/usr/bin/env python3
"""Review-disposition gate: no merge ask while a review finding is still open.

    flow-review-gate.py [--root DIR] [--phase N]

/flow-pr runs this before its step-5 human gate. It reads two review records:

  * the phase's review files, .planning/phases/<N>-*/*-REVIEW.md (phase from --phase, else
    the `Phase: N` line in .planning/STATE.md). Findings are `### CR-NN|BL-NN|WR-NN: title`
    headings (Critical/Blocker/Warning; IN- Info is ignored). A finding is closed when its
    block has a `fixed: <sha>`, `refuted: <reason>` or `deferred: <TODOS.md line|#issue|URL>`
    line, or a sibling *-REVIEW-FIX.md lists its id under `## Fixed Issues`.
  * the last round of .planning/reviews/LEDGER.md: a Rulings row whose disposition is
    PENDING OWNER, or FIX NOW with no commit SHA backfilled, is open.

Exit 1 lists every open finding. No review file → exit 0 with a note. Stdlib only.
"""
import argparse
import re
import sys
from pathlib import Path

FINDING = re.compile(r"^#{2,4}\s+((?:CR|BL|WR)-\d+)\b[:\s]*(.*)$")
HEADING = re.compile(r"^#{1,4}\s")
SHA = re.compile(r"\b[0-9a-f]{7,40}\b")
TODO_REF = re.compile(r"TODOS\.md|#\d+|https?://")
DISPOSITION = re.compile(r"^[\s>*_-]*(fixed|refuted|deferred)\s*:\**\s*(.*)$", re.I)


def disposed(kind, value):
    kind = kind.lower()
    if kind == "fixed":
        return bool(SHA.search(value))
    if kind == "deferred":
        return bool(TODO_REF.search(value))
    return bool(value.strip())


def blocks(text):
    """Yield (heading line, body lines) per heading, ignoring headings inside code fences."""
    head, body, fence = None, [], False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fence = not fence
        if not fence and HEADING.match(line):
            if head is not None:
                yield head, body
            head, body = line, []
        else:
            body.append(line)
    if head is not None:
        yield head, body


def fixed_ids(fix_file):
    ids, in_fixed = set(), False
    for head, _ in blocks(fix_file.read_text(encoding="utf-8")):
        if head.startswith("## "):
            in_fixed = head.strip().lower() == "## fixed issues"
        elif in_fixed and (m := FINDING.match(head)):
            ids.add(m.group(1))
    return ids


def phase_open(root, phase):
    if phase.isdigit():
        phase = f"{int(phase):02d}"
    files = sorted(root.glob(f".planning/phases/{phase}-*/*REVIEW*.md"))
    reviews = [f for f in files if "REVIEW-FIX" not in f.name]
    fixed = set().union(*(fixed_ids(f) for f in files if "REVIEW-FIX" in f.name))
    open_items = []
    for review in reviews:
        for head, body in blocks(review.read_text(encoding="utf-8")):
            m = FINDING.match(head)
            if not m or m.group(1) in fixed:
                continue
            if any((d := DISPOSITION.match(l)) and disposed(*d.groups()) for l in body):
                continue
            open_items.append(f"{review.relative_to(root)}: {m.group(1)} {m.group(2).strip()}")
    return reviews, open_items


def ledger_open(ledger):
    rounds = re.split(r"^## Round ", ledger.read_text(encoding="utf-8"), flags=re.M)
    if len(rounds) < 2:
        return []
    title = rounds[-1].splitlines()[0].strip()
    open_items = []
    for line in rounds[-1].splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not line.lstrip().startswith("|") or len(cells) < 5 or not cells[0].strip("*").replace("-", "").isalnum():
            continue
        disposition = cells[-1]
        if "PENDING OWNER" in disposition or ("FIX NOW" in disposition and not SHA.search(disposition)):
            open_items.append(f"LEDGER round {title}: #{cells[0]} {cells[1]} — {disposition.split('—')[0].strip('* ')}")
    return open_items


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--phase")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    phase = args.phase
    state = root / ".planning/STATE.md"
    if phase is None and state.is_file():
        m = re.search(r"^Phase:\s*(\d+(?:\.\d+)?)\b", state.read_text(encoding="utf-8"), re.M)
        phase = m.group(1) if m else None
    reviews, open_items = phase_open(root, phase) if phase else ([], [])
    ledger = root / ".planning/reviews/LEDGER.md"
    if ledger.is_file():
        open_items += ledger_open(ledger)
    if not reviews and not ledger.is_file():
        print(f"review-gate: PASS — no review file (phase {phase or 'none'}; no LEDGER.md)")
        return 0
    if not open_items:
        print("review-gate: PASS — every review finding is closed or explicitly deferred")
        return 0
    print(f"review-gate: FAIL — {len(open_items)} open review finding(s):")
    for item in open_items:
        print(f"  OPEN {item}")
    print("Fix: resolve each (`fixed: <sha>` / `refuted: <reason>` in the finding, or backfill the "
          "ledger row's commit) or mark it `deferred: <TODOS.md line | #issue>`; then rerun.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
