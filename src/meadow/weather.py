"""Weather phase: generates moisture inputs each tick.

v1 simplification: uniform rainfall across the entire grid.
"""

from __future__ import annotations

from meadow.phases import PhaseName
from meadow.world import PhaseResult, TurnContext, WorldMutator, WorldView
from meadow.world_state import WorldState


class WeatherPhase:
    """Adds uniform rainfall to every tile each tick."""

    def __init__(self, rainfall_per_tick: float = 1.0) -> None:
        self._rainfall = rainfall_per_tick

    @property
    def name(self) -> PhaseName:
        return PhaseName.WEATHER

    def execute(self, view: WorldView, mutator: WorldMutator, ctx: TurnContext) -> PhaseResult:
        if not isinstance(mutator, WorldState):
            raise TypeError("WeatherPhase requires a WorldState mutator for array access")
        mutator.moisture += self._rainfall
        total = self._rainfall * len(mutator.grid)
        return PhaseResult(
            phase_name=self.name.name,
            diagnostics={"rainfall_total": total},
        )
