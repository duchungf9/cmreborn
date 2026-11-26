#!/usr/bin/env python3
"""Summarize direct off-ball action writes from Ghidra batch pseudocode.

This reports literal writes only. Absence from the report does not prove an
action is unused; it may be written through a helper or another code path.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path


WRITE_RE = re.compile(
    r"(?:\*\(undefined4 \*\)\(param_1 \+ 0x8cc\)|param_1\[0x233\])"
    r"\s*=\s*(?:\([^;]*?\)\s*)?(0x[0-9a-fA-F]+|\d+)\s*;"
)
CASE_RE = re.compile(r"^\s*case\s+0x([0-9a-fA-F]+)\s*:", re.MULTILINE)
FAMILY = range(400, 434)


def load_names(path: Path) -> dict[int, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {int(row["action_id"]): row["name"] for row in csv.DictReader(handle)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pseudocode", nargs="+", type=Path)
    parser.add_argument(
        "--action-map",
        type=Path,
        default=Path(__file__).with_name("action-state-name-map.csv"),
    )
    args = parser.parse_args()
    names = load_names(args.action_map)
    all_writes: dict[int, list[tuple[str, int]]] = defaultdict(list)
    all_cases: dict[int, list[tuple[str, int]]] = defaultdict(list)

    for path in args.pseudocode:
        text = path.read_text(encoding="utf-8", errors="replace")
        entries = []
        for match in WRITE_RE.finditer(text):
            value = int(match.group(1), 0)
            if value in FAMILY:
                line = text.count("\n", 0, match.start()) + 1
                entries.append((value, line))
                all_writes[value].append((path.name, line))
        case_entries = []
        for match in CASE_RE.finditer(text):
            value = int(match.group(1), 16)
            if value in FAMILY:
                line = text.count("\n", 0, match.start()) + 1
                case_entries.append((value, line))
                all_cases[value].append((path.name, line))
        unique = sorted({value for value, _ in entries})
        cases = sorted({value for value, _ in case_entries})
        print(f"{path.name}: {len(entries)} literal writes across {len(unique)} states; "
              f"{len(cases)} dispatcher case states")
        for value in unique:
            lines = ", ".join(str(line) for state, line in entries if state == value)
            print(f"  {value}: {names.get(value, 'UNKNOWN')} (lines {lines})")
        if cases:
            print("  switch cases: " + ", ".join(
                f"{value} {names.get(value, 'UNKNOWN')}"
                for value in cases
            ))

    print("\nAUDITED-BATCH INVENTORY")
    located = set(all_writes) | set(all_cases)
    print(f"{len(located)}/34 states have a literal write or dispatcher case in these inputs")
    for value in sorted(located):
        refs = []
        refs.extend(f"write {filename}:{line}" for filename, line in all_writes[value])
        refs.extend(f"case {filename}:{line}" for filename, line in all_cases[value])
        print(f"  {value}: {names.get(value, 'UNKNOWN')} — " + "; ".join(refs))
    missing = sorted(set(FAMILY) - located)
    if missing:
        print("No literal write or dispatcher case found in this batch (not proof of absence): "
              + ", ".join(f"{value} {names.get(value, 'UNKNOWN')}" for value in missing))


if __name__ == "__main__":
    main()
