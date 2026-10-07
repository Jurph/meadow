"""Phase 2 integration: full tick with real WorldState and weather/flow/light.

Key invariants tested:
- Mass conservation through a complete tick
- No negative moisture after flow
- All hexes receive light
"""

import numpy as np
import pytest

from meadow.flow import FlowPhase
from meadow.hex import HexGrid, surface
from meadow.light import LightPhase
from meadow.phases import NoOpPhase, PhaseName
from meadow.sim import TurnPipeline
from meadow.weather import WeatherPhase
from meadow.world import TurnContext
from meadow.world_state import WorldState


def _build_phase2_pipeline(rainfall: float = 1.0, sunlight: float = 1.0) -> TurnPipeline:
    return TurnPipeline(
        {
            PhaseName.WEATHER: WeatherPhase(rainfall_per_tick=rainfall),
            PhaseName.FLOW: FlowPhase(),
            PhaseName.LIGHT: LightPhase(base_sunlight=sunlight),
            PhaseName.UPTAKE: NoOpPhase(PhaseName.UPTAKE),
            PhaseName.DEPLETION: NoOpPhase(PhaseName.DEPLETION),
            PhaseName.GROWTH: NoOpPhase(PhaseName.GROWTH),
        }
    )


class TestPhase2Integration:
    def test_full_tick_completes_on_10x10(self):
        ws = WorldState(HexGrid(10, 10))
        pipeline = _build_phase2_pipeline()
        results = pipeline.run_tick(ws, ws, TurnContext(tick=0, weather_seed=0))
        assert len(results) == 6

    def test_moisture_conservation_across_tick(self):
        grid = HexGrid(8, 8)
        ws = WorldState(grid)
        for h in grid:
            ws.slope_q[ws._col_idx(h.q, h.r)] = 0.2
        pipeline = _build_phase2_pipeline(rainfall=2.0)

        expected_added = 2.0 * len(grid)
        pipeline.run_tick(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert ws.total_moisture() == pytest.approx(expected_added)

    def test_no_negative_moisture_after_tick(self):
        grid = HexGrid(6, 6)
        ws = WorldState(grid)
        for h in grid:
            ws.slope_q[ws._col_idx(h.q, h.r)] = 0.8
            ws.slope_r[ws._col_idx(h.q, h.r)] = 0.3
        pipeline = _build_phase2_pipeline(rainfall=0.1)

        for tick in range(20):
            pipeline.run_tick(ws, ws, TurnContext(tick=tick, weather_seed=tick))

        assert np.all(ws.moisture >= -1e-12)

    def test_light_set_every_tick(self):
        grid = HexGrid(4, 4)
        ws = WorldState(grid)
        pipeline = _build_phase2_pipeline(sunlight=0.9)

        pipeline.run_tick(ws, ws, TurnContext(tick=0, weather_seed=0))

        for col in grid:
            assert ws.light_at(surface(col)) == pytest.approx(0.9)

    def test_multi_tick_moisture_accumulates(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        pipeline = _build_phase2_pipeline(rainfall=1.0)

        for tick in range(5):
            pipeline.run_tick(ws, ws, TurnContext(tick=tick, weather_seed=tick))

        assert ws.total_moisture() == pytest.approx(5.0 * 25)
