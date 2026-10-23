"""Parallel optimizer for level 6 using the beam planner (level6d).

Usage: python opt6d.py <keys e.g. 2,3,4> <variant indices e.g. 0,1>
Best verified program per case is cached in levels/level6/best/<key>.json (seeded from
levels/level6/v3 outputs) and written to levels/level6/best/out_<name>.txt after each pass.
"""
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import level6d  # noqa: E402
from level5 import simulate  # noqa: E402
from level6 import parse  # noqa: E402

D = Path(__file__).parent.parent / "levels" / "level6"
OUT = D / "best"

VARIANTS = [
    dict(W=1),
    dict(W=4),
    dict(W=8, topk=4),
    dict(W=4, seed=1),
    dict(W=4, stall_th=4),
    dict(W=16, topk=4),
    dict(W=16, topk=8),
    dict(W=32, topk=8),
    dict(W=64, topk=8),
]

_geo = {}


def work(args):
    ci, r, pat, cnt, vi, limit = args
    pat = set(map(tuple, pat))
    if r not in _geo:
        _geo[r] = level6d.Geo(r)
    try:
        lines = level6d.Planner(_geo[r], pat, cnt, **VARIANTS[vi]).run(limit)
    except Exception as ex:  # noqa: BLE001
        print("ERR", ci, ex, flush=True)
        return ci, None
    if lines is None or len(lines) >= limit or simulate(r, pat, lines) != cnt:
        return ci, None
    return ci, lines


def load_best(key, fin, cases):
    cache_f = OUT / f"{key}.json"
    if cache_f.exists():
        best = json.loads(cache_f.read_text())
        if len(best) == len(cases) and all(str(i) in best for i in range(len(cases))):
            return best
    v3 = D / "v3" / ("out_" + fin.name[3:])
    progs = v3.read_text().strip().split("\n\n")
    assert len(progs) == len(cases)
    return {str(i): [l.split() for l in p.splitlines()] for i, p in enumerate(progs)}


def save(key, fin, cases, best):
    (OUT / f"{key}.json").write_text(json.dumps(best))
    out = "\n\n".join("\n".join(" ".join(l) for l in best[str(ci)]) for ci in range(len(cases)))
    (OUT / ("out_" + fin.name[3:])).write_text(out + "\n")
    return sum(len(best[str(ci)]) for ci in range(len(cases)))


def main():
    keys = sys.argv[1].split(",")
    vset = [int(x) for x in sys.argv[2].split(",")]
    OUT.mkdir(exist_ok=True)
    with Pool(8) as pool:
        for vi in vset:
            for key in keys:
                fin = next(D.glob(f"in_level-6_{key}*.txt"))
                cases = parse(fin.read_text())
                best = load_best(key, fin, cases)
                t = time.time()
                jobs = [(ci, r, sorted(pat), cnt, vi, len(best[str(ci)]))
                        for ci, (r, pat, cnt) in enumerate(cases)]
                jobs.sort(key=lambda j: -len(j[2]) * j[3])
                for ci, lines in pool.imap_unordered(work, jobs, chunksize=1):
                    if lines is not None and len(lines) < len(best[str(ci)]):
                        best[str(ci)] = lines
                total = save(key, fin, cases, best)
                print(f"variant {vi} {fin.name}: total {total} lines ({time.time() - t:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
