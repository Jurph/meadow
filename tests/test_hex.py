"""Tests for hex coordinate system and topology."""

import pytest

from meadow.hex import Axial, HexGrid, disk, distance, neighbors


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