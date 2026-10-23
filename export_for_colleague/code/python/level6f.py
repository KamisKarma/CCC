"""Level 6, configuration-library planner.

A configuration = which emitters are on and where they stand (positions of off emitters
don't matter). Single configurations can paint 10-25 pattern cells at once, but a
tick-by-tick search rarely reaches them. So:
  1. build a library of valid high-yield configurations by randomized hill climbing,
     plus all their on-subsets and every two-beam configuration for every pattern cell;
  2. repeatedly jump to the configuration with the best (new cells - erased cells) / ticks;
  3. transitions keep beams on while moving when the simulator says it is harmless,
     otherwise switch off, move, switch on.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from validate_level6_optimized import FIRE_DIRECTIONS, geometry, simulate  # noqa: E402


def pc(x):
    return bin(x).count("1")


def rd(a, b, n):
    d = (b - a) % n
    return min(d, n - d)


def step_to(cur, tgt, n):
    if cur == tgt:
        return "-", cur
    fwd = (tgt - cur) % n
    if fwd <= n - fwd:
        return "F", (cur + 1) % n
    return "B", (cur - 1) % n


PAR = {0: 3, 3: 0, 1: 4, 4: 1, 2: 5, 5: 2}


class Plan:
    def __init__(self, case, seed=0, restarts=250, iters=300, alpha=0.0, fast=True):
        self.case = case
        self.rng = random.Random(seed)
        self.alpha = alpha
        self.fast = fast
        cells, beams = geometry(case.radius)
        self.beams = beams
        self.n = 6 * case.radius
        self.P = sum(cells[c] for c in case.pattern)
        F = 0
        for r, c in case.pattern:
            for dr, dc in FIRE_DIRECTIONS:
                k = (r + dr, c + dc)
                if k in cells and k not in case.pattern:
                    F |= cells[k]
        self.F = F
        self.useful = [[p for p in range(self.n) if beams[d][p]] for d in range(6)]
        self.entry = [{} for _ in range(6)]
        for d in range(6):
            for p in range(self.n):
                b = beams[d][p]
                while b:
                    low = b & -b
                    self.entry[d][low] = p
                    b ^= low
        self.lib = {}
        self.build_library(restarts, iters)

    def paint(self, cfg):
        one = two = three = 0
        for d, p in cfg:
            b = self.beams[d][p]
            three |= two & b
            two |= one & b
            one |= b
        return two & ~three, three

    def add(self, cfg):
        cfg = tuple(sorted(cfg))
        if len(cfg) < 2 or cfg in self.lib:
            return
        ex2, th = self.paint(cfg)
        if ex2 & self.F or not ex2 & self.P:
            return
        self.lib[cfg] = (ex2 & self.P, th & self.P)

    def build_library(self, restarts, iters):
        rng = self.rng
        found = []
        for _ in range(restarts):
            on = [d for d in range(6) if rng.random() < 0.75]
            if len(on) < 2:
                on = rng.sample(range(6), 3)
            cfg = {d: rng.choice(self.useful[d]) for d in on}

            def f(c):
                ex2, _ = self.paint(c.items())
                if ex2 & self.F:
                    return -1
                return pc(ex2 & self.P)

            s = f(cfg)
            for _ in range(iters):
                old = dict(cfg)
                r = rng.random()
                d = rng.randrange(6)
                if r < 0.15:
                    if d in cfg and len(cfg) > 2:
                        del cfg[d]
                    elif d not in cfg:
                        cfg[d] = rng.choice(self.useful[d])
                elif d in cfg:
                    if r < 0.4:
                        cfg[d] = rng.choice(self.useful[d])
                    else:
                        cfg[d] = (cfg[d] + rng.choice((-2, -1, 1, 2))) % self.n
                ns = f(cfg)
                if ns >= s:
                    s = ns
                else:
                    cfg = old
            if s > 0:
                found.append(tuple(sorted(cfg.items())))
        for cfg in set(found):
            k = len(cfg)
            for mask in range(1, 1 << k):
                sub = [cfg[j] for j in range(k) if mask >> j & 1]
                if len(sub) >= 2:
                    self.add(sub)
        # every two-beam configuration through every pattern cell
        b = self.P
        while b:
            low = b & -b
            b ^= low
            for e1 in range(6):
                for e2 in range(e1 + 1, 6):
                    if PAR[e1] == e2:
                        continue
                    self.add([(e1, self.entry[e1][low]), (e2, self.entry[e2][low])])
        self.items = list(self.lib.items())

    # ---- transitions -------------------------------------------------------------
    def cost(self, pos, on, cfg):
        tgt = dict(cfg)
        T = 1
        for e in range(6):
            if e in tgt:
                d = rd(pos[e], tgt[e], self.n)
                if d == 0:
                    c = 0 if on[e] else 1
                elif on[e] and self.fast:
                    c = d
                else:
                    c = (1 if on[e] else 0) + d + 1
            else:
                c = 1 if on[e] else 0
            T = max(T, c)
        return T

    def schedule(self, pos, on, cfg, fast):
        """Per-tick instruction lines reaching cfg; final tick realizes the configuration."""
        tgt = dict(cfg)
        cols = []
        for e in range(6):
            col = []
            if e in tgt:
                p = pos[e]
                d = rd(p, tgt[e], self.n)
                if d == 0:
                    col = [] if on[e] else ["T"]
                elif on[e] and fast:
                    while p != tgt[e]:
                        s, p = step_to(p, tgt[e], self.n)
                        col.append(s)
                else:
                    pre = ["T"] if on[e] else []
                    mv = []
                    while p != tgt[e]:
                        s, p = step_to(p, tgt[e], self.n)
                        mv.append(s)
                    col = pre + mv + ["T"]
            else:
                col = ["T"] if on[e] else []
            cols.append(col)
        T = max(1, max(len(c) for c in cols))
        lines = []
        for t in range(T):
            row = []
            for e in range(6):
                col = cols[e]
                # turn-offs happen first, everything else is right-aligned to the final tick
                if col and col[0] == "T" and (len(col) > 1 or e not in tgt):
                    head, rest = ["T"], col[1:]
                    lead = 1
                else:
                    head, rest, lead = [], col, 0
                if t < lead:
                    row.append(head[t])
                else:
                    k = t - (T - len(rest))
                    row.append(rest[k] if 0 <= k < len(rest) else "-")
            lines.append(row)
        return lines

    def run_lines(self, pos, on, M, lines):
        pos, on = list(pos), list(on)
        done = 0
        for row in lines:
            for e, ins in enumerate(row):
                if ins == "F":
                    pos[e] = (pos[e] + 1) % self.n
                elif ins == "B":
                    pos[e] = (pos[e] - 1) % self.n
                elif ins == "T":
                    on[e] = not on[e]
            ex2, th = self.paint([(e, pos[e]) for e in range(6) if on[e]])
            if ex2 & self.F:
                return None
            M = (M | ex2) & ~th
            if M & self.P == self.P:
                M &= ~self.P
                done += 1
        return pos, on, M & (self.P | self.F), done

    # ---- main loop ---------------------------------------------------------------
    def solve(self, limit=10 ** 9):
        n = self.n
        pos = [i * self.case.radius for i in range(6)]
        on = [False] * 6
        M = 0
        done = 0
        prog = []
        while done < self.case.count:
            if len(prog) >= limit:
                return None
            todo = self.P & ~M
            best = None
            for cfg, (gain, kill) in self.items:
                new = pc(gain & todo)
                if not new:
                    continue
                net = new - pc(kill & M & self.P)
                if net <= 0:
                    continue
                T = self.cost(pos, on, cfg)
                sc = net / (T + self.alpha)
                if best is None or sc > best[0]:
                    best = (sc, cfg)
            if best is None:
                return None
            cfg = best[1]
            res = None
            for fast in ((True, False) if self.fast else (False,)):
                lines = self.schedule(pos, on, cfg, fast)
                res = self.run_lines(pos, on, M, lines)
                if res is not None:
                    break
            if res is None:
                # fall back: everything off first, then reconfigure
                off = [["T" if on[e] else "-" for e in range(6)]]
                r0 = self.run_lines(pos, on, M, off)
                if r0 is None:
                    return None
                p2, o2, M2, d2 = r0
                lines = off + self.schedule(p2, o2, cfg, False)
                res = self.run_lines(pos, on, M, lines)
                if res is None:
                    return None
            pos, on, M, d = res
            done += d
            prog.extend(lines)
        # the last submission may happen mid-schedule: trim to it
        r = simulate(self.case, prog, record_ticks=True)
        if r["accepted"] < self.case.count:
            return None
        prog = prog[:r["accepted_at"][self.case.count - 1]]
        return prog if simulate(self.case, prog)["valid"] else None
