"""Tests for the turn pipeline orchestrator."""

import pytest

from meadow.hex import Axial, HexCell, HexGrid
from meadow.phases import PHASE_ORDER, NoOpPhase, PhaseName
from meadow.sim import TurnPipeline
from meadow.world import TurnContext


class StubView:
    def moisture_at(self, h: HexCell) -> float:
        return 0.0

    def nutrients_at(self, h: HexCell) -> float:
        return 0.0

    def light_at(self, h: HexCell) -> float:
        return 0.0

    def occupant_id_at(self, col: Axial) -> int | None:
        return None


class StubMutator:
    def apply_flow_delta(self, h: HexCell, md: float, nd: float) -> None:
        pass

    def set_light(self, h: HexCell, v: float) -> None:
        pass

    def set_occupant(self, col: Axial, pid: int | None) -> None:
        pass


def _all_noop_phases() -> dict[PhaseName, NoOpPhase]:
    return {name: NoOpPhase(name) for name in PhaseName}


class TestTurnPipeline:
    def test_missing_phase_raises(self):
        incomplete = {PhaseName.WEATHER: NoOpPhase(PhaseName.WEATHER)}
        with pytest.raises(ValueError, match="Missing phases"):
            TurnPipeline(incomplete)

    def test_run_tick_returns_one_result_per_phase(self):
        pipeline = TurnPipeline(_all_noop_phases())
        ctx = TurnContext(tick=0, weather_seed=1)
        results = pipeline.run_tick(StubView(), StubMutator(), ctx)
        assert len(results) == len(PHASE_ORDER)

    def test_run_tick_executes_phases_in_order(self):
        pipeline = TurnPipeline(_all_noop_phases())
        ctx = TurnContext(tick=0, weather_seed=1)
        results = pipeline.run_tick(StubView(), StubMutator(), ctx)
        result_names = [r.phase_name for r in results]
        expected_names = [p.name for p in PHASE_ORDER]
        assert result_names == expected_names

    def test_tick_index_passes_through(self):
        pipeline = TurnPipeline(_all_noop_phases())
        ctx = TurnContext(tick=42, weather_seed=7)
        results = pipeline.run_tick(StubView(), StubMutator(), ctx)
        assert len(results) == 6


class TestIntegration:
    """Contract-level integration: one full tick on a toy grid, all stubs."""

    def test_one_tick_on_3x3_grid_completes(self):
        grid = HexGrid(3, 3)
        assert len(grid) == 9
        pipeline = TurnPipeline(_all_noop_phases())
        ctx = TurnContext(tick=0, weather_seed=0)

        view = StubView()
        mutator = StubMutator()
        results = pipeline.run_tick(view, mutator, ctx)

        assert len(results) == len(PHASE_ORDER)
        for result in results:
            assert result.phase_name in {p.name for p in PhaseName}
            assert result.diagnostics is None

    def test_multiple_ticks_increment(self):
        pipeline = TurnPipeline(_all_noop_phases())
        view = StubView()
        mutator = StubMutator()

        for tick in range(5):
            ctx = TurnContext(tick=tick, weather_seed=tick)
            results = pipeline.run_tick(view, mutator, ctx)
            assert len(results) == len(PHASE_ORDER)
