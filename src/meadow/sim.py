"""Turn pipeline: orchestrates phases in fixed order.

No physics here — just sequencing and validation.
"""

from __future__ import annotations

from dataclasses import dataclass

from meadow.flow import FlowPhase
from meadow.growth import GrowthPhase
from meadow.hex import HexCell, HexGrid, surface
from meadow.light import LightPhase
from meadow.phases import PHASE_ORDER, NoOpPhase, Phase, PhaseName
from meadow.plant import PlantPopulation, TraitBundle
from meadow.snapshot import WorldSnapshot, build_world_snapshot
from meadow.uptake import UptakePhase
from meadow.weather import WeatherPhase
from meadow.world import PhaseResult, TurnContext, WorldMutator, WorldView
from meadow.world_state import WorldState


@dataclass(frozen=True)
class SimulationConfig:
    """Stable inputs for creating a deterministic Meadow simulation."""

    width: int = 7
    height: int = 7
    weather_seed: int = 42

    def __post_init__(self) -> None:
        if self.width < 1 or self.height < 1:
            raise ValueError(
                f"Simulation dimensions must be positive, got {self.width}x{self.height}"
            )


class TurnPipeline:
    """Executes registered phases in PHASE_ORDER sequence."""

    def __init__(self, phases: dict[PhaseName, Phase]) -> None:
        missing = set(PHASE_ORDER) - set(phases.keys())
        if missing:
            raise ValueError(f"Missing phases: {missing}")
        self._phases = phases

    def run_tick(
        self, view: WorldView, mutator: WorldMutator, ctx: TurnContext
    ) -> list[PhaseResult]:
        results: list[PhaseResult] = []
        for phase_name in PHASE_ORDER:
            result = self._phases[phase_name].execute(view, mutator, ctx)
            results.append(result)
        return results


class Simulation:
    """Own the mutable world and expose deterministic ticks and snapshots."""

    def __init__(self, config: SimulationConfig | None = None) -> None:
        self._config = config or SimulationConfig()
        self._tick = 0
        self._grid = HexGrid(self._config.width, self._config.height)
        self._world = WorldState(self._grid)
        self._population = PlantPopulation()

        for column in self._grid:
            self._world.apply_flow_delta(surface(column), 0.0, 100.0)

        home = HexCell(self._config.width // 2, self._config.height // 2, 0)
        plant = self._population.register(
            home=home,
            traits=TraitBundle(
                number_of_lobes=1.0,
                lobe_aspect_ratio=1.0,
                lobe_length=12.0,
                alloc_root=0.5,
                alloc_leaf=0.25,
                alloc_stem=0.25,
                alloc_reproduce=0.0,
                hydrotropism_weight=0.0,
            ),
        )
        self._world.set_occupant(home.column, plant.id)

        self._pipeline = TurnPipeline(
            {
                PhaseName.WEATHER: WeatherPhase(rainfall_per_tick=10.0),
                PhaseName.FLOW: FlowPhase(),
                PhaseName.LIGHT: LightPhase(base_sunlight=1.0),
                PhaseName.UPTAKE: UptakePhase(self._population),
                PhaseName.DEPLETION: NoOpPhase(PhaseName.DEPLETION),
                PhaseName.GROWTH: GrowthPhase(self._population, self._grid),
            }
        )

    def run(self, ticks: int) -> WorldSnapshot:
        """Advance by *ticks* and return the resulting immutable snapshot."""
        if ticks < 0:
            raise ValueError(f"ticks must be non-negative, got {ticks}")
        for _ in range(ticks):
            context = TurnContext(
                tick=self._tick,
                weather_seed=self._config.weather_seed,
            )
            self._pipeline.run_tick(self._world, self._world, context)
            self._tick += 1
        return self.snapshot()

    def snapshot(self) -> WorldSnapshot:
        """Copy current mutable state into the renderer/save contract."""
        return build_world_snapshot(
            tick=self._tick,
            world=self._world,
            population=self._population,
        )
