#!/usr/bin/env python3
"""Extract named match-engine action labels from CM 03/04's PE32 executable.

The output is a label map recovered from the action-name switch at VA 0x8F5BF0.
It does not claim that every named action is reachable in a normal match.
"""

import argparse
import csv
import struct
from pathlib import Path

IMAGE_BASE = 0x400000


def extract(exe: bytes) -> dict[int, tuple[str, int]]:
    def u8(va: int) -> int:
        return exe[va - IMAGE_BASE]

    def u32(va: int) -> int:
        return struct.unpack_from("<I", exe, va - IMAGE_BASE)[0]

    def c_string(va: int) -> str:
        return exe[va - IMAGE_BASE :].split(b"\0", 1)[0].decode("latin1")

    def name_at(case_va: int) -> str:
        if u8(case_va) != 0x68:  # PUSH imm32, followed by the common formatter path
            raise ValueError(f"expected PUSH imm32 at VA 0x{case_va:08X}")
        return c_string(u32(case_va + 1))

    rows: dict[int, tuple[str, int]] = {}

    def direct(first_id: int, count: int, table_va: int) -> None:
        for index in range(count):
            case_va = u32(table_va + index * 4)
            rows[first_id + index] = (name_at(case_va), case_va)

    def compressed(first_id: int, count: int, remap_va: int, table_va: int) -> None:
        for index in range(count):
            slot = u8(remap_va + index)
            case_va = u32(table_va + slot * 4)
            rows[first_id + index] = (name_at(case_va), case_va)

    direct(0, 5, 0x8F66B0)
    rows[100] = (name_at(0x8F5C75), 0x8F5C75)
    direct(102, 23, 0x8F66C4)
    rows[200] = (name_at(0x8F5D89), 0x8F5D89)
    direct(201, 14, 0x8F6720)
    rows[300] = (name_at(0x8F5E45), 0x8F5E45)
    direct(301, 16, 0x8F6758)
    rows[400] = (name_at(0x8F5F15), 0x8F5F15)
    compressed(401, 112, 0x8F687C, 0x8F6798)
    rows[600] = (name_at(0x8F617C), 0x8F617C)
    direct(601, 5, 0x8F68EC)
    rows[700] = (name_at(0x8F61D6), 0x8F61D6)
    direct(701, 9, 0x8F6900)
    rows[800] = (name_at(0x8F6258), 0x8F6258)
    direct(801, 6, 0x8F6924)
    rows[900] = (name_at(0x8F62BC), 0x8F62BC)
    compressed(901, 210, 0x8F6988, 0x8F693C)
    rows[1111] = (name_at(0x8F63BA), 0x8F63BA)
    compressed(1201, 200, 0x8F6AA8, 0x8F6A5C)
    rows[1401] = (name_at(0x8F6496), 0x8F6496)
    rows[1500] = (name_at(0x8F64F0), 0x8F64F0)
    compressed(1501, 205, 0x8F6BC8, 0x8F6B88)
    rows[1706] = (name_at(0x8F65BF), 0x8F65BF)
    compressed(1800, 201, 0x8F6CD4, 0x8F6C98)

    # The resolver's fallback is the literal "UNKNOWN ACTION". Keep the CSV
    # focused on positive labels; holes and fallback IDs are described in notes.
    return {action_id: item for action_id, item in rows.items() if item[0].startswith("ME_")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path, help="path to cm0304.exe")
    parser.add_argument("output", type=Path, help="output CSV path")
    args = parser.parse_args()

    rows = extract(args.executable.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(("action_id", "name", "case_va"))
        for action_id, (name, case_va) in sorted(rows.items()):
            writer.writerow((action_id, name, f"0x{case_va:08X}"))
    print(f"wrote {len(rows)} named action labels to {args.output}")


if __name__ == "__main__":
    main()
