"""Level 6, greedy painter.

Emitter A is toggled, emitter B stays on after the first paint. While A is on, every
tick paints the intersection of both beams, so we only keep A on while that
intersection is outside the board or a pattern cell. BFS (A on) finds the nearest
unpainted cell; otherwise A is switched off, both emitters relocate, and A comes back on.
"""
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: E402,F403
from level1 import board  # noqa: E402
from level4 import beam_cells, ring, start_index  # noqa: E402
from level5 import simulate  # noqa: E402
from level6 import PARALLEL, parse  # noqa: E402

STEP = {"F": 1, "B": -1, "-": 0}


def mv(cur, tgt, n):
    if cur == tgt:
        return "-"
    fwd = (tgt - cur) % n
    return "F" if fwd <= n - fwd else "B"


def rd(a, b, n):
    d = (b - a) % n
    return min(d, n - d)


class Geo:
    def __init__(self, r):
        self.r = r
        grid = [list(l) for l in board(r).splitlines()]
        self.pts = ring(r)
        self.n = len(self.pts)
        self.beams = {d: [set(beam_cells(grid, rr, cc, str(d))) for rr, cc in self.pts] for d in range(1, 7)}
        self.entry = {}
        for d in range(1, 7):
            m = {}
            for idx, b in enumerate(self.beams[d]):
                for cell in b:
                    m[cell] = idx
            self.entry[d] = m
        self._inter = {}

    def inter(self, ea, eb):
        key = (ea, eb)
        if key not in self._inter:
            n = self.n
            tab = [[None] * n for _ in range(n)]
            for a in range(n):
                ba = self.beams[ea][a]
                if not ba:
                    continue
                for b in range(n):
                    s = ba & self.beams[eb][b]
                    if s:
                        tab[a][b] = next(iter(s))
            self._inter[key] = tab
        return self._inter[key]


def plan(geo, pat, cnt, ea, eb, limit=None):
    n = geo.n
    inter = geo.inter(ea, eb)
    enA, enB = geo.entry[ea], geo.entry[eb]
    pa, pb = start_index(geo.r, ea), start_index(geo.r, eb)
    a_on = b_on = False
    lines = []

    def emit(ia, ib):
        l = ["-"] * 6
        l[ea - 1] = ia
        l[eb - 1] = ib
        lines.append(l)

    painted = set()
    done = 0
    total = len(pat)
    while done < cnt:
        if limit is not None and len(lines) > limit:
            return None
        todo = [c for c in pat if c not in painted]
        # option 2: relocate cost
        best_c, best_cost = None, None
        for c in todo:
            dA, dB = rd(pa, enA[c], n), rd(pb, enB[c], n)
            if not b_on:
                cost = max(dA, dB) + 1
            elif a_on:
                cost = 2 + max(dA, max(0, dB - 2))
            else:
                cost = 1 + max(dA, max(0, dB - 1))
            if best_cost is None or cost < best_cost:
                best_c, best_cost = c, cost
        # option 1: BFS with A on
        path = None
        if a_on:
            prev = {(pa, pb): None}
            q = deque([(pa, pb, 0)])
            found = None
            while q:
                x, y, d = q.popleft()
                if d + 1 >= best_cost:
                    continue
                for sa in (0, 1, -1):
                    for sb in (0, 1, -1):
                        nx, ny = (x + sa) % n, (y + sb) % n
                        if (nx, ny) in prev:
                            continue
                        cell = inter[nx][ny]
                        if cell is not None and cell not in pat:
                            continue
                        prev[(nx, ny)] = (x, y, sa, sb)
                        if cell is not None and cell not in painted:
                            found = (nx, ny)
                            break
                        q.append((nx, ny, d + 1))
                    if found:
                        break
                if found:
                    break
            if found:
                path = []
                s = found
                while prev[s] is not None:
                    x, y, sa, sb = prev[s]
                    path.append((sa, sb))
                    s = (x, y)
                path.reverse()
        if path is not None:
            for sa, sb in path:
                pa, pb = (pa + sa) % n, (pb + sb) % n
                ia = {1: "F", -1: "B", 0: "-"}[sa]
                ib = {1: "F", -1: "B", 0: "-"}[sb]
                emit(ia, ib)
                cell = inter[pa][pb]
                if cell is not None:
                    painted.add(cell)
        else:
            ta, tb = enA[best_c], enB[best_c]
            if not b_on:
                while pa != ta or pb != tb:
                    ia, ib = mv(pa, ta, n), mv(pb, tb, n)
                    pa, pb = (pa + STEP[ia]) % n, (pb + STEP[ib]) % n
                    emit(ia, ib)
                emit("T", "T")
                a_on = b_on = True
            else:
                if a_on:
                    ib = mv(pb, tb, n)
                    pb = (pb + STEP[ib]) % n
                    emit("T", ib)
                    a_on = False
                while pa != ta or rd(pb, tb, n) > 1:
                    ia, ib = mv(pa, ta, n), mv(pb, tb, n)
                    pa, pb = (pa + STEP[ia]) % n, (pb + STEP[ib]) % n
                    emit(ia, ib)
                ib = mv(pb, tb, n)
                pb = (pb + STEP[ib]) % n
                emit("T", ib)
                a_on = True
            painted.add(inter[pa][pb])
        if len(painted) == total:
            painted = set()
            done += 1
    return lines


def solve_case(geo, pat, cnt):
    best = None
    for ea in range(1, 7):
        for eb in range(1, 7):
            if ea == eb or (ea, eb) in PARALLEL:
                continue
            lines = plan(geo, pat, cnt, ea, eb, None if best is None else len(best))
            if lines is not None and (best is None or len(lines) < len(best)):
                best = lines
    assert simulate(geo.r, pat, best) == cnt, "simulation mismatch"
    return best


def solve(text):
    geos = {}
    progs = []
    total = 0
    for r, pat, cnt in parse(text):
        geo = geos.setdefault(r, Geo(r))
        lines = solve_case(geo, pat, cnt)
        total += len(lines)
        progs.append("\n".join(" ".join(l) for l in lines))
    print(f"  score (total lines): {total}", file=sys.stderr)
    return "\n\n".join(progs)
