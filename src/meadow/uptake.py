"""Uptake phase: root cells transfer soil water and minerals into plants.

The current single-plant rule uses ``root_reach`` as per-cell uptake capacity.
Potential and actual transfers are recorded separately for later competition.
"""

from __future__ import annotations

from meadow.phases import PhaseName
from meadow.plant import PlantPopulation
from meadow.resources import ResourceVector
from meadow.world import PhaseResult, TurnContext, WorldMutator, WorldView


class UptakePhase:
    """Transfer locally available soil resources into plant reserves."""

    def __init__(self, population: PlantPopulation) -> None:
        self._pop = population

    @property
    def name(self) -> PhaseName:
        return PhaseName.UPTAKE

    def execute(self, view: WorldView, mutator: WorldMutator, ctx: TurnContext) -> PhaseResult:
        total_water_taken = 0.0
        total_minerals_taken = 0.0
        for plant in self._pop:
            sheet = plant.balance_sheet_for_tick(ctx.tick)
            if plant.body is None:
                continue

            reach = max(plant.traits.root_reach, 0.0)
            potential_water = 0.0
            actual_water = 0.0
            potential_minerals = 0.0
            actual_minerals = 0.0
            for cell in plant.body.root_cells:
                water_available = max(view.moisture_at(cell), 0.0)
                minerals_available = max(view.nutrients_at(cell), 0.0)
                water_potential = water_available * reach
                minerals_potential = minerals_available * reach
                water_taken = min(water_available, water_potential)
                minerals_taken = min(minerals_available, minerals_potential)
                mutator.apply_flow_delta(cell, -water_taken, -minerals_taken)
                potential_water += water_potential
                actual_water += water_taken
                potential_minerals += minerals_potential
                actual_minerals += minerals_taken

            actual = ResourceVector(water=actual_water, minerals=actual_minerals)
            plant.reserves.credit(actual)
            sheet.record_root_uptake(
                potential=ResourceVector(water=potential_water),
                actual=ResourceVector(water=actual_water),
                limiter="soil_water" if actual_water < potential_water else None,
            )
            sheet.record_root_uptake(
                potential=ResourceVector(minerals=potential_minerals),
                actual=ResourceVector(minerals=actual_minerals),
                limiter="soil_minerals" if actual_minerals < potential_minerals else None,
            )
            total_water_taken += actual_water
            total_minerals_taken += actual_minerals

        return PhaseResult(
            phase_name=self.name.name,
            diagnostics={
                "water_taken": total_water_taken,
                "minerals_taken": total_minerals_taken,
            },
        )
