"""Behavior tests for the production simulation and renderer snapshot seam."""

from meadow.sim import Simulation, SimulationConfig


def test_ten_tick_simulation_returns_deterministic_render_snapshot() -> None:
    config = SimulationConfig(width=7, height=7, weather_seed=42)

    first = Simulation(config).run(10)
    second = Simulation(config).run(10)

    assert first == second
    assert first.schema_version == 2
    assert first.sim_api_version == 2
    assert first.tick == 10
    assert first.world.width == 7
    assert first.world.height == 7
    assert len(first.tiles) == 49
    assert len(first.plants) == 1

    plant = first.plants[0]
    assert plant.home is not None
    assert plant.home.q == 3
    assert plant.home.r == 3
    assert plant.resources.water >= 0.0
    assert plant.resources.minerals >= 0.0
    assert plant.resources.assimilate >= 0.0
    assert plant.balance_sheet is not None
    assert plant.balance_sheet.tick == 9
    assert plant.balance_sheet.closing == plant.resources
    assert sum(item.count for item in plant.balance_sheet.organ_proposals) >= sum(
        item.count for item in plant.balance_sheet.organs_constructed
    )
    assert (
        plant.balance_sheet.construction_potential.assimilate
        >= plant.balance_sheet.construction.assimilate
    )
    assert len(plant.leaves) > 1
    assert all(leaf.area > 0.0 and 0.0 <= leaf.health <= 1.0 for leaf in plant.leaves)
    assert {segment.segment_type for segment in plant.segments} == {"ROOT", "STEM"}
    assert min(segment.end.z for segment in plant.segments if segment.segment_type == "ROOT") < 0
    assert max(segment.end.z for segment in plant.segments if segment.segment_type == "STEM") > 0
