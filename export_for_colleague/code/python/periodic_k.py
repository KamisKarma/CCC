"""CP-SAT search for repeating cycles that submit the pattern k times per cycle.

Generalizes level6_periodic.solve (k=1): a cycle of `length` phases, the pattern is
submitted at exactly k phases (always including the last), so the cost per copy is
length/k instead of an integer. Matter that is submitted is cleared before the next
phase, exactly like the simulator. Run with the Python 3.12 matching OR-Tools:
  <py312> periodic_k.py <key> [procs] [seconds] [min per-rep]
Improvements -> levels/level6/optimized_periodic_k/<key>/case_<i>.txt
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


def solve(case, length, k, incumbent, seconds):
    cells, beams = geometry(case.radius)
    n = 6 * case.radius
    targets = sorted(case.pattern)
    skirts = set()
    for r, c in targets:
        for dr, dc in FIRE_DIRECTIONS:
            cell = (r + dr, c + dc)
            if cell in cells and cell not in case.pattern:
                skirts.add(cell)
    m = cp_model.CpModel()
    p = [[m.NewIntVar(0, n - 1, "") for _ in range(length)] for _ in range(6)]
    on = [[m.NewBoolVar("") for _ in range(length)] for _ in range(6)]
    q = [[m.NewIntVar(0, n, "") for _ in range(length)] for _ in range(6)]
    linked = [(x, 1, x) for x in range(n)] + [(x, 0, n) for x in range(n)]
    trans = []
    for x in range(n):
        for en in (0, 1):
            trans.extend([(x, en, (x + mv) % n, en) for mv in (-1, 0, 1)])
            trans.append((x, en, x, 1 - en))
    for d in range(6):
        for t in range(length):
            m.AddAllowedAssignments([p[d][t], on[d][t], q[d][t]], linked)
            if length > 1:
                m.AddAllowedAssignments([p[d][t], on[d][t], p[d][(t + 1) % length], on[d][(t + 1) % length]], trans)

    def count_var(cell, t):
        bit = cells[cell]
        hits = []
        for d in range(6):
            h = m.NewBoolVar("")
            m.AddElement(q[d][t], [int(bool(ray & bit)) for ray in beams[d]] + [0], h)
            hits.append(h)
        cnt = m.NewIntVar(0, 6, "")
        m.Add(cnt == sum(hits))
        return cnt

    for cell in skirts:
        for t in range(length):
            cnt = count_var(cell, t)
            m.AddAllowedAssignments([cnt], [(v,) for v in (0, 1, 3, 4, 5, 6)])
    comp = [m.NewBoolVar("") for _ in range(length)]
    prev = {cell: 0 for cell in targets}
    pre = [[None] * len(targets) for _ in range(length)]
    for t in range(length):
        for j, cell in enumerate(targets):
            cnt = count_var(cell, t)
            painted = m.NewBoolVar("")
            m.Add(cnt == 2).OnlyEnforceIf(painted)
            m.Add(cnt != 2).OnlyEnforceIf(painted.Not())
            erased = m.NewBoolVar("")
            m.Add(cnt >= 3).OnlyEnforceIf(erased)
            m.Add(cnt <= 2).OnlyEnforceIf(erased.Not())
            mat = m.NewBoolVar("")
            pv = prev[cell]
            m.Add(mat >= painted)
            m.Add(mat <= painted + pv)
            m.Add(mat <= 1 - erased)
            m.Add(mat >= pv - erased)
            pre[t][j] = mat
            m.Add(mat >= comp[t])
        m.Add(sum(pre[t]) <= len(targets) - 1 + comp[t])
        for j, cell in enumerate(targets):
            post = m.NewBoolVar("")
            m.Add(post <= pre[t][j])
            m.Add(post <= 1 - comp[t])
            m.Add(post >= pre[t][j] - comp[t])
            prev[cell] = post
    m.Add(comp[length - 1] == 1)
    m.Add(sum(comp) == k)
    dists = []
    for d in range(6):
        dist = m.NewIntVar(0, n // 2, "")
        m.AddElement(p[d][0], [min((v - d * case.radius) % n, (d * case.radius - v) % n) for v in range(n)], dist)
        dists.append(dist)
    startup = m.NewIntVar(0, n // 2, "")
    m.AddMaxEquality(startup, dists)
    cycles_before_last = (case.count - 1) // k
    m.Add(startup + 1 + cycles_before_last * length + (length - 1) < len(incumbent))
    m.Minimize(startup)
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = seconds
    s.parameters.num_search_workers = 1
    s.parameters.random_seed = 7
    st = s.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    pos = [[s.Value(p[d][t]) for t in range(length)] for d in range(6)]
    act = [[s.Value(on[d][t]) for t in range(length)] for d in range(6)]
    now = [d * case.radius for d in range(6)]
    prog = []
    while any(now[d] != pos[d][0] for d in range(6)):
        row = []
        for d in range(6):
            diff = (pos[d][0] - now[d]) % n
            cmd = "-" if diff == 0 else ("F" if diff <= n // 2 else "B")
            row.append(cmd)
            now[d] = (now[d] + (1 if cmd == "F" else -1 if cmd == "B" else 0)) % n
        prog.append(tuple(row))
    prog.append(tuple("T" if act[d][0] else "-" for d in range(6)))
    for i in range((case.count // k + 2) * length):
        a, b = i % length, (i + 1) % length
        row = []
        for d in range(6):
            if act[d][a] != act[d][b]:
                cmd = "T"
            elif pos[d][a] == pos[d][b]:
                cmd = "-"
            elif (pos[d][b] - pos[d][a]) % n == 1:
                cmd = "F"
            else:
                cmd = "B"
            row.append(cmd)
        prog.append(tuple(row))
    res = simulate(case, prog, record_ticks=True)
    if res["accepted"] < case.count:
        return None
    prog = prog[:res["accepted_at"][case.count - 1]]
    if not simulate(case, prog)["valid"]:
        return None
    return prog if len(prog) < len(incumbent) else None


def work(args):
    fi, i, case, inc, secs = args
    best = inc
    t0 = time.time()
    per = len(inc) / case.count
    for k in (2, 3):
        # from the longest cycle that could still beat the incumbent, shorten while feasible
        L = int(per * k)
        while L > k:
            if L % k == 0:
                L -= 1
                continue  # k=1 search already covers whole multiples
            if 1 + ((case.count - 1) // k) * L + (L - 1) >= len(best):
                L -= 1
                continue
            try:
                res = solve(case, L, k, best, secs)
            except Exception as ex:  # noqa: BLE001
                print("ERR", i, k, L, ex, flush=True)
                break
            if res is None:
                break
            best = res
            L -= 1
    return fi, i, len(inc), best, time.time() - t0


def main():
    fi = int(sys.argv[1])
    procs = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    secs = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
    min_per = float(sys.argv[4]) if len(sys.argv) > 4 else 2.5
    name = NAMES[fi]
    cases = read_cases(D / f"in_level-6_{fi}-{name}.txt")
    merged = json.loads((D / "merged" / f"{fi}.json").read_text())
    out = D / "optimized_periodic_k" / str(fi)
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for i, case in enumerate(cases):
        inc = [tuple(l) for l in merged[str(i)]]
        if case.count >= 4 and len(inc) / case.count >= min_per and len(case.pattern) <= 30:
            jobs.append((fi, i, case, inc, secs))
    jobs.sort(key=lambda j: -j[2].count)
    print(f"{len(jobs)} cases", flush=True)
    saved = 0
    with Pool(procs) as pool:
        for _, i, before, best, dt in pool.imap_unordered(work, jobs):
            if len(best) < before:
                saved += before - len(best)
                (out / f"case_{i}.txt").write_text("\n".join(" ".join(r) for r in best) + "\n")
                print(f"{name} case {i}: {before} -> {len(best)} (saved so far {saved}, {dt:.0f}s)", flush=True)
    print(f"DONE {name}: saved {saved}", flush=True)


if __name__ == "__main__":
    main()
