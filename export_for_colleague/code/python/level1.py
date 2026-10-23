import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: E402,F403


def board(r):
    rows = []
    for i in range(2 * r + 1):
        d = abs(r - i)
        n = 2 * r + 1 - d
        if i in (0, 2 * r):
            cells = ["*"] * n
        else:
            cells = ["*"] + ["O"] * (n - 2) + ["*"]
        rows.append("-" * d + "-".join(cells) + "-" * d)
    return "\n".join(rows)


def solve(text):
    nums = ints(text)
    return "\n\n".join(board(r) for r in nums[1:1 + nums[0]])
