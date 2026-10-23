"""CP-SAT re-optimization of the final tail of level 6 programs.

For the last repetition, take the incumbent's state at tick t0 (positions, activity,
matter) and search for the shortest instruction sequence that completes the pattern
without ever painting a skirt cell. Cells already painted are added to the model lazily
when a candidate would erase them. Every result is re-checked with the full simulator.

Run with the Python 3.12 that matches OR-Tools:
  <py312> tail6.py <key> [procs] [seconds per solve] [tail lengths, e.g. 12,18,24]
Improvements -> levels/level6/optimized_tail_claude/<key>/case_<i>.txt
"""
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, r"C:\Users\david\.cache\ccc2026-optimizer-deps")
sys.path.insert(0, str(Path(__file__).parent))
from ortools.sat.python import cp_model  # noqa: E402
from validate_level6_optimized import FIRE_DIRECTIONS, geometry, read_cases, simulate  # noqa: E402

D = Path(__file__).parent.parent / "levels" / "level6"
NAMES = ["example", "small", "medium", "large", "enormous"]


def state_after(case, prog):
    cells, beams = geometry(case.radius)
    n = 6 * case.radius
    P = sum(cells[c] for c in case.pattern)
    pos = [i * case.radius for i in range(6)]
    on = [False] * 6
    M = 0
    done = 0
    for row in prog:
        for e, x in enumerate(row):
            if x == "F":
                pos[e] = (pos[e] + 1) % n
            elif x == "B":
                pos[e] = (pos[e] - 1) % n
            elif x == "T":
                on[e] = not on[e]
        one = two = three = 0
        for e in range(6):
            if on[e]:
                b = beams[e][pos[e]]
                three |= two & b
                two |= one & b
                one |= b
        M = (M | two) & ~three
        if M & P == P:
            M &= ~P
            done += 1
    return pos, on, M, done


def solve_tail(case, pos0, on0, M0, T, protect, seconds):
    cells, beams = geometry(case.radius)
    n = 6 * case.radius
    P = set(case.pattern)
    skirts = set()
    for r, c in P:
        for dr, dc in FIRE_DIRECTIONS:
            k = (r + dr, c + dc)
            if k in cells and k not in P:
                skirts.add(k)
    todo = [c for c in sorted(P) if not M0 & cells[c]]
    keep = [c for c in sorted(protect) if M0 & cells[c]]
    m = cp_model.CpModel()
    p = [[m.NewIntVar(0, n - 1, "") for _ in range(T)] for _ in range(6)]
    on = [[m.NewBoolVar("") for _ in range(T)] for _ in range(6)]
    q = [[m.NewIntVar(0, n, "") for _ in range(T)] for _ in range(6)]
    linked = [(x, 1, x) for x in range(n)] + [(x, 0, n) for x in range(n)]
    trans = []
    for x in range(n):
        for en in (0, 1):
            trans.extend([(x, en, (x + mv) % n, en) for mv in (-1, 0, 1)])
            trans.append((x, en, x, 1 - en))
    for d in range(6):
        first = [t for t in trans if t[0] == pos0[d] and t[1] == int(on0[d])]
        m.AddAllowedAssignments([p[d][0], on[d][0]], [(a, b) for _, _, a, b in first])
        for t in range(T):
            m.AddAllowedAssignments([p[d][t], on[d][t], q[d][t]], linked)
            if t + 1 < T:
                m.AddAllowedAssignments([p[d][t], on[d][t], p[d][t + 1], on[d][t + 1]], trans)
    table = {}

    def count_var(cell, t):
        bit = cells[cell]
        hits = []
        for d in range(6):
            key = (d, cell)
            if key not in table:
                table[key] = [int(bool(ray & bit)) for ray in beams[d]] + [0]
            h = m.NewBoolVar("")
            m.AddElement(q[d][t], table[key], h)
            hits.append(h)
        cnt = m.NewIntVar(0, 6, "")
        m.Add(cnt == sum(hits))
        return cnt

    for cell in skirts:
        for t in range(T):
            m.AddAllowedAssignments([count_var(cell, t)], [(v,) for v in (0, 1, 3, 4, 5, 6)])
    final = []
    for cell in todo + keep:
        prev = 0 if cell in todo else 1
        for t in range(T):
            cnt = count_var(cell, t)
            painted = m.NewBoolVar("")
            m.Add(cnt == 2).OnlyEnforceIf(painted)
            m.Add(cnt != 2).OnlyEnforceIf(painted.Not())
            erased = m.NewBoolVar("")
            m.Add(cnt >= 3).OnlyEnforceIf(erased)
            m.Add(cnt <= 2).OnlyEnforceIf(erased.Not())
            mat = m.NewBoolVar("")
            m.Add(mat >= painted)
            m.Add(mat <= painted + prev)
            m.Add(mat <= 1 - erased)
            m.Add(mat >= prev - erased)
            prev = mat
        final.append(prev)
    for v in final:
        m.Add(v == 1)
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = seconds
    s.parameters.num_search_workers = 1
    st = s.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    rows = []
    cp, co = list(pos0), [bool(x) for x in on0]
    for t in range(T):
        row = []
        for d in range(6):
            np_, no = s.Value(p[d][t]), bool(s.Value(on[d][t]))
            if no != co[d]:
                row.append("T")
            elif np_ == cp[d]:
                row.append("-")
            elif (np_ - cp[d]) % n == 1:
                row.append("F")
            else:
                row.append("B")
            cp[d], co[d] = np_, no
        rows.append(tuple(row))
    return rows


