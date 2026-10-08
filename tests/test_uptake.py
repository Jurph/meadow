"""Tests for the uptake phase."""

import pytest

from meadow.hex import HexCell, HexGrid
from meadow.phases import PhaseName
from meadow.plant import PlantPopulation, TraitBundle
from meadow.uptake import UptakePhase
from meadow.world import TurnContext
from meadow.world_state import WorldState


class TestUptakePhase:
    def test_name_is_uptake(self):
        pop = PlantPopulation()
        assert UptakePhase(pop).name == PhaseName.UPTAKE

    def test_plant_absorbs_moisture_and_nutrients(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        pop = PlantPopulation()
        home = HexCell(2, 2, 0)
        plant = pop.register(home=home, traits=TraitBundle(root_reach=0.5))
        ws.moisture[ws._col_idx(home.q, home.r)] = 10.0
        ws.nutrients[ws._col_idx(home.q, home.r)] = 6.0

        UptakePhase(pop).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert ws.moisture_at(home) == pytest.approx(5.0)
        assert ws.nutrients_at(home) == pytest.approx(3.0)
        assert plant.reserves.water == pytest.approx(5.0)
        assert plant.reserves.minerals == pytest.approx(3.0)
        assert plant.balance_sheet is not None
        assert plant.balance_sheet.root_uptake.potential.water == pytest.approx(5.0)
        assert plant.balance_sheet.root_uptake.actual.minerals == pytest.approx(3.0)

    def test_no_body_plant_skipped(self):
        ws = WorldState(HexGrid(3, 3))
        pop = PlantPopulation()
        pop.register()
        UptakePhase(pop).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

    def test_reserves_accumulate_across_ticks(self):
        grid = HexGrid(3, 3)
        ws = WorldState(grid)
        pop = PlantPopulation()
        home = HexCell(1, 1, 0)
        plant = pop.register(home=home, traits=TraitBundle(root_reach=0.5))

        for tick in range(3):
            ws.moisture[ws._col_idx(home.q, home.r)] = 4.0
            ws.nutrients[ws._col_idx(home.q, home.r)] = 2.0
            UptakePhase(pop).execute(ws, ws, TurnContext(tick=tick, weather_seed=0))

        assert plant.reserves.water == pytest.approx(6.0)
        assert plant.reserves.minerals == pytest.approx(3.0)

    def test_result_has_diagnostics(self):
        ws = WorldState(HexGrid(3, 3))
        pop = PlantPopulation()
        pop.register(home=HexCell(1, 1, 0))
        ws.moisture[:] = 5.0
        ws.nutrients[:] = 3.0
        result = UptakePhase(pop).execute(ws, ws, TurnContext(tick=0, weather_seed=0))
        assert result.phase_name == "UPTAKE"
        assert result.diagnostics is not None
