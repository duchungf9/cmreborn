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

    for path in args.pseudocode:
        text = path.read_text(encoding="utf-8", errors="replace")
        entries = []
        for match in WRITE_RE.finditer(text):
            value = int(match.group(1), 0)
            if value in FAMILY:
                line = text.count("\n", 0, match.start()) + 1
                entries.append((value, line))
                all_writes[value].append((path.name, line))
        unique = sorted({value for value, _ in entries})
        print(f"{path.name}: {len(entries)} literal writes; "
              f"{len(unique)} distinct states")
        for value in unique:
            lines = ", ".join(str(line) for state, line in entries if state == value)
            print(f"  {value}: {names.get(value, 'UNKNOWN')} (lines {lines})")

    print("\nAUDITED-BATCH INVENTORY")
    print(f"{len(all_writes)}/34 states have a literal action write in these inputs")
    for value in sorted(all_writes):
        refs = ", ".join(f"{filename}:{line}" for filename, line in all_writes[value])
        print(f"  {value}: {names.get(value, 'UNKNOWN')} — {refs}")
    missing = sorted(set(FAMILY) - set(all_writes))
    if missing:
        print("No literal write found in this batch (not proof of absence): "
              + ", ".join(f"{value} {names.get(value, 'UNKNOWN')}" for value in missing))


if __name__ == "__main__":
    main()
