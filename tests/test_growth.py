"""Tests for the growth phase."""

from meadow.growth import GrowthPhase
from meadow.hex import HexCell, HexGrid
from meadow.phases import PhaseName
from meadow.plant import PlantPopulation, TraitBundle
from meadow.world import TurnContext
from meadow.world_state import WorldState


class TestGrowthPhase:
    def test_name_is_growth(self):
        pop = PlantPopulation()
        grid = HexGrid(1, 1)
        assert GrowthPhase(pop, grid).name == PhaseName.GROWTH

    def test_plant_produces_cellulose(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        pop = PlantPopulation()
        home = HexCell(2, 2, 0)
        plant = pop.register(home=home)
        plant.moisture_reserve = 5.0
        plant.nutrient_reserve = 5.0
        ws.light[ws._col_idx(home.q, home.r)] = 1.0

        GrowthPhase(pop, grid).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert plant.cellulose > 0.0

    def test_photosynthesis_consumes_reserves(self):
        grid = HexGrid(3, 3)
        ws = WorldState(grid)
        pop = PlantPopulation()
        home = HexCell(1, 1, 0)
        plant = pop.register(home=home)
        plant.moisture_reserve = 2.0
        plant.nutrient_reserve = 2.0
        ws.light[ws._col_idx(home.q, home.r)] = 1.0

        before_m = plant.moisture_reserve
        before_n = plant.nutrient_reserve
        GrowthPhase(pop, grid).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert plant.moisture_reserve < before_m
        assert plant.nutrient_reserve < before_n

    def test_no_light_no_cellulose(self):
        grid = HexGrid(3, 3)
        ws = WorldState(grid)
        pop = PlantPopulation()
        home = HexCell(1, 1, 0)
        plant = pop.register(home=home)
        plant.moisture_reserve = 10.0
        plant.nutrient_reserve = 10.0

        GrowthPhase(pop, grid).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert plant.cellulose == 0.0

    def test_no_body_plant_skipped(self):
        grid = HexGrid(3, 3)
        ws = WorldState(grid)
        pop = PlantPopulation()
        pop.register()
        GrowthPhase(pop, grid).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

    def test_larger_leaf_area_produces_more(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        ws.light[:] = 1.0

        pop_small = PlantPopulation()
        small = pop_small.register(
            home=HexCell(2, 2, 0),
            traits=TraitBundle(number_of_lobes=1.0, lobe_aspect_ratio=20.0, lobe_length=5.0),
        )
        small.moisture_reserve = 50.0
        small.nutrient_reserve = 50.0

        pop_big = PlantPopulation()
        big = pop_big.register(
            home=HexCell(2, 2, 0),
            traits=TraitBundle(number_of_lobes=5.0, lobe_aspect_ratio=1.5, lobe_length=8.0),
        )
        big.moisture_reserve = 50.0
        big.nutrient_reserve = 50.0

        GrowthPhase(pop_small, grid).execute(ws, ws, TurnContext(tick=0, weather_seed=0))
        GrowthPhase(pop_big, grid).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert big.cellulose > small.cellulose

    def test_result_has_diagnostics(self):
        grid = HexGrid(3, 3)
        ws = WorldState(grid)
        pop = PlantPopulation()
        result = GrowthPhase(pop, grid).execute(ws, ws, TurnContext(tick=0, weather_seed=0))
        assert result.phase_name == "GROWTH"


class TestGrowthExecution:
    def test_root_extends_after_growth(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        ws.light[:] = 1.0
        ws.moisture[:] = 10.0
        ws.nutrients[:] = 10.0
        pop = PlantPopulation()
        plant = pop.register(home=HexCell(2, 2, 0))
        plant.moisture_reserve = 10.0
        plant.nutrient_reserve = 10.0
        plant.cellulose = 5.0

        GrowthPhase(pop, grid).execute(ws, ws, TurnContext(tick=0, weather_seed=42))

        assert len(plant.body.root_hexes) > 1

    def test_no_cellulose_no_growth(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        pop = PlantPopulation()
        plant = pop.register(home=HexCell(2, 2, 0))

        initial_cells = len(plant.body.graph.all_cells)
        GrowthPhase(pop, grid).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert len(plant.body.graph.all_cells) == initial_cells

    def test_root_grows_downward(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        ws.light[:] = 1.0
        pop = PlantPopulation()
        plant = pop.register(home=HexCell(2, 2, 0))
        plant.moisture_reserve = 10.0
        plant.nutrient_reserve = 10.0
        plant.cellulose = 10.0

        GrowthPhase(pop, grid).execute(ws, ws, TurnContext(tick=0, weather_seed=42))

        root_zs = [c.z for c in plant.body.root_hexes]
        assert min(root_zs) < 0
