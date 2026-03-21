"""Light phase: distribute sunlight to tiles.

v1 simplification: uniform sunlight everywhere, no canopy occlusion.
Canopy-based shading will be added when plants have leaf coverage.
"""

from __future__ import annotations

from meadow.phases import PhaseName
from meadow.world import PhaseResult, TurnContext, WorldMutator, WorldView
from meadow.world_state import WorldState


class LightPhase:
    """Set sunlight to a uniform base value across all tiles."""

    def __init__(self, base_sunlight: float = 1.0) -> None:
        self._base = base_sunlight

    @property
    def name(self) -> PhaseName:
        return PhaseName.LIGHT

    def execute(
        self, view: WorldView, mutator: WorldMutator, ctx: TurnContext
    ) -> PhaseResult:
        if not isinstance(mutator, WorldState):
            raise TypeError("LightPhase requires a WorldState mutator")
        mutator.light[:] = self._base
        return PhaseResult(phase_name=self.name.name)
