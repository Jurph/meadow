"""Tests for the growth phase."""

from meadow.growth import GrowthPhase
from meadow.hex import Axial, HexGrid
from meadow.phases import PhaseName
from meadow.plant import PlantPopulation, TraitBundle
from meadow.world import TurnContext
from meadow.world_state import WorldState


class TestGrowthPhase:
    def test_name_is_growth(self):
        pop = PlantPopulation()
        assert GrowthPhase(pop).name == PhaseName.GROWTH

    def test_plant_produces_cellulose(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        pop = PlantPopulation()
        home = Axial(2, 2)
        plant = pop.register(home=home)
        plant.moisture_reserve = 5.0
        plant.nutrient_reserve = 5.0
        ws.light[ws._idx(home)] = 1.0

        GrowthPhase(pop).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert plant.cellulose > 0.0

    def test_photosynthesis_consumes_reserves(self):
        grid = HexGrid(3, 3)
        ws = WorldState(grid)
        pop = PlantPopulation()
        home = Axial(1, 1)
        plant = pop.register(home=home)
        plant.moisture_reserve = 2.0
        plant.nutrient_reserve = 2.0
        ws.light[ws._idx(home)] = 1.0

        before_m = plant.moisture_reserve
        before_n = plant.nutrient_reserve
        GrowthPhase(pop).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert plant.moisture_reserve < before_m
        assert plant.nutrient_reserve < before_n

    def test_no_light_no_cellulose(self):
        grid = HexGrid(3, 3)
        ws = WorldState(grid)
        pop = PlantPopulation()
        home = Axial(1, 1)
        plant = pop.register(home=home)
        plant.moisture_reserve = 10.0
        plant.nutrient_reserve = 10.0

        GrowthPhase(pop).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert plant.cellulose == 0.0

    def test_no_body_plant_skipped(self):
        ws = WorldState(HexGrid(3, 3))
        pop = PlantPopulation()
        pop.register()
        GrowthPhase(pop).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

    def test_larger_leaf_area_produces_more(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        ws.light[:] = 1.0

        pop_small = PlantPopulation()
        small = pop_small.register(
            home=Axial(2, 2),
            traits=TraitBundle(number_of_lobes=1.0, lobe_aspect_ratio=20.0, lobe_length=5.0),
        )
        small.moisture_reserve = 50.0
        small.nutrient_reserve = 50.0

        pop_big = PlantPopulation()
        big = pop_big.register(
            home=Axial(2, 2),
            traits=TraitBundle(number_of_lobes=5.0, lobe_aspect_ratio=1.5, lobe_length=8.0),
        )
        big.moisture_reserve = 50.0
        big.nutrient_reserve = 50.0

        GrowthPhase(pop_small).execute(ws, ws, TurnContext(tick=0, weather_seed=0))
        GrowthPhase(pop_big).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert big.cellulose > small.cellulose

    def test_result_has_diagnostics(self):
        ws = WorldState(HexGrid(3, 3))
        pop = PlantPopulation()
        result = GrowthPhase(pop).execute(ws, ws, TurnContext(tick=0, weather_seed=0))
        assert result.phase_name == "GROWTH"
