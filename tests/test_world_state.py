"""Tests for the numpy-backed WorldState."""

import pytest

from meadow.hex import Axial, HexGrid
from meadow.world import WorldMutator, WorldView
from meadow.world_state import WorldState


class TestWorldStateProtocols:
    def test_satisfies_world_view(self):
        ws = WorldState(HexGrid(3, 3))
        assert isinstance(ws, WorldView)

    def test_satisfies_world_mutator(self):
        ws = WorldState(HexGrid(3, 3))
        assert isinstance(ws, WorldMutator)


class TestWorldStateReadWrite:
    def test_moisture_round_trip(self):
        ws = WorldState(HexGrid(5, 5))
        h = Axial(2, 3)
        ws.apply_flow_delta(h, moisture_delta=1.5, nutrient_delta=0.0)
        assert ws.moisture_at(h) == pytest.approx(1.5)

    def test_nutrients_round_trip(self):
        ws = WorldState(HexGrid(5, 5))
        h = Axial(1, 1)
        ws.apply_flow_delta(h, moisture_delta=0.0, nutrient_delta=3.7)
        assert ws.nutrients_at(h) == pytest.approx(3.7)

    def test_light_round_trip(self):
        ws = WorldState(HexGrid(5, 5))
        h = Axial(0, 0)
        ws.set_light(h, 0.85)
        assert ws.light_at(h) == pytest.approx(0.85)

    def test_occupant_default_is_none(self):
        ws = WorldState(HexGrid(3, 3))
        assert ws.occupant_id_at(Axial(1, 1)) is None

    def test_occupant_set_and_clear(self):
        ws = WorldState(HexGrid(3, 3))
        h = Axial(1, 1)
        ws.set_occupant(h, 42)
        assert ws.occupant_id_at(h) == 42
        ws.set_occupant(h, None)
        assert ws.occupant_id_at(h) is None

    def test_initial_fields_are_zero(self):
        ws = WorldState(HexGrid(4, 4))
        for h in ws.grid:
            assert ws.moisture_at(h) == 0.0
            assert ws.nutrients_at(h) == 0.0
            assert ws.light_at(h) == 0.0

    def test_flow_delta_accumulates(self):
        ws = WorldState(HexGrid(3, 3))
        h = Axial(1, 1)
        ws.apply_flow_delta(h, 2.0, 1.0)
        ws.apply_flow_delta(h, 3.0, 0.5)
        assert ws.moisture_at(h) == pytest.approx(5.0)
        assert ws.nutrients_at(h) == pytest.approx(1.5)


class TestWorldStateArrayAccess:
    def test_total_moisture_property(self):
        ws = WorldState(HexGrid(3, 3))
        ws.apply_flow_delta(Axial(0, 0), 10.0, 0.0)
        ws.apply_flow_delta(Axial(1, 1), 5.0, 0.0)
        assert ws.total_moisture() == pytest.approx(15.0)

    def test_total_nutrients_property(self):
        ws = WorldState(HexGrid(3, 3))
        ws.apply_flow_delta(Axial(0, 0), 0.0, 7.0)
        assert ws.total_nutrients() == pytest.approx(7.0)
