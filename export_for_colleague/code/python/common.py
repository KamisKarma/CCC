"""Shared helpers for CCC levels."""
from collections import deque


def ints(line):
    return list(map(int, line.split()))


def lines_of(text):
    return [l for l in text.splitlines() if l.strip()]


DIRS4 = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
DIRS8 = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]


def bfs(start, neighbors):
    """Generic BFS. neighbors(node) -> iterable. Returns dict node -> distance."""
    dist = {start: 0}
    q = deque([start])
    while q:
        n = q.popleft()
        for m in neighbors(n):
            if m not in dist:
                dist[m] = dist[n] + 1
                q.append(m)
    return dist
