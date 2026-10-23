"""Local compression of level 6 programs: delete single lines or merge adjacent lines
(when they touch disjoint emitters), keeping only changes that stay valid.

Usage: python compress6.py <keys e.g. 2,3,4>
Reads merged/<key>.json, writes improvements to optimized_compress_claude/<key>/case_<i>.txt
"""
import json
import sys
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from validate_level6_optimized import read_cases, simulate  # noqa: E402

D = Path(__file__).parent.parent / "levels" / "level6"
NAMES = ["example", "small", "medium", "large", "enormous"]


def valid(case, prog):
    return simulate(case, prog)["valid"]


def compress(args):
    i, case, prog = args
    prog = [tuple(l) for l in prog]
    orig = len(prog)
    changed = True
    while changed:
        changed = False
        j = 0
        while j < len(prog):
            cand = prog[:j] + prog[j + 1:]
            if valid(case, cand):
                prog = cand
                changed = True
                continue
            if j + 1 < len(prog):
                a, b = prog[j], prog[j + 1]
                if all(x == "-" or y == "-" for x, y in zip(a, b)):
                    merged = tuple(x if x != "-" else y for x, y in zip(a, b))
                    cand = prog[:j] + [merged] + prog[j + 2:]
                    if valid(case, cand):
                        prog = cand
                        changed = True
                        continue
            j += 1
    return i, orig, prog


def main():
    for fi in [int(k) for k in sys.argv[1].split(",")]:
        name = NAMES[fi]
        cases = read_cases(D / f"in_level-6_{fi}-{name}.txt")
        merged = json.loads((D / "merged" / f"{fi}.json").read_text())
        out = D / "optimized_compress_claude" / str(fi)
        out.mkdir(parents=True, exist_ok=True)
        saved = 0
        with Pool(8) as pool:
            for i, orig, prog in pool.imap_unordered(compress, [(i, c, merged[str(i)]) for i, c in enumerate(cases)]):
                if len(prog) < orig:
                    saved += orig - len(prog)
                    (out / f"case_{i}.txt").write_text("\n".join(" ".join(r) for r in prog) + "\n")
        print(f"{name}: compression saved {saved}", flush=True)


if __name__ == "__main__":
    main()
