"""Tests for the flow phase — slope-driven moisture/nutrient redistribution.

Key invariant: total moisture and nutrients are conserved (closed boundary).
"""

import numpy as np
import pytest

from meadow.flow import FlowPhase
from meadow.hex import Axial, HexGrid
from meadow.phases import PhaseName
from meadow.world import TurnContext
from meadow.world_state import WorldState


class TestFlowPhaseContract:
    def test_name_is_flow(self):
        assert FlowPhase().name == PhaseName.FLOW

    def test_result_has_diagnostics(self):
        ws = WorldState(HexGrid(3, 3))
        result = FlowPhase().execute(ws, ws, TurnContext(tick=0, weather_seed=0))
        assert result.phase_name == "FLOW"
        assert result.diagnostics is not None


class TestFlowConservation:
    """Mass conservation: total moisture/nutrients before == after."""

    def test_moisture_conserved_on_flat_terrain(self):
        ws = WorldState(HexGrid(5, 5))
        ws.moisture[::2] = 10.0
        before = ws.total_moisture()

        FlowPhase().execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert ws.total_moisture() == pytest.approx(before)

    def test_moisture_conserved_on_sloped_terrain(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        ws.moisture[:] = 5.0
        for h in grid:
            i = ws._idx(h)
            ws.slope_q[i] = 0.3
            ws.slope_r[i] = -0.1
        before = ws.total_moisture()

        FlowPhase().execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert ws.total_moisture() == pytest.approx(before)

    def test_nutrients_conserved(self):
        grid = HexGrid(4, 4)
        ws = WorldState(grid)
        ws.nutrients[:] = 2.0
        ws.moisture[:] = 5.0
        for h in grid:
            ws.slope_q[ws._idx(h)] = 0.5
        before = ws.total_nutrients()

        FlowPhase().execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert ws.total_nutrients() == pytest.approx(before)


class TestFlowBehavior:
    def test_no_flow_on_flat_terrain(self):
        ws = WorldState(HexGrid(3, 3))
        ws.moisture[:] = 5.0
        snapshot = ws.moisture.copy()

        FlowPhase().execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        np.testing.assert_array_almost_equal(ws.moisture, snapshot)

    def test_moisture_moves_downhill(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        center = Axial(2, 2)
        ci = ws._idx(center)
        ws.moisture[ci] = 100.0
        ws.slope_q[ci] = 1.0

        FlowPhase().execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert ws.moisture_at(center) < 100.0
        assert ws.moisture_at(Axial(3, 2)) > 0.0 or ws.moisture_at(Axial(3, 1)) > 0.0

    def test_no_negative_moisture(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        ws.moisture[:] = 0.1
        for h in grid:
            ws.slope_q[ws._idx(h)] = 1.0

        for _ in range(10):
            FlowPhase().execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert np.all(ws.moisture >= -1e-12)
