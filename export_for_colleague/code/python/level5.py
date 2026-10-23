import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: E402,F403
from level1 import board  # noqa: E402
from level4 import beam_cells, ring, start_index  # noqa: E402

NEIGH = [(0, 2), (0, -2), (1, 1), (1, -1), (-1, 1), (-1, -1)]


def step(grid, pts, pos, active, line):
    for e, ins in enumerate(line):
        if ins == "F":
            pos[e] = (pos[e] + 1) % len(pts)
        elif ins == "B":
            pos[e] = (pos[e] - 1) % len(pts)
        elif ins == "T":
            active[e] = not active[e]
    hits = Counter()
    for e in range(6):
        if active[e]:
            rr, cc = pts[pos[e]]
            hits.update(beam_cells(grid, rr, cc, str(e + 1)))
    for (rr, cc), k in hits.items():
        if k == 2:
            grid[rr][cc] = "M"
        elif k >= 3:
            grid[rr][cc] = "O"


def pattern_ready(grid, pat):
    for r, c in pat:
        if grid[r][c] != "M":
            return False
    for r, c in pat:
        for dr, dc in NEIGH:
            rr, cc = r + dr, c + dc
            if (rr, cc) not in pat and 0 <= rr < len(grid) and 0 <= cc < len(grid[rr]) and grid[rr][cc] == "M":
                return False
    return True


def simulate(r, pat, program):
    grid = [list(l) for l in board(r).splitlines()]
    pts = ring(r)
    pos = [start_index(r, e) for e in range(1, 7)]
    active = [False] * 6
    count = 0
    for line in program:
        step(grid, pts, pos, active, line)
        if pattern_ready(grid, pat):
            for rr, cc in pat:
                grid[rr][cc] = "O"
            count += 1
    return count


def parse(text):
    lines = text.splitlines()
    n = int(lines[0])
    i = 1
    cases = []
    for _ in range(n):
        while not lines[i].strip():
            i += 1
        r, h, w = ints(lines[i])
        pgrid = lines[i + 1:i + 1 + h]
        pat = {(a, b) for a, row in enumerate(pgrid) for b, ch in enumerate(row.strip()) if ch == "M"}
        i += 1 + h
        L = int(lines[i])
        prog = [lines[i + 1 + j].split() for j in range(L)]
        i += 1 + L
        cases.append((r, pat, prog))
    return cases


def solve(text):
    return "\n".join(str(simulate(r, pat, prog)) for r, pat, prog in parse(text))
