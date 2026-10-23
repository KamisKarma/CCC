"""Independent CCC 2026 Level 6 program validator and raw-score calculator.

No solver modules are imported. Geometry is constructed by walking the six
rail edges, and matter is simulated with integer bitsets. The rules are from
levels 3-6 and the supplied sandbox-level-6.html. All physical instruction
lines count, including six-noop lines (the sandbox's displayed Cycles differs).

Usage:
  python validate_level6_optimized.py --output-dir path/to/outputs
  python validate_level6_optimized.py input.txt output.txt
  python validate_level6_optimized.py --output-dir path --json report.json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable


FIRE_DIRECTIONS = ((0, 2), (1, 1), (1, -1), (0, -2), (-1, -1), (-1, 1))
RAIL_DIRECTIONS = ((-1, 1), (0, 2), (1, 1), (1, -1), (0, -2), (-1, -1))
VALID_TOKENS = frozenset(("F", "B", "T", "-"))


@dataclass(frozen=True)
class Case:
    radius: int
    pattern: frozenset[tuple[int, int]]
    count: int


def read_cases(path: Path) -> list[Case]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if not lines:
        raise ValueError(f"{path}: empty input")
    number = int(lines[0])
    cursor = 1
    cases = []
    for case_number in range(1, number + 1):
        while cursor < len(lines) and not lines[cursor].strip():
            cursor += 1
        if cursor >= len(lines):
            raise ValueError(f"{path}: missing input case {case_number}")
        header = lines[cursor].split()
        if len(header) != 4:
            raise ValueError(f"{path}:{cursor + 1}: expected four input integers")
        radius, height, width, count = map(int, header)
        if radius < 1 or count < 1 or height != 2 * radius + 1 or width != 4 * radius + 1:
            raise ValueError(f"{path}:{cursor + 1}: invalid dimensions or count")
        cursor += 1
        rows = lines[cursor:cursor + height]
        if len(rows) != height or any(len(row) != width for row in rows):
            raise ValueError(f"{path}: invalid grid shape in case {case_number}")
        cells = geometry(radius)[0]
        pattern = set()
        for row_index, row in enumerate(rows):
            for col_index, symbol in enumerate(row):
                cell = row_index, col_index
                if symbol not in "-*OM":
                    raise ValueError(f"{path}: unknown grid symbol {symbol!r}")
                if (symbol in "OM") != (cell in cells):
                    raise ValueError(f"{path}: wrong interior geometry at {cell}")
                if symbol == "M":
                    pattern.add(cell)
        if not pattern:
            raise ValueError(f"{path}: case {case_number} has no matter")
        cases.append(Case(radius, frozenset(pattern), count))
        cursor += height
    if any(line.strip() for line in lines[cursor:]):
        raise ValueError(f"{path}: extra data after last input case")
    return cases


@lru_cache(maxsize=None)
def geometry(radius: int):
    """Return interior coordinate bits and emitter beam bitsets by rail index."""
    # Independent construction from the six rail edges, each containing r cells.
    perimeter = []
    rr, cc = radius, 0
    for dr, dc in RAIL_DIRECTIONS:
        for _ in range(radius):
            perimeter.append((rr, cc))
            rr, cc = rr + dr, cc + dc
    assert (rr, cc) == (radius, 0)
    assert len(set(perimeter)) == 6 * radius
    perimeter_set = set(perimeter)
    interior = {}
    for rr in range(1, 2 * radius):
        lo = abs(radius - rr)
        hi = 4 * radius - lo
        for cc in range(lo + 2, hi, 2):
            interior[(rr, cc)] = 1 << len(interior)
    beams = []
    inside_board = set(interior) | perimeter_set
    for dr, dc in FIRE_DIRECTIONS:
        direction_beams = []
        for rr, cc in perimeter:
            mask = 0
            rr, cc = rr + dr, cc + dc
            while (rr, cc) in inside_board:
                mask |= interior.get((rr, cc), 0)
                rr, cc = rr + dr, cc + dc
            direction_beams.append(mask)
        beams.append(tuple(direction_beams))
    return interior, tuple(beams)


def read_programs(path: Path) -> list[list[tuple[str, ...]]]:
    programs = []
    current = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            if current:
                programs.append(current)
                current = []
            continue
        tokens = tuple(line.split())
        if len(tokens) != 6 or any(token not in VALID_TOKENS for token in tokens):
            raise ValueError(f"{path}:{line_number}: expected exactly six F/B/T/- instructions")
        current.append(tokens)
    if current:
        programs.append(current)
    return programs


def simulate(case: Case, program: Iterable[tuple[str, ...]], *, record_ticks=False) -> dict:
    cells, beams = geometry(case.radius)
    pattern_mask = sum(cells[cell] for cell in case.pattern)
    forbidden_mask = 0
    for rr, cc in case.pattern:
        for dr, dc in FIRE_DIRECTIONS:
            neighbor = rr + dr, cc + dc
            if neighbor not in case.pattern:
                forbidden_mask |= cells.get(neighbor, 0)
    positions = [index * case.radius for index in range(6)]
    enabled = [False] * 6
    matter = 0
    accepted = 0
    ticks = 0
    accepted_at = []
    limit = 6 * case.radius
    for ticks, instructions in enumerate(program, 1):
        if len(instructions) != 6 or any(token not in VALID_TOKENS for token in instructions):
            raise ValueError(f"invalid instruction line {ticks}")
        for emitter, token in enumerate(instructions):
            if token == "F":
                positions[emitter] = (positions[emitter] + 1) % limit
            elif token == "B":
                positions[emitter] = (positions[emitter] - 1) % limit
            elif token == "T":
                enabled[emitter] = not enabled[emitter]
        # Threshold bitsets: seen by >= 1, >= 2, >= 3 beams, respectively.
        one = two = three = 0
        for emitter in range(6):
            if enabled[emitter]:
                ray = beams[emitter][positions[emitter]]
                three |= two & ray
                two |= one & ray
                one |= ray
        matter = (matter | two) & ~three
        if matter & pattern_mask == pattern_mask and not matter & forbidden_mask:
            accepted += 1
            matter &= ~pattern_mask
            if record_ticks:
                accepted_at.append(ticks)
    result = {"lines": ticks, "required": case.count, "accepted": accepted,
              "valid": accepted == case.count}
    if record_ticks:
        result["accepted_at"] = accepted_at
    return result


def validate_files(input_path: Path, output_path: Path, *, at_least=False) -> dict:
    cases = read_cases(input_path)
    programs = read_programs(output_path)
    if len(cases) != len(programs):
        raise ValueError(f"{output_path}: expected {len(cases)} programs, found {len(programs)}")
    details = []
    for number, (case, program) in enumerate(zip(cases, programs), 1):
        report = simulate(case, program)
        if at_least:
            report["valid"] = report["accepted"] >= report["required"]
        details.append({"case": number, **report})
    return {"input": str(input_path.resolve()), "output": str(output_path.resolve()),
            "cases": len(cases), "score": sum(item["lines"] for item in details),
            "required": sum(item["required"] for item in details),
            "accepted": sum(item["accepted"] for item in details),
            "valid": all(item["valid"] for item in details), "details": details}


def main() -> int:
    default_dir = Path(__file__).resolve().parents[1] / "levels" / "level6"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path, help="optional input output file pair")
    parser.add_argument("--input-dir", type=Path, default=default_dir)
    parser.add_argument("--output-dir", type=Path, default=default_dir)
    parser.add_argument("--json", type=Path, help="write detailed machine-readable report")
    parser.add_argument("--at-least", action="store_true", help="accept oversupply as the sandbox does")
    args = parser.parse_args()
    if args.files:
        if len(args.files) != 2:
            parser.error("provide both an input and an output file")
        pairs = [tuple(args.files)]
    else:
        inputs = sorted(args.input_dir.glob("in_level-6_*.txt"))
        if not inputs:
            parser.error("no level 6 input files found")
        pairs = [(path, args.output_dir / path.name.replace("in_", "out_", 1)) for path in inputs]
    reports = []
    for input_path, output_path in pairs:
        try:
            report = validate_files(input_path, output_path, at_least=args.at_least)
        except (ValueError, OSError) as exc:
            print(f"INVALID {output_path.name}: {exc}")
            reports.append({"output": str(output_path), "valid": False, "error": str(exc)})
            continue
        reports.append(report)
        label = "VALID" if report["valid"] else "INVALID"
        print(f"{label:7} {output_path.name}: {report['score']:,} lines; "
              f"{report['accepted']:,}/{report['required']:,} patterns; {report['cases']} programs")
        for case in report["details"]:
            if not case["valid"]:
                print(f"  case {case['case']}: accepted {case['accepted']}, required {case['required']}")
    result = {"valid": all(report["valid"] for report in reports),
              "score": sum(report.get("score", 0) for report in reports), "files": reports}
    print(f"TOTAL: {result['score']:,} instruction lines; " + ("all valid" if result["valid"] else "INVALID"))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
