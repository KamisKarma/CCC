"""Shorten windows by rescheduling all six emitter tracks, with exact physics.

Preserves emitter endpoints and toggles, but permits different intermediate
motion, action timing, matter, and pickup timing. The suffix is simulated with
cached beam masks. Every saved program also passes the independent validator.
"""
from __future__ import annotations
import argparse
from functools import lru_cache
import itertools
import json
import math
from pathlib import Path
import random
import time

from package_level6_optimized import choose_programs, DATASETS
from validate_level6_optimized import read_cases, geometry, simulate, FIRE_DIRECTIONS


@lru_cache(maxsize=None)
def alternatives(column, width):
    move = column.count("F") - column.count("B")
    toggle = column.count("T") % 2
    if abs(move) + toggle > width:
        return ()
    alphabet = tuple(symbol for symbol in "-FBT" if symbol == "-" or symbol in column)
    choices = [seq for seq in itertools.product(alphabet, repeat=width)
               if seq.count("F") - seq.count("B") == move and seq.count("T") % 2 == toggle]
    choices.sort(key=lambda seq: sum(symbol != "-" for symbol in seq))
    return tuple(choices)


class Physics:
    def __init__(self, case):
        self.case = case
        cells, raw_beams = geometry(case.radius)
        self.target = sum(cells[cell] for cell in case.pattern)
        self.skirt = 0
        for rr, cc in case.pattern:
            for dr, dc in FIRE_DIRECTIONS:
                neighbor = rr + dr, cc + dc
                if neighbor not in case.pattern:
                    self.skirt |= cells.get(neighbor, 0)
        relevant = self.target | self.skirt
        self.beams = tuple(tuple(mask & relevant for mask in track) for track in raw_beams)
        self.rail = 6 * case.radius

    def beam_schedule(self, position, active, emitter, actions):
        result = []
        track = self.beams[emitter]
        for action in actions:
            if action == "F": position = (position + 1) % self.rail
            elif action == "B": position = (position - 1) % self.rail
            elif action == "T": active = not active
            result.append(track[position] if active else 0)
        return result

    @staticmethod
    def merge_rays(rays):
        one = two = three = 0
        for ray in rays:
            three |= two & ray
            two |= one & ray
            one |= ray
        return two, three

    def snapshots(self, program):
        positions = [index * self.case.radius for index in range(6)]
        active = [False] * 6
        matter = count = 0
        snapshots = [(tuple(positions), tuple(active), matter, count)]
        effects = []
        for row in program:
            rays = []
            for emitter, action in enumerate(row):
                if action == "F": positions[emitter] = (positions[emitter] + 1) % self.rail
                elif action == "B": positions[emitter] = (positions[emitter] - 1) % self.rail
                elif action == "T": active[emitter] = not active[emitter]
                rays.append(self.beams[emitter][positions[emitter]] if active[emitter] else 0)
            two, three = self.merge_rays(rays)
            effects.append((two, three))
            matter = (matter | two) & ~three
            if matter & self.target == self.target and not matter & self.skirt:
                count += 1
                matter &= ~self.target
            snapshots.append((tuple(positions), tuple(active), matter, count))
        assert count == self.case.count, (count, self.case.count)
        return snapshots, effects

    def succeeds(self, beams, matter, count, suffix, expected_state):
        target, skirt = self.target, self.skirt
        for rays in zip(*beams):
            one = two = three = 0
            for ray in rays:
                three |= two & ray
                two |= one & ray
                one |= ray
            matter = (matter | two) & ~three
            if matter & target == target and not matter & skirt:
                count += 1
                matter &= ~target
        if (matter, count) == expected_state:
            return True
        if count > self.case.count:
            return False
        for two, three in suffix:
            matter = (matter | two) & ~three
            if matter & target == target and not matter & skirt:
                count += 1
                matter &= ~target
                if count > self.case.count:
                    return False
        return count == self.case.count


