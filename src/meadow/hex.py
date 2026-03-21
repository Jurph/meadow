"""Hex coordinate system, topology, and footprint math.

Uses axial coordinates (q, r) with pointy-top orientation.
A rectangular grid patch maps q in [0, width) and r in [0, height).
"""

from __future__ import annotations

from typing import NamedTuple


class Axial(NamedTuple):
    """An axial hex coordinate (q, r)."""

    q: int
    r: int


DIRECTIONS: tuple[Axial, ...] = (
    Axial(+1, 0),
    Axial(+1, -1),
    Axial(0, -1),
    Axial(-1, 0),
    Axial(-1, +1),
    Axial(0, +1),
)


def neighbors(h: Axial) -> list[Axial]:
    """Return the six axial neighbors of *h*."""
    return [Axial(h.q + d.q, h.r + d.r) for d in DIRECTIONS]


def distance(a: Axial, b: Axial) -> int:
    """Hex distance between two axial coordinates."""
    dq = a.q - b.q
    dr = a.r - b.r
    return (abs(dq) + abs(dq + dr) + abs(dr)) // 2


def disk(center: Axial, radius: int) -> set[Axial]:
    """Return the set of hexes within *radius* steps of *center*."""
    if radius < 0:
        return set()
    results: set[Axial] = set()
    for q in range(center.q - radius, center.q + radius + 1):
        for r in range(center.r - radius, center.r + radius + 1):
            candidate = Axial(q, r)
            if distance(center, candidate) <= radius:
                results.add(candidate)
    return results


class HexGrid:
    """A rectangular patch in axial space: q in [0, width), r in [0, height)."""

    def __init__(self, width: int, height: int) -> None:
        if width < 1 or height < 1:
            raise ValueError(f"Grid dimensions must be positive, got {width}x{height}")
        self.width = width
        self.height = height

    def in_bounds(self, h: Axial) -> bool:
        return 0 <= h.q < self.width and 0 <= h.r < self.height

    def neighbors_in_bounds(self, h: Axial) -> list[Axial]:
        return [n for n in neighbors(h) if self.in_bounds(n)]

    def __iter__(self):
        for q in range(self.width):
            for r in range(self.height):
                yield Axial(q, r)

    def __len__(self) -> int:
        return self.width * self.height