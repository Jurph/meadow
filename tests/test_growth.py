"""Behavior tests for photosynthesis and organ construction."""

from meadow.growth import GrowthPhase
from meadow.hex import HexCell, HexGrid
from meadow.phases import PhaseName
from meadow.plant import PlantPopulation, TraitBundle
from meadow.resources import ResourceVector
from meadow.world import TurnContext
from meadow.world_state import WorldState


def _seed_reserves(
    plant,
    *,
    water: float,
    minerals: float,
    assimilate: float,
) -> None:
    plant.reserves.credit(
        ResourceVector(
            water=water,
            minerals=minerals,
            assimilate=assimilate,
        )
    )


class TestGrowthPhase:
    def test_name_is_growth(self):
        assert GrowthPhase(PlantPopulation(), HexGrid(1, 1)).name == PhaseName.GROWTH

    def test_explicit_leaf_produces_assimilate(self):
        grid = HexGrid(5, 5)
        world = WorldState(grid)
        population = PlantPopulation()
        home = HexCell(2, 2, 0)
        plant = population.register(home=home)
        _seed_reserves(plant, water=5.0, minerals=5.0, assimilate=0.0)
        world.light[world._col_idx(home.q, home.r)] = 1.0

        GrowthPhase(population, grid).execute(
            world,
            world,
            TurnContext(tick=0, weather_seed=0),
        )

        assert plant.reserves.assimilate > 0.0

    def test_photosynthesis_consumes_water_but_not_minerals(self):
        grid = HexGrid(3, 3)
        world = WorldState(grid)
        population = PlantPopulation()
        home = HexCell(1, 1, 0)
        plant = population.register(home=home)
        _seed_reserves(plant, water=2.0, minerals=2.0, assimilate=0.0)
        world.light[world._col_idx(home.q, home.r)] = 1.0

        GrowthPhase(population, grid).execute(
            world,
            world,
            TurnContext(tick=0, weather_seed=0),
        )

        assert plant.reserves.water < 2.0
        assert plant.reserves.minerals == 2.0

    def test_no_light_produces_no_assimilate(self):
        grid = HexGrid(3, 3)
        world = WorldState(grid)
        population = PlantPopulation()
        plant = population.register(home=HexCell(1, 1, 0))
        _seed_reserves(plant, water=10.0, minerals=10.0, assimilate=0.0)

        GrowthPhase(population, grid).execute(
            world,
            world,
            TurnContext(tick=0, weather_seed=0),
        )

        assert plant.reserves.assimilate == 0.0
        assert plant.balance_sheet is not None
        assert plant.balance_sheet.photosynthesis.limiting_factors == {"light"}

    def test_zero_active_leaf_area_is_reported_as_the_limiter(self):
        grid = HexGrid(3, 3)
        world = WorldState(grid)
        world.light[:] = 1.0
        population = PlantPopulation()
        plant = population.register(
            home=HexCell(1, 1, 0),
            traits=TraitBundle(number_of_lobes=0.0),
        )
        _seed_reserves(plant, water=10.0, minerals=10.0, assimilate=0.0)

        GrowthPhase(population, grid).execute(
            world,
            world,
            TurnContext(tick=0, weather_seed=0),
        )

        assert plant.balance_sheet is not None
        assert plant.balance_sheet.photosynthesis.limiting_factors == {"leaf_area"}

    def test_bodyless_plant_closes_an_unchanged_balance_sheet(self):
        grid = HexGrid(3, 3)
        world = WorldState(grid)
        population = PlantPopulation()
        plant = population.register()

        GrowthPhase(population, grid).execute(
            world,
            world,
            TurnContext(tick=0, weather_seed=0),
        )

        assert plant.balance_sheet is not None
        assert plant.balance_sheet.closed
        assert plant.balance_sheet.opening == plant.balance_sheet.closing

    def test_larger_explicit_leaf_area_produces_more(self):
        grid = HexGrid(5, 5)
        world = WorldState(grid)
        world.light[:] = 1.0

        small_population = PlantPopulation()
        small = small_population.register(
            home=HexCell(2, 2, 0),
            traits=TraitBundle(
                number_of_lobes=1.0,
                lobe_aspect_ratio=20.0,
                lobe_length=5.0,
            ),
        )
        _seed_reserves(small, water=50.0, minerals=50.0, assimilate=0.0)

        big_population = PlantPopulation()
        big = big_population.register(
            home=HexCell(2, 2, 0),
            traits=TraitBundle(
                number_of_lobes=5.0,
                lobe_aspect_ratio=1.5,
                lobe_length=8.0,
            ),
        )
        _seed_reserves(big, water=50.0, minerals=50.0, assimilate=0.0)

        GrowthPhase(small_population, grid).execute(
            world,
            world,
            TurnContext(tick=0, weather_seed=0),
        )
        GrowthPhase(big_population, grid).execute(
            world,
            world,
            TurnContext(tick=0, weather_seed=0),
        )

        assert big.reserves.assimilate > small.reserves.assimilate

    def test_result_and_balance_sheet_expose_actual_fluxes(self):
        grid = HexGrid(3, 3)
        world = WorldState(grid)
        world.light[:] = 1.0
        population = PlantPopulation()
        plant = population.register(home=HexCell(1, 1, 0))
        _seed_reserves(plant, water=2.0, minerals=2.0, assimilate=0.0)

        result = GrowthPhase(population, grid).execute(
            world,
            world,
            TurnContext(tick=0, weather_seed=0),
        )

        assert result.phase_name == "GROWTH"
        assert result.diagnostics is not None
        assert result.diagnostics["assimilate_produced"] > 0.0
        assert plant.balance_sheet is not None
        assert plant.balance_sheet.closed
        assert plant.balance_sheet.photosynthesis.actual.assimilate > 0.0


