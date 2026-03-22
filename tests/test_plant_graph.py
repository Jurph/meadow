"""Tests for PlantGraph and Segment types."""

from meadow.hex import HexCell
from meadow.plant_graph import PlantGraph, SegmentType


class TestPlantGraphSeed:
    def test_create_seed_has_root_and_stem_tips(self):
        g = PlantGraph.create_seed(HexCell(5, 5, 0))
        root_tips = [t for t in g.tips if t.segment_type == SegmentType.ROOT]
        stem_tips = [t for t in g.tips if t.segment_type == SegmentType.STEM]
        assert len(root_tips) == 1
        assert len(stem_tips) == 1

    def test_seed_tips_at_home(self):
        home = HexCell(3, 3, 0)
        g = PlantGraph.create_seed(home)
        assert all(t.cell == home for t in g.tips)

    def test_seed_has_no_segments(self):
        g = PlantGraph.create_seed(HexCell(0, 0, 0))
        assert len(g.segments) == 0


class TestAddSegment:
    def test_segment_gets_unique_id(self):
        g = PlantGraph()
        s1 = g.add_segment(None, HexCell(0, 0, 0), HexCell(0, 0, -1), SegmentType.ROOT)
        s2 = g.add_segment(s1.id, HexCell(0, 0, -1), HexCell(0, 0, -2), SegmentType.ROOT)
        assert s1.id != s2.id

    def test_segment_stored(self):
        g = PlantGraph()
        s = g.add_segment(None, HexCell(0, 0, 0), HexCell(0, 0, -1), SegmentType.ROOT)
        assert s.id in g.segments


class TestCellProperties:
    def test_root_cells_from_root_segments(self):
        g = PlantGraph()
        g.add_segment(None, HexCell(5, 5, 0), HexCell(5, 5, -1), SegmentType.ROOT)
        assert HexCell(5, 5, 0) in g.root_cells
        assert HexCell(5, 5, -1) in g.root_cells

    def test_root_cells_includes_root_tips(self):
        g = PlantGraph.create_seed(HexCell(2, 2, 0))
        assert HexCell(2, 2, 0) in g.root_cells

    def test_stem_segments_not_in_root_cells(self):
        g = PlantGraph()
        g.add_segment(None, HexCell(0, 0, 0), HexCell(0, 0, 1), SegmentType.STEM)
        assert len(g.root_cells) == 0

    def test_leaf_cells_from_stem_tips(self):
        g = PlantGraph.create_seed(HexCell(1, 1, 0))
        assert HexCell(1, 1, 0) in g.leaf_cells

    def test_all_cells_union(self):
        g = PlantGraph()
        g.add_segment(None, HexCell(0, 0, 0), HexCell(0, 0, -1), SegmentType.ROOT)
        g.add_segment(None, HexCell(0, 0, 0), HexCell(0, 0, 1), SegmentType.STEM)
        assert len(g.all_cells) == 3
