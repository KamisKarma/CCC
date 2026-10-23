"""Parallel multi-variant optimizer for level 6.

Usage: python opt6.py <file-key: 1|2|3|4> [variant-set]
Keeps the best verified program per case in levels/level6/best/<key>.json and writes
levels/level6/best/out_<name>.txt from it.
"""
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import level6b  # noqa: E402
import level6c  # noqa: E402
from level5 import simulate  # noqa: E402
from level6 import parse  # noqa: E402

D = Path(__file__).parent.parent / "levels" / "level6"
OUT = D / "best"

VARIANTS = [
    dict(stall_th=2, w_min=10, w_mean=1.0, seed=None),
    dict(stall_th=1, w_min=10, w_mean=1.0, seed=None),
    dict(stall_th=3, w_min=10, w_mean=1.0, seed=None),
    dict(stall_th=2, w_min=3, w_mean=1.0, seed=None),
    dict(stall_th=2, w_min=20, w_mean=0.3, seed=None),
    dict(stall_th=2, w_min=10, w_mean=1.0, seed=1),
    dict(stall_th=2, w_min=10, w_mean=1.0, seed=2),
    dict(stall_th=1, w_min=10, w_mean=1.0, seed=3),
]

_geo = {}


def geo(r):
    if r not in _geo:
        _geo[r] = level6c.Geo(r)
    return _geo[r]


def work(args):
    ci, r, pat, cnt, vi, limit = args
    pat = set(map(tuple, pat))
    try:
        lines = level6c.plan(geo(r), pat, cnt, limit, **VARIANTS[vi])
    except Exception:
        return ci, None
    if lines is None or simulate(r, pat, lines) != cnt:
        return ci, None
    return ci, lines


def main():
    key = sys.argv[1]
    vset = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else list(range(len(VARIANTS)))
    fin = next(D.glob(f"in_level-6_{key}*.txt"))
    cases = parse(fin.read_text())
    OUT.mkdir(exist_ok=True)
    cache_f = OUT / f"{key}.json"
    best = json.loads(cache_f.read_text()) if cache_f.exists() else {}
    # seed cache with the line-painter baseline
    for ci, (r, pat, cnt) in enumerate(cases):
        if str(ci) not in best:
            best[str(ci)] = level6b.solve_case(level6b.Geo(r), pat, cnt)
    t = time.time()
    jobs = [(ci, r, sorted(pat), cnt, vi, len(best[str(ci)]))
            for vi in vset for ci, (r, pat, cnt) in enumerate(cases)]
    with Pool(8) as pool:
        for ci, lines in pool.imap_unordered(work, jobs, chunksize=1):
            if lines is not None and len(lines) < len(best[str(ci)]):
                best[str(ci)] = lines
    cache_f.write_text(json.dumps(best))
    total = sum(len(best[str(ci)]) for ci in range(len(cases)))
    out = "\n\n".join("\n".join(" ".join(l) for l in best[str(ci)]) for ci in range(len(cases)))
    (OUT / ("out_" + fin.name[3:])).write_text(out + "\n")
    print(f"{fin.name}: total {total} lines ({time.time() - t:.0f}s)")


if __name__ == "__main__":
    main()
