"""Tests for the weather phase."""

import pytest

from meadow.hex import HexGrid, surface
from meadow.phases import PhaseName
from meadow.weather import WeatherPhase
from meadow.world import TurnContext
from meadow.world_state import WorldState


class TestWeatherPhase:
    def test_name_is_weather(self):
        phase = WeatherPhase(rainfall_per_tick=1.0)
        assert phase.name == PhaseName.WEATHER

    def test_rainfall_adds_moisture_uniformly(self):
        grid = HexGrid(3, 3)
        ws = WorldState(grid)
        phase = WeatherPhase(rainfall_per_tick=2.5)
        ctx = TurnContext(tick=0, weather_seed=0)

        phase.execute(ws, ws, ctx)

        for col in grid:
            assert ws.moisture_at(surface(col)) == pytest.approx(2.5)

    def test_rainfall_accumulates_over_ticks(self):
        grid = HexGrid(3, 3)
        ws = WorldState(grid)
        phase = WeatherPhase(rainfall_per_tick=1.0)

        for tick in range(3):
            phase.execute(ws, ws, TurnContext(tick=tick, weather_seed=tick))

        assert ws.total_moisture() == pytest.approx(3.0 * 9)

    def test_total_moisture_increase_matches_expected(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        phase = WeatherPhase(rainfall_per_tick=0.5)

        before = ws.total_moisture()
        phase.execute(ws, ws, TurnContext(tick=0, weather_seed=0))
        after = ws.total_moisture()

        assert after - before == pytest.approx(0.5 * 25)

    def test_result_has_diagnostics(self):
        ws = WorldState(HexGrid(2, 2))
        phase = WeatherPhase(rainfall_per_tick=1.0)
        result = phase.execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert result.phase_name == "WEATHER"
        assert result.diagnostics is not None
        assert result.diagnostics["rainfall_total"] == pytest.approx(4.0)
