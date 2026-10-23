"""Level 6, exhaustive-per-tick beam search (numpy).

Every tick, all 4^6 instruction combos are scored for each beam state:
  value = 1000 * progress - distance potential + small bonus for active emitters
where progress = submitted * |pattern| + painted pattern cells. Combos that would put
matter on a non-pattern cell adjacent to the pattern are rejected. The best W children
survive. If progress stalls, a forced two-emitter move paints the nearest open cell.
"""
import itertools
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: E402,F403
from level1 import board  # noqa: E402
from level4 import beam_cells, ring, start_index  # noqa: E402

NEIGH = [(0, 2), (0, -2), (1, 1), (1, -1), (-1, 1), (-1, -1)]
CH = "-FBT"
COMBOS = np.array(list(itertools.product(range(4), repeat=6)), dtype=np.int64)
MOV = np.array([0, 1, -1, 0])[COMBOS]
TOG = np.array([False, False, False, True])[COMBOS]
PID = ((MOV + 1) * (3 ** np.arange(6))).sum(1)
POSMOV = np.array([[(p // 3 ** e) % 3 - 1 for e in range(6)] for p in range(729)])
_PAIRS = [(a, b) for a in range(6) for b in range(a + 1, 6) if b - a != 3]


class Geo:
    def __init__(self, r):
        self.r = r
        grid = [list(l) for l in board(r).splitlines()]
        self.cells = [(a, b) for a, row in enumerate(grid) for b, ch in enumerate(row) if ch == "O"]
        self.idx = {c: i for i, c in enumerate(self.cells)}
        self.C = len(self.cells)
        self.pts = ring(r)
        self.n = len(self.pts)
        self.beam = np.zeros((6, self.n, self.C), dtype=np.int8)
        self.entry = np.zeros((6, self.C), dtype=np.int64)
        for d in range(6):
            for k, (rr, cc) in enumerate(self.pts):
                for cell in beam_cells(grid, rr, cc, str(d + 1)):
                    self.beam[d, k, self.idx[cell]] = 1
                    self.entry[d, self.idx[cell]] = k
        self.words = (self.C + 63) // 64
        self.beamb = np.stack([pack2(self.beam[d].astype(bool), self.words) for d in range(6)])

    def pack(self, arr):
        return pack2(arr[None, :], self.words)[0]

    def unpack(self, w):
        return np.unpackbits(w.view(np.uint8), bitorder="little")[:self.C].astype(bool)


POP8 = np.array([bin(i).count("1") for i in range(256)], np.int32)
ZERO = np.uint64(0)


def pack2(arr, words):
    """(rows, C) bool -> (rows, words) uint64, little-endian bit order."""
    b = np.packbits(arr, axis=1, bitorder="little")
    out = np.zeros((arr.shape[0], words * 8), np.uint8)
    out[:, :b.shape[1]] = b
    return out.view(np.uint64)


def rd(a, b, n):
    d = (b - a) % n
    return min(d, n - d)


def mv(cur, tgt, n):
    if cur == tgt:
        return "-"
    fwd = (tgt - cur) % n
    return "F" if fwd <= n - fwd else "B"


class Planner:
    def __init__(self, geo, pat, cnt, W=1, stall_th=2, w_min=10.0, w_mean=1.0, seed=None, topk=None,
                 w_cov=0.0, w_on=0.1, w_prog=1000.0, pot_sum=False, cap=0, w_far=0.0):
        self.cap = cap
        self.w_far = w_far
        self.w_prog = w_prog
        self.pot_sum = pot_sum
        self.g = geo
        self.w_cov = w_cov
        self.w_on = w_on
        self.cnt = cnt
        self.W = W
        self.topk = topk or W
        self.stall_th = stall_th
        self.w_min = w_min
        self.w_mean = w_mean
        self.rng = np.random.default_rng(seed) if seed is not None else None
        C = geo.C
        self.P = np.zeros(C, bool)
        for c in pat:
            self.P[geo.idx[c]] = True
        self.Ps = int(self.P.sum())
        forb = np.zeros(C, bool)
        for (a, b) in pat:
            for da, db in NEIGH:
                c = (a + da, b + db)
                if c in geo.idx:
                    forb[geo.idx[c]] = True
        self.forb = forb & ~self.P
        self.Pb = geo.pack(self.P)
        self.Fb = geo.pack(self.forb)

    def potential(self, pos, M):
        g = self.g
        todo = np.nonzero(self.P & ~M)[0]
        if len(todo) == 0:
            return np.zeros(729)
        ent = g.entry[:, todo]
        npos = (pos[None, :] + POSMOV) % g.n
        dd = np.abs(ent[None, :, :] - npos[:, :, None]) % g.n
        dd = np.minimum(dd, g.n - dd)
        sec = None
        for a, b in _PAIRS:
            m = np.maximum(dd[:, a], dd[:, b])
            sec = m if sec is None else np.minimum(sec, m)
        return self.w_min * sec.min(1) + self.w_mean * (sec.sum(1) if self.pot_sum else sec.mean(1)) + self.w_far * sec.max(1)

    def expand(self, st):
        g = self.g
        pos, on, M, done = st["pos"], st["on"], st["M"], st["done"]
        npos = (pos[None, :] + MOV) % g.n
        non = on[None, :] ^ TOG
        K = len(COMBOS)
        ones = np.zeros((K, g.words), np.uint64)
        twos = np.zeros((K, g.words), np.uint64)
        threes = np.zeros((K, g.words), np.uint64)
        for e in range(6):
            b = np.where(non[:, e, None], g.beamb[e][npos[:, e]], ZERO)
            threes |= twos & b
            twos |= ones & b
            ones |= b
        Mb = g.pack(M)
        newM = (Mb[None, :] | (twos & ~threes)) & ~threes
        valid = ~((newM & self.Fb[None, :]) != 0).any(1)
        painted = POP8[np.ascontiguousarray(newM & self.Pb[None, :]).view(np.uint8)].sum(1)
        complete = painted == self.Ps
        progress = np.where(complete, (done + 1) * self.Ps, done * self.Ps + painted)
        pot = self.potential(pos, M)[PID]
        val = progress * self.w_prog - pot + self.w_on * non.sum(1)
        if self.w_cov:
            # formation value: what all six beams would paint at each reachable position combo
            np729 = (pos[None, :] + POSMOV) % g.n
            o = np.zeros((729, g.words), np.uint64)
            tw = np.zeros((729, g.words), np.uint64)
            th = np.zeros((729, g.words), np.uint64)
            for e in range(6):
                b = g.beamb[e][np729[:, e]]
                th |= tw & b
                tw |= o & b
                o |= b
            ex2 = tw & ~th
            todo_b = self.Pb & ~Mb
            done_b = self.Pb & Mb
            pc = lambda x: POP8[np.ascontiguousarray(x).view(np.uint8)].sum(1)  # noqa: E731
            cov = pc(ex2 & todo_b[None, :]) - 2 * pc(ex2 & self.Fb[None, :]) - pc(th & done_b[None, :])
            val = val + self.w_cov * cov[PID]
        if self.rng is not None:
            val = val + self.rng.random(len(val)) * 0.5
        val[~valid] = -np.inf
        k = min(self.topk, int(valid.sum()))
        if k <= 0:
            return []
        top = np.argpartition(-val, k - 1)[:k]
        kids = []
        for ci in top:
            m = g.unpack(newM[ci].copy())
            d = done
            if complete[ci]:
                m = m & ~self.P
                d = done + 1
            kids.append(dict(pos=npos[ci].copy(), on=non[ci].copy(), M=m.copy(), done=d,
                             prog=int(progress[ci]), val=float(val[ci]),
                             node=(st["node"], tuple(CH[x] for x in COMBOS[ci])), t=st["t"] + 1))
        return kids

    def apply(self, st, ins):
        g = self.g
        pos = st["pos"].copy()
        on = st["on"].copy()
        for e, o in enumerate(ins):
            if o == "F":
                pos[e] = (pos[e] + 1) % g.n
            elif o == "B":
                pos[e] = (pos[e] - 1) % g.n
            elif o == "T":
                on[e] = not on[e]
        cnt = np.zeros(g.C, np.int8)
        for e in range(6):
            if on[e]:
                cnt += g.beam[e][pos[e]]
        M = (st["M"] | (cnt == 2)) & ~(cnt >= 3)
        if (M & self.forb).any():
            return None
        done = st["done"]
        if (M & self.P).sum() == self.Ps:
            M = M & ~self.P
            done += 1
        painted = int((M & self.P).sum())
        return dict(pos=pos, on=on, M=M, done=done, prog=done * self.Ps + painted, val=0.0,
                    node=(st["node"], tuple(ins)), t=st["t"] + 1)

    def forced(self, st):
        g = self.g
        todo = np.nonzero(self.P & ~st["M"])[0]
        best = None
        for c in todo:
            for e1, e2 in _PAIRS:
                cost = max(rd(st["pos"][e1], g.entry[e1, c], g.n), rd(st["pos"][e2], g.entry[e2, c], g.n))
                if best is None or cost < best[0]:
                    best = (cost, c, e1, e2)
        _, c, e1, e2 = best
        start_prog = st["prog"]
        while True:
            t1, t2 = g.entry[e1, c], g.entry[e2, c]
            ready = st["pos"][e1] == t1 and st["pos"][e2] == t2
            ins = ["-"] * 6
            for e in range(6):
                if e in (e1, e2):
                    t = g.entry[e, c]
                    if st["pos"][e] != t:
                        ins[e] = "T" if st["on"][e] else mv(st["pos"][e], t, g.n)
                    elif ready and not st["on"][e]:
                        ins[e] = "T"
                elif st["on"][e]:
                    ins[e] = "T"
            st = self.apply(st, ins)
            if st is None:
                return None
            if st["prog"] > start_prog:
                return st

    def run(self, max_ticks):
        g = self.g
        pos = np.array([start_index(g.r, e) for e in range(1, 7)], dtype=np.int64)
        st = dict(pos=pos, on=np.zeros(6, bool), M=np.zeros(g.C, bool), done=0, prog=0, val=0.0,
                  node=None, t=0)
        beam = [st]
        best_prog, stall = 0, 0
        target = self.cnt * self.Ps
        while True:
            fin = [s for s in beam if s["done"] >= self.cnt]
            if fin:
                return self.lines(min(fin, key=lambda s: s["t"]))
            if beam[0]["t"] >= max_ticks:
                return None
            if stall >= self.stall_th:
                top = max(beam, key=lambda s: (s["prog"], s["val"]))
                ns = self.forced(top)
                if ns is None:
                    return None
                beam = [ns]
                best_prog, stall = ns["prog"], 0
                continue
            kids = []
            for s in beam:
                kids.extend(self.expand(s))
            if not kids:
                stall = self.stall_th
                continue
            kids.sort(key=lambda s: -s["val"])
            seen, nb, per_m = set(), [], {}
            for k in kids:
                key = (k["pos"].tobytes(), k["on"].tobytes(), k["M"].tobytes(), k["done"])
                if key in seen:
                    continue
                seen.add(key)
                if self.cap:
                    mk = (k["M"].tobytes(), k["done"])
                    if per_m.get(mk, 0) >= self.cap:
                        continue
                    per_m[mk] = per_m.get(mk, 0) + 1
                nb.append(k)
                if len(nb) >= self.W:
                    break
            beam = nb
            bp = max(s["prog"] for s in beam)
            if bp > best_prog:
                best_prog, stall = bp, 0
            else:
                stall += 1
            if best_prog >= target:
                stall = 0

    @staticmethod
    def lines(st):
        out = []
        node = st["node"]
        while node is not None:
            node, ins = node
            out.append(list(ins))
        out.reverse()
        return out
