"""Behavior tests for the production simulation and renderer snapshot seam."""

from meadow.sim import Simulation, SimulationConfig


def test_ten_tick_simulation_returns_deterministic_render_snapshot() -> None:
    config = SimulationConfig(width=7, height=7, weather_seed=42)

    first = Simulation(config).run(10)
    second = Simulation(config).run(10)

    assert first == second
    assert first.schema_version == 1
    assert first.sim_api_version == 1
    assert first.tick == 10
    assert first.world.width == 7
    assert first.world.height == 7
    assert len(first.tiles) == 49
    assert len(first.plants) == 1

    plant = first.plants[0]
    assert plant.home.q == 3
    assert plant.home.r == 3
    assert {segment.segment_type for segment in plant.segments} == {"ROOT", "STEM"}
    assert min(segment.end.z for segment in plant.segments if segment.segment_type == "ROOT") < 0
    assert max(segment.end.z for segment in plant.segments if segment.segment_type == "STEM") > 0
