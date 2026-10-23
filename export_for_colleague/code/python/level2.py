import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: E402,F403

# emitter digit -> (drow, dcol) in the character grid
DIRS = {"1": (0, 2), "2": (1, 1), "3": (1, -1), "4": (0, -2), "5": (-1, -1), "6": (-1, 1)}


def parse_boards(text):
    lines = text.splitlines()
    n = int(lines[0])
    i = 1
    boards = []
    for _ in range(n):
        while not lines[i].strip():
            i += 1
        r, h, w = ints(lines[i])
        grid = [list(l.strip()) for l in lines[i + 1:i + 1 + h]]
        boards.append((r, grid))
        i += 1 + h
    return boards


def fire(grid, r0, c0, d):
    dr, dc = DIRS[d]
    r, c = r0 + dr, c0 + dc
    while 0 <= r < len(grid) and 0 <= c < len(grid[r]) and grid[r][c] in "OM":
        grid[r][c] = "M"
        r, c = r + dr, c + dc


def solve(text):
    out = []
    for _, grid in parse_boards(text):
        for r, row in enumerate(grid):
            for c, ch in enumerate(row):
                if ch in DIRS:
                    fire(grid, r, c, ch)
        out.append("\n".join("".join(row) for row in grid))
    return "\n\n".join(out)