def work(args):
    i, case, inc, tails, secs = args
    best = [tuple(r) for r in inc]
    t_start = time.time()
    res0 = simulate(case, best, record_ticks=True)
    last_start = res0["accepted_at"][-2] if case.count > 1 else 0
    for L in tails:
        t0 = len(best) - L
        if t0 < last_start:
            t0 = last_start
        L = len(best) - t0
        if L < 3:
            continue
        pos0, on0, M0, _ = state_after(case, best[:t0])
        protect = set()
        T = L - 1
        while T >= 1:
            sol = None
            for _attempt in range(4):
                sol = solve_tail(case, pos0, on0, M0, T, protect, secs)
                if sol is None:
                    break
                cand = best[:t0] + sol
                r = simulate(case, cand, record_ticks=True)
                if r["accepted"] >= case.count:
                    cand = cand[:r["accepted_at"][case.count - 1]]
                    if simulate(case, cand)["valid"]:
                        best = cand
                        break
                # find erased cells and protect them
                cells, _ = geometry(case.radius)
                _, _, Mx, _ = state_after(case, best[:t0] + sol)
                lost = {c for c in case.pattern if M0 & cells[c] and not Mx & cells[c]}
                if not lost - protect:
                    sol = None
                    break
                protect |= lost
                sol = None
            if sol is None:
                break
            T = len(best) - t0 - 1
    return i, len(inc), best, time.time() - t_start


def main():
    fi = int(sys.argv[1])
    procs = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    secs = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
    tails = [int(x) for x in (sys.argv[4] if len(sys.argv) > 4 else "12,18").split(",")]
    name = NAMES[fi]
    cases = read_cases(D / f"in_level-6_{fi}-{name}.txt")
    merged = json.loads((D / "merged" / f"{fi}.json").read_text())
    out = D / "optimized_tail_claude" / str(fi)
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(i, c, merged[str(i)], tails, secs) for i, c in enumerate(cases)]
    jobs.sort(key=lambda j: -len(j[2]))
    saved = 0
    with Pool(procs) as pool:
        for i, before, best, dt in pool.imap_unordered(work, jobs):
            if len(best) < before:
                saved += before - len(best)
                (out / f"case_{i}.txt").write_text("\n".join(" ".join(r) for r in best) + "\n")
                print(f"{name} case {i}: {before} -> {len(best)} (saved so far {saved}, {dt:.0f}s)", flush=True)
    print(f"DONE {name}: saved {saved}", flush=True)


if __name__ == "__main__":
    main()
