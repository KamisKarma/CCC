import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: E402,F403
from level1 import board  # noqa: E402
from level4 import beam_cells, ring, start_index  # noqa: E402
from level5 import simulate  # noqa: E402

PARALLEL = {(1, 4), (4, 1), (2, 5), (5, 2), (3, 6), (6, 3)}


def parse(text):
    lines = text.splitlines()
    n = int(lines[0])
    i = 1
    cases = []
    for _ in range(n):
        while not lines[i].strip():
            i += 1
        r, h, w, cnt = ints(lines[i])
        pgrid = lines[i + 1:i + 1 + h]
        pat = {(a, b) for a, row in enumerate(pgrid) for b, ch in enumerate(row.strip()) if ch == "M"}
        cases.append((r, pat, cnt))
        i += 1 + h
    return cases


def entry_map(r):
    """entry[d][cell] = ring index from which emitter d's beam passes through cell."""
    grid = [list(l) for l in board(r).splitlines()]
    pts = ring(r)
    entry = {}
    for d in range(1, 7):
        m = {}
        for idx, (rr, cc) in enumerate(pts):
            for cell in beam_cells(grid, rr, cc, str(d)):
                m[cell] = idx
        entry[d] = m
    return entry


def ring_step(cur, tgt, n):
    if cur == tgt:
        return 0, "-"
    fwd = (tgt - cur) % n
    return (1, "F") if fwd <= n - fwd else (-1, "B")


def ring_dist(a, b, n):
    d = (b - a) % n
    return min(d, n - d)


def build(r, cells_order, ea, eb, entry, n):
    """ea is toggled per cell, eb stays on. Returns list of 6-instruction lines."""
    pa = start_index(r, ea)
    pb = start_index(r, eb)
    lines = []

    def line(ia, ib):
        l = ["-"] * 6
        l[ea - 1] = ia
        l[eb - 1] = ib
        return l

    # turn eb on, move ea toward first target
    ta = entry[ea][cells_order[0]]
    s, ia = ring_step(pa, ta, n)
    pa = (pa + s) % n
    lines.append(line(ia, "T"))
    pending_off = False
    for cell in cells_order:
        ta, tb = entry[ea][cell], entry[eb][cell]
        if pending_off:
            # off tick for ea; eb may move one step
            s, ib = ring_step(pb, tb, n)
            pb = (pb + s) % n
            lines.append(line("T", ib))
        while pa != ta or ring_dist(pb, tb, n) > 1:
            sa, ia = ring_step(pa, ta, n)
            sb, ib = ring_step(pb, tb, n)
            pa, pb = (pa + sa) % n, (pb + sb) % n
            lines.append(line(ia, ib))
        sb, ib = ring_step(pb, tb, n)
        pb = (pb + sb) % n
        lines.append(line("T", ib))  # on tick: creates matter at intersection
        pending_off = True
    return lines


def order_cells(start_cells, entry, ea, eb, n, r):
    # greedy nearest neighbour by max(ring distances)
    rem = set(start_cells)
    pa, pb = start_index(r, ea), start_index(r, eb)
    out = []
    while rem:
        c = min(rem, key=lambda c: (max(ring_dist(pa, entry[ea][c], n), ring_dist(pb, entry[eb][c], n) - 2), c))
        out.append(c)
        rem.remove(c)
        pa, pb = entry[ea][c], entry[eb][c]
    return out


def solve_case(r, pat, cnt):
    entry = entry_map(r)
    n = len(ring(r))
    best = None
    for ea in range(1, 7):
        for eb in range(1, 7):
            if ea == eb or (ea, eb) in PARALLEL:
                continue
            order = order_cells(pat, entry, ea, eb, n, r)
            lines = build(r, order * cnt, ea, eb, entry, n)
            if best is None or len(lines) < len(best):
                best = lines
    assert simulate(r, pat, best) == cnt, "simulation mismatch"
    return best


def solve(text):
    progs = []
    total = 0
    for r, pat, cnt in parse(text):
        lines = solve_case(r, pat, cnt)
        total += len(lines)
        progs.append("\n".join(" ".join(l) for l in lines))
    print(f"  score (total lines): {total}", file=sys.stderr)
    return "\n\n".join(progs)
