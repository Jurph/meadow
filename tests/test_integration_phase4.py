"""Phase 4 integration: plant growth over multiple ticks.

Key behaviors tested:
- Root cells expand over multiple ticks
- Roots grow preferentially downward (gravitropism)
- Roots grow toward moisture (hydrotropism)
- Branching creates additional growth tips
- Full pipeline runs cleanly with growth execution
"""

from meadow.flow import FlowPhase
from meadow.growth import GrowthPhase
from meadow.hex import Axial, HexCell, HexGrid, surface
from meadow.light import LightPhase
from meadow.phases import NoOpPhase, PhaseName
from meadow.plant import PlantPopulation, TraitBundle
from meadow.plant_graph import SegmentType
from meadow.sim import TurnPipeline
from meadow.uptake import UptakePhase
from meadow.weather import WeatherPhase
from meadow.world import TurnContext
from meadow.world_state import WorldState

# Growth spends from per-pool allocation; default 0.25 root share needs cellulose >= 4
# before the root pool reaches cellulose_per_segment (1.0). Bias allocation for these tests.
_ROOT_GROWTH_ALLOC = dict(alloc_root=1.0, alloc_leaf=0.0, alloc_stem=0.0, alloc_reproduce=0.0)


def _build_phase4_pipeline(
    pop: PlantPopulation, grid: HexGrid, rainfall: float = 5.0
) -> TurnPipeline:
    return TurnPipeline(
        {
            PhaseName.WEATHER: WeatherPhase(rainfall_per_tick=rainfall),
            PhaseName.FLOW: FlowPhase(),
            PhaseName.LIGHT: LightPhase(base_sunlight=1.0),
            PhaseName.UPTAKE: UptakePhase(pop),
            PhaseName.DEPLETION: NoOpPhase(PhaseName.DEPLETION),
            PhaseName.GROWTH: GrowthPhase(pop, grid),
        }
    )


def _seed_nutrients(ws: WorldState, amount: float = 50.0):
    """Add nutrients uniformly so photosynthesis is not nutrient-limited."""
    for col in ws.grid:
        ws.apply_flow_delta(surface(col), 0.0, amount)


class TestPhase4Integration:
    def test_root_cells_expand_over_ticks(self):
        grid = HexGrid(10, 10)
        ws = WorldState(grid)
        pop = PlantPopulation()
        plant = pop.register(home=HexCell(5, 5, 0), traits=TraitBundle(**_ROOT_GROWTH_ALLOC))
        pipeline = _build_phase4_pipeline(pop, grid, rainfall=10.0)
        _seed_nutrients(ws, 100.0)

        initial_roots = len(plant.body.root_hexes)
        for tick in range(10):
            pipeline.run_tick(ws, ws, TurnContext(tick=tick, weather_seed=42))

        assert len(plant.body.root_hexes) > initial_roots

    def test_roots_grow_downward(self):
        grid = HexGrid(10, 10)
        ws = WorldState(grid)
        pop = PlantPopulation()
        traits = TraitBundle(gravitropism_weight=2.0, hydrotropism_weight=0.0, **_ROOT_GROWTH_ALLOC)
        plant = pop.register(home=HexCell(5, 5, 0), traits=traits)
        pipeline = _build_phase4_pipeline(pop, grid, rainfall=10.0)
        _seed_nutrients(ws, 100.0)

        for tick in range(10):
            pipeline.run_tick(ws, ws, TurnContext(tick=tick, weather_seed=42))

        root_zs = [c.z for c in plant.body.root_hexes]
        assert min(root_zs) < 0, "Roots should extend underground"

    def test_hydrotropism_attracts_roots(self):
        grid = HexGrid(10, 10)
        ws = WorldState(grid)
        pop = PlantPopulation()
        traits = TraitBundle(gravitropism_weight=0.0, hydrotropism_weight=2.0, **_ROOT_GROWTH_ALLOC)
        plant = pop.register(home=HexCell(5, 5, 0), traits=traits)
        _seed_nutrients(ws, 50.0)

        # Bias moisture east of home so roots can reach high moisture in one step;
        # q=7 alone is not a neighbor of (5,5), so include q=6 for a reliable gradient.
        for wet in (Axial(6, 5), Axial(7, 5)):
            ws.moisture[ws._col_idx(wet.q, wet.r)] = 500.0

        pipeline = _build_phase4_pipeline(pop, grid, rainfall=2.0)
        for tick in range(15):
            pipeline.run_tick(ws, ws, TurnContext(tick=tick, weather_seed=42))

        root_qs = [c.q for c in plant.body.root_hexes]
        assert max(root_qs) > 5, "Roots should grow toward the wet columns (q>5)"

    def test_branching_creates_lateral_tips(self):
        grid = HexGrid(10, 10)
        ws = WorldState(grid)
        pop = PlantPopulation()
        traits = TraitBundle(
            branch_probability=1.0,
            branch_spacing=1.0,
            basal_length=0.0,
            **_ROOT_GROWTH_ALLOC,
        )
        plant = pop.register(home=HexCell(5, 5, 0), traits=traits)
        # Branching pays for a lateral in the same pass as the primary segment.
        plant.cellulose = 2.0
        pipeline = _build_phase4_pipeline(pop, grid, rainfall=20.0)
        _seed_nutrients(ws, 200.0)

        for tick in range(5):
            pipeline.run_tick(ws, ws, TurnContext(tick=tick, weather_seed=42))

        root_tips = [t for t in plant.body.graph.tips if t.segment_type == SegmentType.ROOT]
        assert len(root_tips) > 1, "Branching should create additional root tips"

    def test_full_tick_completes_with_6_results(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        pop = PlantPopulation()
        pop.register(home=HexCell(2, 2, 0))
        _seed_nutrients(ws, 50.0)
        pipeline = _build_phase4_pipeline(pop, grid)
        results = pipeline.run_tick(ws, ws, TurnContext(tick=0, weather_seed=0))
        assert len(results) == 6

    def test_graph_segments_accumulate(self):
        grid = HexGrid(10, 10)
        ws = WorldState(grid)
        pop = PlantPopulation()
        plant = pop.register(home=HexCell(5, 5, 0), traits=TraitBundle(**_ROOT_GROWTH_ALLOC))
        pipeline = _build_phase4_pipeline(pop, grid, rainfall=10.0)
        _seed_nutrients(ws, 100.0)

        for tick in range(10):
            pipeline.run_tick(ws, ws, TurnContext(tick=tick, weather_seed=42))

        assert len(plant.body.graph.segments) > 0, "Graph should have segments after growth"
