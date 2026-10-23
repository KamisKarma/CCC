"""Shorten valid Level 6 programs by removing ticks and composing nearby rows.

Every accepted change is checked with the independent simulator. Source files
are never overwritten: candidates go to optimized_compact/{dataset}/case_N.txt.
Run again after other searches finish to compact the latest merged best set.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from package_level6_optimized import choose_programs, DATASETS
from validate_level6_optimized import read_cases, simulate


def compose(rows):
    """Compose each emitter's net position and toggle into at most one action."""
    result = []
    for emitter in range(6):
        move = sum((1 if row[emitter] == "F" else -1 if row[emitter] == "B" else 0) for row in rows)
        toggle = sum(row[emitter] == "T" for row in rows) % 2
        if abs(move) > 1 or (toggle and move):
            return None
        result.append("T" if toggle else "F" if move == 1 else "B" if move == -1 else "-")
    return tuple(result)


def compact(case, program, deadline):
    before = len(program)
    attempts = accepted_changes = 0
    # Composition often preserves all future emitter states, so try it first.
    for sweep in range(3):
        changed = False
        for group_length, merge in ((3, True), (2, True), (3, False), (2, False), (1, False)):
            position = 0
            while position + group_length <= len(program):
                if time.monotonic() >= deadline or len(program) <= case.count:
                    return program, attempts, accepted_changes
                replacement = []
                if merge:
                    combined = compose(program[position:position + group_length])
                    if combined is None:
                        position += 1
                        continue
                    replacement = [combined]
                candidate = program[:position] + replacement + program[position + group_length:]
                attempts += 1
                if simulate(case, candidate)["valid"]:
                    program = candidate
                    accepted_changes += 1
                    changed = True
                    position = max(0, position - 2)
                else:
                    position += 1
        if not changed:
            break
    return program, attempts, accepted_changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", type=Path, default=Path(__file__).resolve().parents[1] / "levels" / "level6")
    parser.add_argument("--seconds", type=float, default=120)
    args = parser.parse_args()
    outputs, starting_report = choose_programs(args.base_dir)
    work = []
    for dataset, name in enumerate(DATASETS):
        cases = read_cases(args.base_dir / f"in_level-6_{dataset}-{name}.txt")
        programs = [[tuple(line.split()) for line in block.splitlines()]
                    for block in outputs[f"out_level-6_{dataset}-{name}.txt"].strip().split("\n\n")]
        work.extend((dataset, index, case, program) for index, (case, program) in enumerate(zip(cases, programs)))
    started = time.monotonic()
    deadline = started + args.seconds
    result_directory = args.base_dir / "optimized_compact"
    details = []
    total_saved = attempts_total = 0
    for work_index, (dataset, index, case, program) in enumerate(work):
        before = len(program)
        # Give every case a fair share rather than spending the budget on early files.
        remaining = max(0, deadline - time.monotonic())
        case_deadline = min(deadline, time.monotonic() + max(0.02, 1.5 * remaining / (len(work) - work_index)))
        program, attempts, changes = compact(case, program, case_deadline)
        if not simulate(case, program)["valid"]:
            raise ValueError(f"Compaction invalidated dataset {dataset}, case {index}")
        directory = result_directory / str(dataset)
        directory.mkdir(parents=True, exist_ok=True)
        text = "\n".join(" ".join(line) for line in program) + "\n"
        (directory / f"case_{index}.txt").write_text(text, encoding="utf-8")
        saved = before - len(program)
        total_saved += saved
        attempts_total += attempts
        details.append({"dataset": dataset, "case": index, "before": before, "after": len(program),
                        "saved": saved, "candidate_checks": attempts, "accepted_changes": changes})
        if (work_index + 1) % 40 == 0 or work_index + 1 == len(work):
            print(f"{work_index + 1}/{len(work)} cases; saved {total_saved} ticks; "
                  f"{attempts_total} candidate checks; {time.monotonic() - started:.1f}s", flush=True)
    report = {"before": starting_report["score_including_example"],
              "after": starting_report["score_including_example"] - total_saved,
              "saved": total_saved, "candidate_checks": attempts_total,
              "elapsed_seconds": round(time.monotonic() - started, 2), "cases": details}
    (result_directory / "compaction-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"COMPACTION: {report['before']} -> {report['after']} lines, saved {total_saved}; "
          f"all {len(work)} programs independently validated", flush=True)


if __name__ == "__main__":
    main()
