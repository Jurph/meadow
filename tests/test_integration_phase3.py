"""Phase 3 integration: full tick with a real plant on a real grid.

Key invariants:
- Plant accumulates cellulose after one tick with moisture, nutrients, and light
- Resources deducted from tiles match what the plant absorbed
- Grass vs maple leaf traits produce different cellulose amounts
"""

from meadow.flow import FlowPhase
from meadow.growth import GrowthPhase
from meadow.hex import HexCell, HexGrid, surface
from meadow.light import LightPhase
from meadow.phases import NoOpPhase, PhaseName
from meadow.plant import PlantPopulation, TraitBundle
from meadow.sim import TurnPipeline
from meadow.uptake import UptakePhase
from meadow.weather import WeatherPhase
from meadow.world import TurnContext
from meadow.world_state import WorldState


def _build_phase3_pipeline(
    pop: PlantPopulation, grid: HexGrid, rainfall: float = 2.0
) -> TurnPipeline:
    return TurnPipeline({
        PhaseName.WEATHER: WeatherPhase(rainfall_per_tick=rainfall),
        PhaseName.FLOW: FlowPhase(),
        PhaseName.LIGHT: LightPhase(base_sunlight=1.0),
        PhaseName.UPTAKE: UptakePhase(pop),
        PhaseName.DEPLETION: NoOpPhase(PhaseName.DEPLETION),
        PhaseName.GROWTH: GrowthPhase(pop, grid),
    })


def _seed_uniform_nutrients(ws: WorldState, amount: float) -> None:
    """Tiles start with no nutrients; weather only adds moisture."""
    for col in ws.grid:
        ws.apply_flow_delta(surface(col), 0.0, amount)


class TestPhase3Integration:
    def test_plant_gains_cellulose_after_tick(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        _seed_uniform_nutrients(ws, 50.0)
        pop = PlantPopulation()
        plant = pop.register(home=HexCell(2, 2, 0))
        pipeline = _build_phase3_pipeline(pop, grid)

        pipeline.run_tick(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert plant.cellulose > 0.0

    def test_tile_moisture_reduced_by_uptake(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        pop = PlantPopulation()
        home = HexCell(2, 2, 0)
        pop.register(home=home, traits=TraitBundle(root_reach=0.5))
        pipeline = _build_phase3_pipeline(pop, grid, rainfall=4.0)

        pipeline.run_tick(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert ws.moisture_at(home) < 4.0

    def test_grass_vs_maple_cellulose_difference(self):
        grid = HexGrid(5, 5)

        ws_grass = WorldState(grid)
        _seed_uniform_nutrients(ws_grass, 50.0)
        pop_grass = PlantPopulation()
        grass = pop_grass.register(
            home=HexCell(2, 2, 0),
            traits=TraitBundle(
                number_of_lobes=1.0, lobe_aspect_ratio=20.0, lobe_length=15.0,
                root_reach=0.5,
            ),
        )
        pipe_grass = _build_phase3_pipeline(pop_grass, grid, rainfall=10.0)
        pipe_grass.run_tick(ws_grass, ws_grass, TurnContext(tick=0, weather_seed=0))

        ws_maple = WorldState(grid)
        _seed_uniform_nutrients(ws_maple, 50.0)
        pop_maple = PlantPopulation()
        maple = pop_maple.register(
            home=HexCell(2, 2, 0),
            traits=TraitBundle(
                number_of_lobes=5.0, lobe_aspect_ratio=1.5, lobe_length=8.0,
                root_reach=0.5,
            ),
        )
        pipe_maple = _build_phase3_pipeline(pop_maple, grid, rainfall=10.0)
        pipe_maple.run_tick(ws_maple, ws_maple, TurnContext(tick=0, weather_seed=0))

        assert maple.cellulose > grass.cellulose

    def test_five_ticks_cellulose_grows(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        _seed_uniform_nutrients(ws, 200.0)
        pop = PlantPopulation()
        plant = pop.register(home=HexCell(2, 2, 0))
        pipeline = _build_phase3_pipeline(pop, grid)

        for tick in range(5):
            pipeline.run_tick(ws, ws, TurnContext(tick=tick, weather_seed=tick))

        assert plant.cellulose > 0.0

    def test_full_tick_completes_with_6_results(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        pop = PlantPopulation()
        pop.register(home=HexCell(2, 2, 0))
        pipeline = _build_phase3_pipeline(pop, grid)
        results = pipeline.run_tick(ws, ws, TurnContext(tick=0, weather_seed=0))
        assert len(results) == 6
