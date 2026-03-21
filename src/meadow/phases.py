"""Phase contracts and ordering for the turn pipeline.

Each named phase executes once per tick in PHASE_ORDER sequence.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Protocol, runtime_checkable

from meadow.world import PhaseResult, TurnContext, WorldMutator, WorldView


class PhaseName(Enum):
    WEATHER = auto()
    FLOW = auto()
    LIGHT = auto()
    UPTAKE = auto()
    DEPLETION = auto()
    GROWTH = auto()


PHASE_ORDER: tuple[PhaseName, ...] = (
    PhaseName.WEATHER,
    PhaseName.FLOW,
    PhaseName.LIGHT,
    PhaseName.UPTAKE,
    PhaseName.DEPLETION,
    PhaseName.GROWTH,
)


@runtime_checkable
class Phase(Protocol):
    @property
    def name(self) -> PhaseName: ...

    def execute(
        self, view: WorldView, mutator: WorldMutator, ctx: TurnContext
    ) -> PhaseResult: ...


class NoOpPhase:
    """Stub phase that does nothing — placeholder for Phase 1."""

    def __init__(self, phase_name: PhaseName) -> None:
        self._name = phase_name

    @property
    def name(self) -> PhaseName:
        return self._name

    def execute(
        self, view: WorldView, mutator: WorldMutator, ctx: TurnContext
    ) -> PhaseResult:
        return PhaseResult(phase_name=self._name.name)
