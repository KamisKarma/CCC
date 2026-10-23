"""Level 6, multi-emitter greedy.

All 6 emitters are used. Each tick, instructions are chosen by coordinate descent to
maximize newly painted pattern cells (plus a positioning potential), under the
constraint that no matter is ever created on a non-pattern cell adjacent to the pattern
(stray matter elsewhere is allowed by the rules). Board state is kept as bitmasks.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: E402,F403
from level1 import board  # noqa: E402
from level4 import beam_cells, ring, start_index  # noqa: E402
from level5 import simulate  # noqa: E402
from level6 import parse  # noqa: E402
import level6b  # noqa: E402

NEIGH = [(0, 2), (0, -2), (1, 1), (1, -1), (-1, 1), (-1, -1)]
OPTS = "-FBT"
# non-parallel emitter pairs (0-based); parallel ones are (0,3), (1,4), (2,5)
_PAIRS = [(a, b) for a in range(6) for b in range(a + 1, 6) if b - a != 3]
PA = np.array([a for a, _ in _PAIRS])
PB = np.array([b for _, b in _PAIRS])


def popcount(x):
    return bin(x).count("1")


class Geo:
    def __init__(self, r):
        self.r = r
        grid = [list(l) for l in board(r).splitlines()]
        self.cells = [(a, b) for a, row in enumerate(grid) for b, ch in enumerate(row) if ch == "O"]
        self.bit = {c: 1 << i for i, c in enumerate(self.cells)}
        self.pts = ring(r)
        self.n = len(self.pts)
        self.beam = {}
        self.entry = {}
        for d in range(1, 7):
            self.beam[d] = []
            self.entry[d] = {}
            for idx, (rr, cc) in enumerate(self.pts):
                m = 0
                for cell in beam_cells(grid, rr, cc, str(d)):
                    m |= self.bit[cell]
                    self.entry[d][cell] = idx
                self.beam[d].append(m)

    def mask(self, cells):
        m = 0
        for c in cells:
            m |= self.bit[c]
        return m

    def neighbours_mask(self, cells):
        m = 0
        for (a, b) in cells:
            for da, db in NEIGH:
                c = (a + da, b + db)
                if c in self.bit:
                    m |= self.bit[c]
        return m


def beams_eval(masks):
    ones = twos = threes = 0
    for b in masks:
        threes |= twos & b
        twos |= ones & b
        ones |= b
    return twos & ~threes, threes


def plan(geo, pat, cnt, max_ticks, stall_th=2, w_min=10, w_mean=1.0, seed=None):
    import random
    rng = random.Random(seed) if seed is not None else None
    n = geo.n
    P = geo.mask(pat)
    forbidden = geo.neighbours_mask(pat) & ~P
    pat_list = sorted(pat)
    pat_idx = [geo.bit[c].bit_length() - 1 for c in pat_list]
    ent = np.array([[geo.entry[e][c] for c in pat_list] for e in range(1, 7)])
    pos = [start_index(geo.r, e) for e in range(1, 7)]
    on = [False] * 6
    M = 0
    done = 0
    lines = []
    stall = 0

    def apply(ins):
        npos = list(pos)
        non = list(on)
        for e, o in enumerate(ins):
            if o == "F":
                npos[e] = (npos[e] + 1) % n
            elif o == "B":
                npos[e] = (npos[e] - 1) % n
            elif o == "T":
                non[e] = not non[e]
        return npos, non

    def evaluate(ins):
        npos, non = apply(ins)
        bm = [geo.beam[e + 1][npos[e]] for e in range(6)]
        ex2, ge3 = beams_eval([bm[e] for e in range(6) if non[e]])
        newM = (M | ex2) & ~ge3
        if newM & forbidden:
            return None
        gain = popcount(newM & P) - popcount(M & P)
        todo = P & ~newM
        if not todo:
            return gain * 1000 + 500
        idx = [i for i, ci in enumerate(pat_idx) if not (todo >> ci) & 1]
        keep = np.ones(len(pat_idx), bool)
        keep[idx] = False
        p = np.array(npos)[:, None]
        dd = np.abs(ent - p) % n
        dd = np.minimum(dd, n - dd)[:, keep]
        # emitters that are off need one extra tick to toggle on
        dd = dd + (~np.array(non))[:, None]
        second = np.maximum(dd[PA], dd[PB]).min(axis=0)
        v = gain * 1000 - w_min * int(second.min()) - w_mean * float(second.mean())
        if rng is not None:
            v += rng.random() * 0.5
        return v

    forced = None

    def forced_ins(target, e1, e2):
        ins = ["-"] * 6
        ready = True
        for e in (e1, e2):
            t = geo.entry[e + 1][target]
            if pos[e] != t:
                ready = False
        for e in range(6):
            if e in (e1, e2):
                t = geo.entry[e + 1][target]
                if pos[e] != t:
                    ins[e] = "T" if on[e] else level6b.mv(pos[e], t, n)
                elif ready and not on[e]:
                    ins[e] = "T"
            elif on[e]:
                ins[e] = "T"
        return ins

    def pick_forced():
        todo = [c for c in pat_list if not (M >> (geo.bit[c].bit_length() - 1)) & 1]
        best_t = None
        for c in todo:
            for e1, e2 in _PAIRS:
                d1 = level6b.rd(pos[e1], geo.entry[e1 + 1][c], n)
                d2 = level6b.rd(pos[e2], geo.entry[e2 + 1][c], n)
                cost = max(d1, d2)
                if best_t is None or cost < best_t[0]:
                    best_t = (cost, c, e1, e2)
        return best_t[1:]

    while done < cnt:
        if len(lines) >= max_ticks:
            return None
        if forced is None and stall >= stall_th:
            forced = pick_forced()
        if forced is not None:
            ins = forced_ins(*forced)
            target_bit = geo.bit[forced[0]]
            before = popcount(M & P)
            pos, on = apply(ins)
            bm = [geo.beam[e + 1][pos[e]] for e in range(6) if on[e]]
            ex2, ge3 = beams_eval(bm)
            M = (M | ex2) & ~ge3
            if M & forbidden:
                return None
            lines.append(ins)
            if M & target_bit:
                forced = None
                stall = 0
            if M & P == P:
                M &= ~P
                done += 1
                forced = None
                stall = 0
            continue
        ins = ["-"] * 6
        best = evaluate(ins)
        if best is None:
            best = -10 ** 9
        for _ in range(3):
            improved = False
            base_ins = ins
            for e in range(6):
                for o in OPTS:
                    if o == base_ins[e]:
                        continue
                    cand = list(base_ins)
                    cand[e] = o
                    v = evaluate(cand)
                    if v is not None and v > best:
                        best, ins, improved = v, cand, True
            for e1 in range(6):
                for e2 in range(e1 + 1, 6):
                    for o1 in OPTS:
                        if o1 == base_ins[e1]:
                            continue
                        for o2 in OPTS:
                            if o2 == base_ins[e2]:
                                continue
                            cand = list(base_ins)
                            cand[e1], cand[e2] = o1, o2
                            v = evaluate(cand)
                            if v is not None and v > best:
                                best, ins, improved = v, cand, True
            if not improved:
                break
        before = popcount(M & P)
        pos, on = apply(ins)
        bm = [geo.beam[e + 1][pos[e]] for e in range(6) if on[e]]
        ex2, ge3 = beams_eval(bm)
        M = (M | ex2) & ~ge3
        if M & forbidden:
            return None
        lines.append(ins)
        if M & P == P:
            M &= ~P
            done += 1
            stall = 0
        elif popcount(M & P) > before:
            stall = 0
        else:
            stall += 1
            if stall > 3 * n:
                return None
    return lines


def solve_case(geo, geo_b, pat, cnt):
    base = level6b.solve_case(geo_b, pat, cnt)
    best = base
    lines = plan(geo, pat, cnt, len(best))
    if lines is not None and len(lines) < len(best) and simulate(geo.r, pat, lines) == cnt:
        best = lines
    return best


def solve(text):
    geos, geos_b = {}, {}
    progs = []
    total = 0
    for r, pat, cnt in parse(text):
        geo = geos.setdefault(r, Geo(r))
        geo_b = geos_b.setdefault(r, level6b.Geo(r))
        lines = solve_case(geo, geo_b, pat, cnt)
        total += len(lines)
        progs.append("\n".join(" ".join(l) for l in lines))
    print(f"  score (total lines): {total}", file=sys.stderr)
    return "\n\n".join(progs)