class TestOrganConstruction:
    def test_root_extends_after_paying_full_cost(self):
        grid = HexGrid(5, 5)
        world = WorldState(grid)
        population = PlantPopulation()
        plant = population.register(
            home=HexCell(2, 2, 0),
            traits=TraitBundle(
                alloc_root=1.0,
                alloc_leaf=0.0,
                alloc_stem=0.0,
                alloc_reproduce=0.0,
            ),
        )
        _seed_reserves(plant, water=10.0, minerals=10.0, assimilate=5.0)

        GrowthPhase(population, grid).execute(
            world,
            world,
            TurnContext(tick=0, weather_seed=42),
        )

        assert plant.body is not None
        assert len(plant.body.root_cells) > 1
        assert plant.balance_sheet is not None
        assert plant.balance_sheet.organs_constructed["root"] == 1

    def test_unfunded_cost_does_not_partially_construct_or_spend(self):
        grid = HexGrid(5, 5)
        world = WorldState(grid)
        population = PlantPopulation()
        plant = population.register(
            home=HexCell(2, 2, 0),
            traits=TraitBundle(
                alloc_root=1.0,
                alloc_leaf=0.0,
                alloc_stem=0.0,
                alloc_reproduce=0.0,
            ),
        )
        _seed_reserves(plant, water=0.0, minerals=0.0, assimilate=5.0)
        before = plant.reserves.snapshot()

        GrowthPhase(population, grid).execute(
            world,
            world,
            TurnContext(tick=0, weather_seed=42),
        )

        assert plant.body is not None
        assert len(plant.body.graph.segments) == 0
        assert plant.reserves.snapshot() == before
        assert plant.balance_sheet is not None
        assert {"water", "minerals"} <= plant.balance_sheet.construction_limiting_factors
        assert plant.balance_sheet.organ_proposals["root"] == 1
        assert plant.balance_sheet.construction_potential.water > 0.0
        assert plant.balance_sheet.construction == ResourceVector()

    def test_root_grows_downward(self):
        grid = HexGrid(5, 5)
        world = WorldState(grid)
        population = PlantPopulation()
        plant = population.register(
            home=HexCell(2, 2, 0),
            traits=TraitBundle(
                alloc_root=1.0,
                alloc_leaf=0.0,
                alloc_stem=0.0,
                alloc_reproduce=0.0,
            ),
        )
        _seed_reserves(plant, water=10.0, minerals=10.0, assimilate=10.0)

        GrowthPhase(population, grid).execute(
            world,
            world,
            TurnContext(tick=0, weather_seed=42),
        )

        assert plant.body is not None
        assert min(cell.z for cell in plant.body.root_cells) < 0

    def test_stem_growth_constructs_an_attached_leaf(self):
        grid = HexGrid(5, 5)
        world = WorldState(grid)
        population = PlantPopulation()
        plant = population.register(
            home=HexCell(2, 2, 0),
            traits=TraitBundle(
                alloc_root=0.0,
                alloc_leaf=0.25,
                alloc_stem=0.75,
                alloc_reproduce=0.0,
            ),
        )
        _seed_reserves(plant, water=10.0, minerals=10.0, assimilate=10.0)

        GrowthPhase(population, grid).execute(
            world,
            world,
            TurnContext(tick=0, weather_seed=42),
        )

        assert plant.body is not None
        attached_leaves = [
            leaf
            for leaf in plant.body.graph.leaves.values()
            if leaf.attachment_segment_id is not None
        ]
        assert len(attached_leaves) == 1
        leaf = attached_leaves[0]
        segment = plant.body.graph.segments[leaf.attachment_segment_id]
        assert leaf.cell == segment.end
        assert plant.balance_sheet is not None
        assert plant.balance_sheet.organs_constructed["stem"] == 1
        assert plant.balance_sheet.organs_constructed["leaf"] == 1
