"""Beam planner (level6e) against the merged incumbents.

Usage: python opt6e.py <key> '<json variant dict>' [procs]
Improvements go to levels/level6/optimized_beam_claude/<key>/case_<i>.txt (merge6.py picks them up).
"""
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import level6e  # noqa: E402
from level5 import simulate  # noqa: E402
from level6 import parse  # noqa: E402

D = Path(__file__).parent.parent / "levels" / "level6"
_geo = {}


def work(args):
    ci, r, pat, cnt, kw, limit = args
    pat = set(map(tuple, pat))
    if r not in _geo:
        _geo[r] = level6e.Geo(r)
    try:
        lines = level6e.Planner(_geo[r], pat, cnt, **kw).run(limit)
    except Exception as ex:  # noqa: BLE001
        print("ERR", ci, ex, flush=True)
        return ci, limit, None
    if lines is None or len(lines) >= limit or simulate(r, pat, lines) != cnt:
        return ci, limit, None
    return ci, limit, lines


def main():
    key = sys.argv[1]
    kw = json.loads(sys.argv[2])
    procs = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    fin = next(D.glob(f"in_level-6_{key}*.txt"))
    cases = parse(fin.read_text())
    merged = json.loads((D / "merged" / f"{key}.json").read_text())
    out = D / "optimized_beam_claude" / key
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(ci, r, sorted(pat), cnt, kw, len(merged[str(ci)])) for ci, (r, pat, cnt) in enumerate(cases)]
    jobs.sort(key=lambda j: -j[5])
    saved, t = 0, time.time()
    with Pool(procs) as pool:
        for ci, limit, lines in pool.imap_unordered(work, jobs, chunksize=1):
            if lines is not None:
                f = out / f"case_{ci}.txt"
                if f.exists() and len(f.read_text().strip().splitlines()) <= len(lines):
                    continue
                saved += limit - len(lines)
                f.write_text("\n".join(" ".join(l) for l in lines) + "\n")
                print(f"case {ci}: {limit} -> {len(lines)} (saved {saved})", flush=True)
    print(f"DONE {fin.name} {kw}: saved {saved} in {time.time() - t:.0f}s", flush=True)


if __name__ == "__main__":
    main()
