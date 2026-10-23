"""Parallel driver for level6_periodic.solve (CP-SAT repeating cycles).

Run with the Python 3.12 that matches the OR-Tools build:
  <py312> periodic6.py <key> [Lmax] [seconds per L>=2]
Incumbents come from levels/level6/merged/<key>.json; improvements are written to
levels/level6/optimized_periodic_claude/<key>/case_<i>.txt (picked up by merge6.py).
"""
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from level6_periodic import solve  # noqa: E402
from validate_level6_optimized import read_cases, simulate  # noqa: E402

D = Path(__file__).parent.parent / "levels" / "level6"
NAMES = ["example", "small", "medium", "large", "enormous"]


def work(args):
    fi, i, case, inc, lmax, secs = args
    best = inc
    t = time.time()
    for L in range(1, lmax + 1):
        if 1 + (case.count - 1) * L >= len(best):
            break
        try:
            res = solve(case, L, best, 0.5 if L == 1 else secs)
        except Exception as ex:  # noqa: BLE001
            print("ERR", fi, i, L, ex, flush=True)
            continue
        if res is not None and len(res) < len(best) and simulate(case, res)["valid"]:
            best = res
    return fi, i, len(inc), best, time.time() - t


def main():
    fi = int(sys.argv[1])
    lmax = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    secs = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
    procs = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    min_per_rep = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
    name = NAMES[fi]
    cases = read_cases(D / f"in_level-6_{fi}-{name}.txt")
    merged = json.loads((D / "merged" / f"{fi}.json").read_text())
    out = D / "optimized_periodic_claude" / str(fi)
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for i, case in enumerate(cases):
        inc = [tuple(l) for l in merged[str(i)]]
        if case.count >= 2 and len(inc) / case.count >= min_per_rep:
            jobs.append((fi, i, case, inc, min(lmax, (len(inc) - 2) // case.count), secs))
    jobs.sort(key=lambda j: -len(j[3]))
    saved = 0
    with Pool(procs) as pool:
        for fi_, i, before, best, dt in pool.imap_unordered(work, jobs):
            if len(best) < before:
                saved += before - len(best)
                (out / f"case_{i}.txt").write_text("\n".join(" ".join(r) for r in best) + "\n")
                print(f"{name} case {i}: {before} -> {len(best)}  (saved so far {saved}, {dt:.0f}s)", flush=True)
    print(f"DONE {name}: saved {saved}", flush=True)


if __name__ == "__main__":
    main()
