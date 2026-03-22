"""Growth phase: photosynthesis and cellulose allocation.

Each plant converts reserves + light into cellulose via metabolism helpers,
then allocates cellulose to growth categories. Actual hex expansion
(new roots, new leaves) is deferred to Phase 4.
"""

from __future__ import annotations

from meadow.metabolism import allocate_cellulose, compute_photosynthesis
from meadow.phases import PhaseName
from meadow.plant import PlantPopulation
from meadow.world import PhaseResult, TurnContext, WorldMutator, WorldView


class GrowthPhase:
    """Photosynthesize and allocate cellulose for each plant."""

    def __init__(self, population: PlantPopulation) -> None:
        self._pop = population

    @property
    def name(self) -> PhaseName:
        return PhaseName.GROWTH

    def execute(
        self, view: WorldView, _mutator: WorldMutator, _ctx: TurnContext
    ) -> PhaseResult:
        total_cellulose = 0.0
        for plant in self._pop:
            if plant.body is None:
                continue
            leaves = plant.body.leaf_hexes
            if leaves is None:
                continue
            total_light = sum(view.light_at(h) for h in leaves)
            produced = compute_photosynthesis(
                plant.moisture_reserve,
                plant.nutrient_reserve,
                total_light,
                plant.traits.effective_leaf_area,
            )
            plant.moisture_reserve -= produced
            plant.nutrient_reserve -= produced
            plant.cellulose += produced
            total_cellulose += produced
            allocate_cellulose(produced, plant.traits)
        return PhaseResult(
            phase_name=self.name.name,
            diagnostics={"cellulose_produced": total_cellulose},
        )
