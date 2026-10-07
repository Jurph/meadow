"""Uptake phase: plants absorb moisture and nutrients from root tiles.

Each root hex contributes: available_resource * root_reach.
Absorbed amounts are deducted from the tile and added to plant reserves.
"""

from __future__ import annotations

from meadow.phases import PhaseName
from meadow.plant import PlantPopulation
from meadow.world import PhaseResult, TurnContext, WorldMutator, WorldView


class UptakePhase:
    """Plants pull resources from root hexes into internal reserves."""

    def __init__(self, population: PlantPopulation) -> None:
        self._pop = population

    @property
    def name(self) -> PhaseName:
        return PhaseName.UPTAKE

    def execute(self, view: WorldView, mutator: WorldMutator, ctx: TurnContext) -> PhaseResult:
        total_moisture_taken = 0.0
        total_nutrient_taken = 0.0
        for plant in self._pop:
            if plant.body is None:
                continue
            reach = plant.traits.root_reach
            for h in plant.body.root_hexes:
                m_avail = view.moisture_at(h)
                n_avail = view.nutrients_at(h)
                m_take = m_avail * reach
                n_take = n_avail * reach
                mutator.apply_flow_delta(h, -m_take, -n_take)
                plant.moisture_reserve += m_take
                plant.nutrient_reserve += n_take
                total_moisture_taken += m_take
                total_nutrient_taken += n_take
        return PhaseResult(
            phase_name=self.name.name,
            diagnostics={
                "moisture_taken": total_moisture_taken,
                "nutrient_taken": total_nutrient_taken,
            },
        )
