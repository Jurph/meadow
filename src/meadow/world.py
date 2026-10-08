"""World-layer contracts: read/write protocols, turn context, phase results.

Plant code interacts with the world ONLY through WorldView (reads)
and WorldMutator (writes). Implementations live elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from meadow.hex import Axial, HexCell

SIM_API_VERSION: int = 2


@dataclass(frozen=True)
class TurnContext:
    """Read-only snapshot passed to every phase in a tick."""

    tick: int
    weather_seed: int


@dataclass
class PhaseResult:
    """Returned by each phase for diagnostics and testing."""

    phase_name: str
    diagnostics: dict[str, float] | None = None


@runtime_checkable
class WorldView(Protocol):
    """Read surface exposed to plants and phases."""

    def moisture_at(self, h: HexCell) -> float: ...
    def nutrients_at(self, h: HexCell) -> float: ...
    def light_at(self, h: HexCell) -> float: ...
    def occupant_id_at(self, col: Axial) -> int | None: ...


@runtime_checkable
class WorldMutator(Protocol):
    """Write surface scoped to phase execution."""

    def apply_flow_delta(
        self, h: HexCell, moisture_delta: float, nutrient_delta: float
    ) -> None: ...
    def set_light(self, h: HexCell, value: float) -> None: ...
    def set_occupant(self, col: Axial, plant_id: int | None) -> None: ...
