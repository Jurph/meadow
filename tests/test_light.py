"""Tests for the light phase."""

import pytest

from meadow.hex import HexGrid, surface
from meadow.light import LightPhase
from meadow.phases import PhaseName
from meadow.world import TurnContext
from meadow.world_state import WorldState


class TestLightPhase:
    def test_name_is_light(self):
        assert LightPhase().name == PhaseName.LIGHT

    def test_uniform_sunlight(self):
        grid = HexGrid(4, 4)
        ws = WorldState(grid)
        LightPhase(base_sunlight=1.0).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        for col in grid:
            assert ws.light_at(surface(col)) == pytest.approx(1.0)

    def test_configurable_intensity(self):
        grid = HexGrid(3, 3)
        ws = WorldState(grid)
        LightPhase(base_sunlight=0.6).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        for col in grid:
            assert ws.light_at(surface(col)) == pytest.approx(0.6)

    def test_result_has_diagnostics(self):
        ws = WorldState(HexGrid(2, 2))
        result = LightPhase().execute(ws, ws, TurnContext(tick=0, weather_seed=0))
        assert result.phase_name == "LIGHT"
