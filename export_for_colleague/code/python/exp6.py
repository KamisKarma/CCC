"""Quick A/B harness: python exp6.py <key> <N heaviest cases> '<json list of variant dicts>'"""
import json
import sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import level6e as level6d  # noqa: E402
from level6 import parse  # noqa: E402

D = Path(__file__).parent.parent / "levels" / "level6"
_geo = {}


def work(a):
    vi, ci, r, pat, cnt, kw = a
    if r not in _geo:
        _geo[r] = level6d.Geo(r)
    l = level6d.Planner(_geo[r], set(map(tuple, pat)), cnt, **kw).run(10 ** 6)
    return vi, ci, (len(l) if l else 10 ** 6)


if __name__ == "__main__":
    key, N, vs = sys.argv[1], int(sys.argv[2]), json.loads(sys.argv[3])
    cases = parse(next(D.glob(f"in_level-6_{key}*.txt")).read_text())
    best = json.loads((D / "merged" / f"{key}.json").read_text())
    order = sorted(range(len(cases)), key=lambda i: -len(best[str(i)]))[:N]
    jobs = [(vi, ci, cases[ci][0], sorted(cases[ci][1]), cases[ci][2], kw) for vi, kw in enumerate(vs) for ci in order]
    res = {}
    with Pool(int(sys.argv[4]) if len(sys.argv) > 4 else 4) as p:
        for vi, ci, L in p.imap_unordered(work, jobs):
            res.setdefault(vi, {})[ci] = L
    print("current best:", sum(len(best[str(ci)]) for ci in order))
    for vi, kw in enumerate(vs):
        print(kw, sum(res[vi].values()))
