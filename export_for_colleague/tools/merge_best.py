"""Merge all contributions into best/: per case, keep the shortest program that is valid.

Usage (from the repo root): python tools/merge_best.py
Sources: best/out_level-6_<name>.txt and contrib/<who>/<key>/case_<i>.txt (key = 2, 3 or 4).
A program counts only if it submits the pattern exactly `count` times.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code" / "python"))
from validate_level6_optimized import read_cases, read_programs, simulate  # noqa: E402

FILES = {2: "2-medium", 3: "3-large", 4: "4-enormous"}


def main():
    total = 0
    for key, name in FILES.items():
        cases = read_cases(ROOT / "inputs" / f"in_level-6_{name}.txt")
        best_file = ROOT / "best" / f"out_level-6_{name}.txt"
        best = read_programs(best_file)
        assert len(best) == len(cases)
        before = sum(len(p) for p in best)
        for p in sorted((ROOT / "contrib").glob(f"*/{key}/case_*.txt")):
            i = int(p.stem.split("_")[1])
            progs = read_programs(p)
            if not progs or i >= len(cases):
                continue
            prog = progs[0]
            if len(prog) < len(best[i]) and simulate(cases[i], prog)["valid"]:
                best[i] = prog
        for i, (c, prog) in enumerate(zip(cases, best)):
            assert simulate(c, prog)["valid"], f"{name} case {i} invalid"
        text = "\n\n".join("\n".join(" ".join(r) for r in prog) for prog in best)
        best_file.write_text(text + "\n")
        after = sum(len(p) for p in best)
        total += after
        print(f"{name}: {before} -> {after}")
    print(f"TOTAL: {total}")


if __name__ == "__main__":
    main()
