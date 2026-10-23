import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: E402,F403
from level1 import board  # noqa: E402
from level2 import DIRS  # noqa: E402


def ring(r):
    """Border positions (row, col) in clockwise order, starting at the left vertex."""
    w = 4 * r
    pts = []
    for i in range(r, 0, -1):            # upper-left edge, going up
        pts.append((i, r - i))
    for k in range(r + 1):               # top row, left -> right (row 0, starts at col r)
        pts.append((0, r + 2 * k))
    for i in range(1, r + 1):            # upper-right edge, going down
        pts.append((i, w - (r - i)))
    for i in range(r + 1, 2 * r + 1):    # lower-right edge, going down
        pts.append((i, w - (i - r)))
    for k in range(1, r + 1):            # bottom row, right -> left
        pts.append((2 * r, 3 * r - 2 * k))
    for i in range(2 * r - 1, r, -1):    # lower-left edge, going up
        pts.append((i, i - r))
    return pts


def start_index(r, emitter):
    # 1 left vertex, 2 top-left, 3 top-right, 4 right vertex, 5 bottom-right, 6 bottom-left
    return {1: 0, 2: r, 3: 2 * r, 4: 3 * r, 5: 4 * r, 6: 5 * r}[emitter]


def beam_cells(grid, r0, c0, d):
    dr, dc = DIRS[d]
    r, c = r0 + dr, c0 + dc
    while 0 <= r < len(grid) and 0 <= c < len(grid[r]) and grid[r][c] in "OM":
        yield r, c
        r, c = r + dr, c + dc


def run_program(r, program):
    grid = [list(l) for l in board(r).splitlines()]
    pts = ring(r)
    pos = [start_index(r, e) for e in range(1, 7)]
    active = [False] * 6
    for line in program:
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
    return "\n".join("".join(row) for row in grid)


def parse_programs(text):
    lines = text.splitlines()
    n = int(lines[0])
    i = 1
    progs = []
    for _ in range(n):
        while not lines[i].strip():
            i += 1
        r = int(lines[i])
        L = int(lines[i + 1])
        prog = [lines[i + 2 + j].split() for j in range(L)]
        progs.append((r, prog))
        i += 2 + L
    return progs


def solve(text):
    return "\n\n".join(run_program(r, prog) for r, prog in parse_programs(text))
