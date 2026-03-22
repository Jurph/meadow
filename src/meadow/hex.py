"""Hex coordinate system, topology, and footprint math.

Uses axial coordinates (q, r) with pointy-top orientation.
A rectangular grid patch maps q in [0, width) and r in [0, height).
HexCell(q, r, z) extends axial to 3D: z=0 is surface, negative is
underground, positive is aboveground.
"""

from __future__ import annotations

from typing import NamedTuple


class Axial(NamedTuple):
    """An axial hex coordinate (q, r)."""

    q: int
    r: int


class HexCell(NamedTuple):
    """A 3D hex coordinate: (q, r) horizontal + z vertical.

    z=0 is surface. Negative z is underground, positive is aboveground.
    """

    q: int
    r: int
    z: int

    @property
    def column(self) -> Axial:
        return Axial(self.q, self.r)


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


def surface(col: Axial) -> HexCell:
    """Convert a column coordinate to a surface-level cell."""
    return HexCell(col.q, col.r, 0)


def neighbors_3d(h: HexCell) -> list[HexCell]:
    """Return 6 lateral neighbors at the same z, plus one above and one below."""
    lateral = [HexCell(h.q + d.q, h.r + d.r, h.z) for d in DIRECTIONS]
    lateral.append(HexCell(h.q, h.r, h.z + 1))
    lateral.append(HexCell(h.q, h.r, h.z - 1))
    return lateral


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
    """A rectangular patch in axial space with optional vertical range."""

    def __init__(self, width: int, height: int, min_z: int = -20, max_z: int = 50) -> None:
        if width < 1 or height < 1:
            raise ValueError(f"Grid dimensions must be positive, got {width}x{height}")
        self.width = width
        self.height = height
        self.min_z = min_z
        self.max_z = max_z

    @property
    def z_levels(self) -> int:
        return self.max_z - self.min_z + 1

    def in_bounds(self, h: Axial) -> bool:
        return 0 <= h.q < self.width and 0 <= h.r < self.height

    def cell_in_bounds(self, h: HexCell) -> bool:
        return self.in_bounds(h.column) and self.min_z <= h.z <= self.max_z

    def neighbors_in_bounds(self, h: Axial) -> list[Axial]:
        return [n for n in neighbors(h) if self.in_bounds(n)]

    def __iter__(self):
        """Iterate over all columns as Axial coordinates."""
        for q in range(self.width):
            for r in range(self.height):
                yield Axial(q, r)

    def __len__(self) -> int:
        """Number of columns (not cells)."""
        return self.width * self.height
