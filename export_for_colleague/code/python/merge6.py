"""Merge every level 6 candidate program per case, keep the shortest valid one, then
improve with the transition-graph BFS from level6_cycles (union of all candidates).

Usage: python merge6.py [keys, default 1,2,3,4]
Writes levels/level6/merged/out_<name>.txt and merged/<key>.json. Every kept program is
checked with both validate_level6_optimized.simulate and our own level5.simulate.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from level5 import simulate as sim5  # noqa: E402
from level6 import parse  # noqa: E402
from level6_cycles import shortest  # noqa: E402
from validate_level6_optimized import read_cases, read_programs, simulate  # noqa: E402

D = Path(__file__).parent.parent / "levels" / "level6"
OUT = D / "merged"
NAMES = ["example", "small", "medium", "large", "enormous"]


def candidates(fi, name, n):
    alts = [[] for _ in range(n)]

    def add_file(p):
        if p.exists():
            progs = read_programs(p)
            if len(progs) == n:
                for a, prog in zip(alts, progs):
                    a.append(prog)

    for p in [D / f"out_level-6_{fi}-{name}.txt", D / f"candidate-route-{fi}.txt",
              D / "v3" / f"out_level-6_{fi}-{name}.txt", D / "best" / f"out_level-6_{fi}-{name}.txt",
              D / "merged" / f"out_level-6_{fi}-{name}.txt", D / "optimized_final" / f"out_level-6_{fi}-{name}.txt",
              D.parent.parent / "cs_root" / "Lösungen" / "level6_cs" / f"out_level-6_{fi}-{name}.txt"]:
        add_file(p)
    for j in (D / "best" / f"{fi}.json",):
        if j.exists():
            b = json.loads(j.read_text())
            for i in range(n):
                if str(i) in b:
                    alts[i].append([tuple(l) for l in b[str(i)]])
    for d in D.iterdir():
        if d.is_dir() and (d.name.startswith("optimized_") or d.name == "round2_prefixes"):
            for sub in (name, str(fi)):
                for p in (d / sub).glob("case_*.txt"):
                    try:
                        i = int(p.stem.split("_")[1])
                        progs = read_programs(p)
                    except Exception:  # noqa: BLE001
                        continue
                    if progs and i < n:
                        alts[i].append(progs[0])
    return alts


def main():
    keys = [int(k) for k in (sys.argv[1] if len(sys.argv) > 1 else "1,2,3,4").split(",")]
    OUT.mkdir(exist_ok=True)
    total = 0
    for fi in keys:
        name = NAMES[fi]
        fin = D / f"in_level-6_{fi}-{name}.txt"
        cases = read_cases(fin)
        mycases = parse(fin.read_text())
        alts = candidates(fi, name, len(cases))
        best = []
        before = after = 0
        for i, (case, progs) in enumerate(zip(cases, alts)):
            valid = [p for p in progs if simulate(case, p)["valid"]]
            old = min(valid, key=len)
            try:
                new = shortest(case, valid)
            except Exception:  # noqa: BLE001
                new = old
            if len(new) > len(old) or not simulate(case, new)["valid"]:
                new = old
            r, pat, cnt = mycases[i]
            assert sim5(r, pat, [list(l) for l in new]) == cnt, f"own simulator disagrees on case {i}"
            before += len(old)
            after += len(new)
            best.append([list(l) for l in new])
        (OUT / f"{fi}.json").write_text(json.dumps({str(i): b for i, b in enumerate(best)}))
        text = "\n\n".join("\n".join(" ".join(l) for l in b) for b in best)
        (OUT / f"out_level-6_{fi}-{name}.txt").write_text(text + "\n")
        print(f"{name}: min-merge {before}, after route BFS {after}", flush=True)
        if fi >= 2:
            total += after
    print("TOTAL scored (medium+large+enormous):", total)


if __name__ == "__main__":
    main()
