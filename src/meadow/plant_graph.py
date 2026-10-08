"""Graph representation of a plant's physical structure.

A plant body is a tree of Segments connecting HexCells. Active growth
happens at GrowthTips which extend into neighboring cells each tick.
Inspired by Swarm Grammar root models (Mußmann et al. 2024).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from math import isfinite

from meadow.hex import HexCell


class SegmentType(Enum):
    ROOT = auto()
    STEM = auto()


@dataclass
class Segment:
    """One edge in the plant graph, connecting two hex cells."""

    id: int
    parent_id: int | None
    start: HexCell
    end: HexCell
    segment_type: SegmentType
    diameter: float = 1.0
    order: int = 0
    accumulated_length: float = 1.0


@dataclass
class LeafOrgan:
    """A photosynthetic surface organ attached to a stem node."""

    id: int
    attachment_segment_id: int | None
    cell: HexCell
    area: float
    health: float = 1.0


@dataclass
class GrowthTip:
    """An active growth point at the frontier of the plant."""

    segment_id: int
    cell: HexCell
    segment_type: SegmentType
    order: int = 0
    accumulated_length: float = 0.0


class PlantGraph:
    """Tree of segments representing a plant's spatial structure."""

    def __init__(self) -> None:
        self._segments: dict[int, Segment] = {}
        self._leaves: dict[int, LeafOrgan] = {}
        self._tips: list[GrowthTip] = []
        self._next_segment_id: int = 0
        self._next_leaf_id: int = 0

    @classmethod
    def create_seed(cls, home: HexCell, *, leaf_area: float) -> PlantGraph:
        """Create a seed with root/stem tips and one crown leaf."""
        graph = cls()
        graph._tips.append(
            GrowthTip(
                segment_id=-1,
                cell=home,
                segment_type=SegmentType.ROOT,
                order=0,
                accumulated_length=0.0,
            )
        )
        graph._tips.append(
            GrowthTip(
                segment_id=-1,
                cell=home,
                segment_type=SegmentType.STEM,
                order=0,
                accumulated_length=0.0,
            )
        )
        graph.add_leaf(None, home, area=leaf_area)
        return graph

    def add_segment(
        self,
        parent_id: int | None,
        start: HexCell,
        end: HexCell,
        segment_type: SegmentType,
        diameter: float = 1.0,
        order: int = 0,
        accumulated_length: float = 1.0,
    ) -> Segment:
        seg = Segment(
            id=self._next_segment_id,
            parent_id=parent_id,
            start=start,
            end=end,
            segment_type=segment_type,
            diameter=diameter,
            order=order,
            accumulated_length=accumulated_length,
        )
        self._segments[self._next_segment_id] = seg
        self._next_segment_id += 1
        return seg

    def add_leaf(
        self,
        attachment_segment_id: int | None,
        cell: HexCell,
        *,
        area: float,
        health: float = 1.0,
    ) -> LeafOrgan:
        """Attach a leaf to the crown or the end node of a stem segment."""
        if not isfinite(area) or area < 0.0:
            raise ValueError(f"leaf area must be non-negative finite, got {area}")
        if not isfinite(health) or not 0.0 <= health <= 1.0:
            raise ValueError(f"leaf health must be between 0 and 1, got {health}")
        if attachment_segment_id is not None:
            segment = self._segments.get(attachment_segment_id)
            if segment is None:
                raise ValueError(f"unknown attachment segment {attachment_segment_id}")
            if segment.segment_type != SegmentType.STEM:
                raise ValueError("leaf organs must attach to a stem segment")
            if cell != segment.end:
                raise ValueError("leaf cell must match the attachment stem end")
        leaf = LeafOrgan(
            id=self._next_leaf_id,
            attachment_segment_id=attachment_segment_id,
            cell=cell,
            area=area,
            health=health,
        )
        self._leaves[self._next_leaf_id] = leaf
        self._next_leaf_id += 1
        return leaf

    @property
    def segments(self) -> dict[int, Segment]:
        return self._segments

    @property
    def leaves(self) -> dict[int, LeafOrgan]:
        return self._leaves

    @property
    def tips(self) -> list[GrowthTip]:
        return self._tips

    @property
    def root_cells(self) -> set[HexCell]:
        cells: set[HexCell] = set()
        for seg in self._segments.values():
            if seg.segment_type == SegmentType.ROOT:
                cells.add(seg.start)
                cells.add(seg.end)
        for tip in self._tips:
            if tip.segment_type == SegmentType.ROOT:
                cells.add(tip.cell)
        return cells

    @property
    def all_cells(self) -> set[HexCell]:
        cells: set[HexCell] = set()
        for seg in self._segments.values():
            cells.add(seg.start)
            cells.add(seg.end)
        for tip in self._tips:
            cells.add(tip.cell)
        for leaf in self._leaves.values():
            cells.add(leaf.cell)
        return cells
