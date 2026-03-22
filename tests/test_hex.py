"""Tests for hex coordinate system and topology."""

import pytest

from meadow.hex import Axial, HexCell, HexGrid, disk, distance, neighbors, neighbors_3d, surface


class TestAxial:
    def test_create_and_unpack(self):
        h = Axial(3, 5)
        assert h.q == 3
        assert h.r == 5

    def test_equality(self):
        assert Axial(1, 2) == Axial(1, 2)
        assert Axial(1, 2) != Axial(2, 1)

    def test_usable_as_dict_key(self):
        d = {Axial(0, 0): "origin"}
        assert d[Axial(0, 0)] == "origin"


class TestHexCell:
    def test_create_and_unpack(self):
        c = HexCell(3, 5, -2)
        assert c.q == 3
        assert c.r == 5
        assert c.z == -2

    def test_column_property(self):
        c = HexCell(1, 2, 7)
        assert c.column == Axial(1, 2)

    def test_equality(self):
        assert HexCell(1, 2, 0) == HexCell(1, 2, 0)
        assert HexCell(1, 2, 0) != HexCell(1, 2, 1)

    def test_usable_as_dict_key(self):
        d = {HexCell(0, 0, 0): "surface"}
        assert d[HexCell(0, 0, 0)] == "surface"

    def test_surface_helper(self):
        col = Axial(4, 5)
        cell = surface(col)
        assert cell == HexCell(4, 5, 0)
        assert cell.column == col


class TestDistance:
    def test_distance_to_self_is_zero(self):
        assert distance(Axial(3, 4), Axial(3, 4)) == 0

    def test_distance_to_neighbor_is_one(self):
        origin = Axial(0, 0)
        for n in neighbors(origin):
            assert distance(origin, n) == 1

    def test_distance_symmetry(self):
        a, b = Axial(0, 0), Axial(3, -2)
        assert distance(a, b) == distance(b, a)

    def test_known_distance(self):
        assert distance(Axial(0, 0), Axial(2, -1)) == 2


class TestNeighbors:
    def test_origin_has_six_neighbors(self):
        assert len(neighbors(Axial(0, 0))) == 6

    def test_neighbors_are_all_distinct(self):
        ns = neighbors(Axial(5, 5))
        assert len(set(ns)) == 6

    def test_neighbors_are_distance_one(self):
        center = Axial(3, 3)
        for n in neighbors(center):
            assert distance(center, n) == 1


class TestNeighbors3D:
    def test_returns_eight_neighbors(self):
        c = HexCell(2, 2, 0)
        ns = neighbors_3d(c)
        assert len(ns) == 8

    def test_includes_above_and_below(self):
        c = HexCell(2, 2, 5)
        ns = neighbors_3d(c)
        assert HexCell(2, 2, 6) in ns
        assert HexCell(2, 2, 4) in ns

    def test_lateral_neighbors_share_z(self):
        c = HexCell(3, 3, -1)
        ns = neighbors_3d(c)
        lateral = [n for n in ns if n.z == c.z]
        assert len(lateral) == 6


class TestDisk:
    def test_disk_radius_zero_is_single_hex(self):
        assert disk(Axial(5, 5), 0) == {Axial(5, 5)}

    def test_disk_radius_one_has_seven_hexes(self):
        assert len(disk(Axial(0, 0), 1)) == 7

    def test_disk_radius_two_has_nineteen_hexes(self):
        assert len(disk(Axial(0, 0), 2)) == 19

    def test_disk_negative_radius_is_empty(self):
        assert disk(Axial(0, 0), -1) == set()


class TestHexGrid:
    def test_grid_size(self):
        g = HexGrid(10, 10)
        assert len(g) == 100

    def test_in_bounds(self):
        g = HexGrid(5, 5)
        assert g.in_bounds(Axial(0, 0))
        assert g.in_bounds(Axial(4, 4))
        assert not g.in_bounds(Axial(-1, 0))
        assert not g.in_bounds(Axial(5, 0))

    def test_cell_in_bounds(self):
        g = HexGrid(5, 5, min_z=-10, max_z=10)
        assert g.cell_in_bounds(HexCell(0, 0, 0))
        assert g.cell_in_bounds(HexCell(4, 4, 10))
        assert g.cell_in_bounds(HexCell(2, 2, -10))
        assert not g.cell_in_bounds(HexCell(5, 0, 0))
        assert not g.cell_in_bounds(HexCell(0, 0, 11))
        assert not g.cell_in_bounds(HexCell(0, 0, -11))

    def test_z_levels(self):
        g = HexGrid(3, 3, min_z=-20, max_z=50)
        assert g.z_levels == 71

    def test_iteration_yields_all_coords(self):
        g = HexGrid(3, 3)
        coords = list(g)
        assert len(coords) == 9
        assert Axial(0, 0) in coords
        assert Axial(2, 2) in coords

    def test_neighbors_in_bounds_filters_edges(self):
        g = HexGrid(5, 5)
        corner_neighbors = g.neighbors_in_bounds(Axial(0, 0))
        assert all(g.in_bounds(n) for n in corner_neighbors)
        assert len(corner_neighbors) < 6

    def test_invalid_dimensions_rejected(self):
        with pytest.raises(ValueError):
            HexGrid(0, 5)
        with pytest.raises(ValueError):
            HexGrid(5, -1)
