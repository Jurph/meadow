"""Turn pipeline: orchestrates phases in fixed order.

No physics here — just sequencing and validation.
"""

from __future__ import annotations

from meadow.phases import PHASE_ORDER, Phase, PhaseName
from meadow.world import PhaseResult, TurnContext, WorldMutator, WorldView


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