def improve(case, program, deadline, seed, samples):
    physics = Physics(case)
    rng = random.Random(seed)
    attempts = accepted = windows = 0
    snapshots, effects = physics.snapshots(program)
    for sweep in range(4):
        changed = False
        for old_width, new_width in ((3, 2), (4, 3), (5, 4), (5, 3), (2, 1)):
            position = 0
            while position + old_width <= len(program):
                if time.monotonic() > deadline or len(program) <= case.count:
                    return program, attempts, accepted, windows
                old = program[position:position + old_width]
                columns = [tuple(row[emitter] for row in old) for emitter in range(6)]
                options = [alternatives(column, new_width) for column in columns]
                if any(not choices for choices in options):
                    position += 1
                    continue
                windows += 1
                before_pos, before_active, before_matter, before_count = snapshots[position]
                beam_options = [[physics.beam_schedule(before_pos[e], before_active[e], e, actions)
                                 for actions in options[e]] for e in range(6)]
                # Different movement timings can produce identical ray sequences
                # (especially outside the board); their physics is interchangeable.
                for emitter in range(6):
                    distinct = {}
                    for actions, rays in zip(options[emitter], beam_options[emitter]):
                        distinct.setdefault(tuple(rays), actions)
                    options[emitter] = tuple(distinct.values())
                    beam_options[emitter] = list(distinct)
                lengths = [len(choices) for choices in options]
                possibilities = math.prod(lengths)
                if possibilities <= samples:
                    combinations = itertools.product(*(range(length) for length in lengths))
                else:
                    # Start with the shortest action sequences, then vary every track.
                    candidate_combinations = [tuple(0 for _ in range(6))]
                    candidate_combinations.extend(tuple(rng.randrange(length) for length in lengths) for _ in range(samples - 1))
                    combinations = iter(dict.fromkeys(candidate_combinations))
                suffix = effects[position + old_width:]
                expected_state = snapshots[position + old_width][2:]
                found = False
                for combination in combinations:
                    attempts += 1
                    if attempts % 256 == 0 and time.monotonic() > deadline:
                        return program, attempts, accepted, windows
                    rays = [beam_options[e][choice] for e, choice in enumerate(combination)]
                    if physics.succeeds(rays, before_matter, before_count, suffix, expected_state):
                        tracks = [options[e][choice] for e, choice in enumerate(combination)]
                        replacement = list(zip(*tracks))
                        candidate = program[:position] + replacement + program[position + old_width:]
                        if not simulate(case, candidate)["valid"]:
                            raise AssertionError("Fast local validation disagrees with independent validator")
                        program = candidate
                        accepted += 1
                        changed = found = True
                        snapshots, effects = physics.snapshots(program)
                        position = max(0, position - 2)
                        break
                if not found:
                    position += 1
        if not changed:
            break
    return program, attempts, accepted, windows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", type=Path, default=Path(__file__).resolve().parents[1] / "levels" / "level6")
    parser.add_argument("--seconds", type=float, default=330)
    parser.add_argument("--samples", type=int, default=128)
    parser.add_argument("--seed", type=int, default=62302)
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
    directory = args.base_dir / "optimized_compact_round2"
    directory.mkdir(parents=True, exist_ok=True)
    details = []
    saved_total = attempts_total = 0
    for work_index, (dataset, index, case, program) in enumerate(work):
        before = len(program)
        remaining = max(0, deadline - time.monotonic())
        case_deadline = min(deadline, time.monotonic() + 1.1 * remaining / (len(work) - work_index))
        program, attempts, changes, windows = improve(case, program, case_deadline, args.seed + 1000 * dataset + index, args.samples)
        assert simulate(case, program)["valid"]
        saved_total += before - len(program)
        attempts_total += attempts
        folder = directory / str(dataset)
        folder.mkdir(exist_ok=True)
        file = folder / f"case_{index}.txt"
        temporary = file.with_suffix(".tmp")
        temporary.write_text("\n".join(" ".join(row) for row in program) + "\n", encoding="utf-8")
        temporary.replace(file)
        details.append({"dataset": dataset, "case": index, "before": before, "after": len(program),
                        "saved": before - len(program), "attempts": attempts, "changes": changes, "windows": windows})
        if (work_index + 1) % 25 == 0 or work_index + 1 == len(work):
            print(f"{work_index + 1}/{len(work)} cases; saved {saved_total}; {attempts_total} variants; "
                  f"{time.monotonic() - started:.1f}s", flush=True)
    report = {"before": starting_report["score_including_example"],
              "after": starting_report["score_including_example"] - saved_total,
              "saved": saved_total, "attempts": attempts_total,
              "elapsed_seconds": round(time.monotonic() - started, 2), "cases": details}
    (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"ROUND2 COMPACTION {report['before']} -> {report['after']}, saved {saved_total}; all independently valid", flush=True)


if __name__ == "__main__":
    main()
