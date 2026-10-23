import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: E402,F403
from level2 import DIRS, parse_boards  # noqa: E402


def beam_cells(grid, r0, c0, d):
    dr, dc = DIRS[d]
    r, c = r0 + dr, c0 + dc
    while 0 <= r < len(grid) and 0 <= c < len(grid[r]) and grid[r][c] in "OM":
        yield r, c
        r, c = r + dr, c + dc


def apply_beams(grid):
    hits = Counter()
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if ch in DIRS:
                hits.update(beam_cells(grid, r, c, ch))
    for (r, c), k in hits.items():
        if k == 2:
            grid[r][c] = "M"
        elif k >= 3:
            grid[r][c] = "O"


def solve(text):
    out = []
    for _, grid in parse_boards(text):
        apply_beams(grid)
        out.append("\n".join("".join(row) for row in grid))
    return "\n\n".join(out)
