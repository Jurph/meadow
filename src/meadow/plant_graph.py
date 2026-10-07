"""Graph representation of a plant's physical structure.

A plant body is a tree of Segments connecting HexCells. Active growth
happens at GrowthTips which extend into neighboring cells each tick.
Inspired by Swarm Grammar root models (Mußmann et al. 2024).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

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
        self._tips: list[GrowthTip] = []
        self._next_id: int = 0

    @classmethod
    def create_seed(cls, home: HexCell) -> PlantGraph:
        """Create a graph for a newly planted seed at *home*.

        Starts with one root tip pointing down and one stem tip pointing up.
        """
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
            id=self._next_id,
            parent_id=parent_id,
            start=start,
            end=end,
            segment_type=segment_type,
            diameter=diameter,
            order=order,
            accumulated_length=accumulated_length,
        )
        self._segments[self._next_id] = seg
        self._next_id += 1
        return seg

    @property
    def segments(self) -> dict[int, Segment]:
        return self._segments

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
    def leaf_cells(self) -> set[HexCell]:
        cells: set[HexCell] = set()
        for tip in self._tips:
            if tip.segment_type == SegmentType.STEM:
                cells.add(tip.cell)
        if not cells:
            for seg in self._segments.values():
                if seg.segment_type == SegmentType.STEM:
                    cells.add(seg.end)
        if not cells:
            for tip in self._tips:
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
        return cells
