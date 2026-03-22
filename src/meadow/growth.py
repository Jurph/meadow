"""Growth phase: photosynthesis, allocation, and body expansion.

After photosynthesis produces cellulose, allocation splits it by trait weights.
Then root and stem tips extend into neighboring cells guided by tropisms,
with zone-based branching creating lateral growth points.

Branching zones follow Mußmann et al. 2024:
- basal zone: no branching (near parent junction)
- branching zone: laterals may emerge at branch_spacing intervals
- apical zone: no branching (active growing tip)
"""

from __future__ import annotations

import random

from meadow.hex import HexGrid, neighbors_3d
from meadow.metabolism import allocate_cellulose, compute_photosynthesis
from meadow.phases import PhaseName
from meadow.plant import Plant, PlantPopulation
from meadow.plant_graph import GrowthTip, SegmentType
from meadow.tropisms import rank_growth_candidates
from meadow.world import PhaseResult, TurnContext, WorldMutator, WorldView


def _in_branching_zone(tip: GrowthTip, plant: Plant) -> bool:
    """Check if a tip's accumulated length is in the branching zone."""
    t = plant.traits
    after_basal = tip.accumulated_length > t.basal_length
    before_apical = tip.accumulated_length < (t.max_root_length - t.apical_length)
    return after_basal and before_apical


def _should_branch(tip: GrowthTip, plant: Plant, rng: random.Random) -> bool:
    """Decide whether to create a lateral branch at the current tip position."""
    if not _in_branching_zone(tip, plant):
        return False
    t = plant.traits
    if t.branch_spacing <= 0:
        return False
    at_branch_point = (tip.accumulated_length % t.branch_spacing) < 1.0
    return at_branch_point and rng.random() < t.branch_probability


def _grow_tips(
    plant: Plant,
    allocation: dict[str, float],
    view: WorldView,
    grid: HexGrid,
    rng: random.Random,
) -> float:
    """Extend active growth tips, spending allocated cellulose. Returns cellulose spent."""
    if plant.body is None or plant.body.graph is None:
        return 0.0

    graph = plant.body.graph
    cost = plant.traits.cellulose_per_segment
    spent = 0.0
    new_tips: list[GrowthTip] = []
    tips_to_keep: list[GrowthTip] = []

    for tip in graph.tips:
        is_root = tip.segment_type == SegmentType.ROOT

        if is_root:
            available = allocation.get("root", 0.0)
        else:
            available = allocation.get("leaf", 0.0) + allocation.get("stem", 0.0)

        if available < cost or plant.cellulose < cost:
            tips_to_keep.append(tip)
            continue

        if tip.accumulated_length >= plant.traits.max_root_length and is_root:
            continue

        candidates = [c for c in neighbors_3d(tip.cell) if grid.cell_in_bounds(c)]
        if not candidates:
            tips_to_keep.append(tip)
            continue

        ranked = rank_growth_candidates(
            tip.cell,
            candidates,
            view,
            is_root=is_root,
            gravity_weight=plant.traits.gravitropism_weight,
            hydro_weight=plant.traits.hydrotropism_weight,
        )
        if not ranked:
            tips_to_keep.append(tip)
            continue

        best_cell = ranked[0][0]
        seg = graph.add_segment(
            parent_id=tip.segment_id,
            start=tip.cell,
            end=best_cell,
            segment_type=tip.segment_type,
            order=tip.order,
            accumulated_length=tip.accumulated_length + 1.0,
        )

        new_tip = GrowthTip(
            segment_id=seg.id,
            cell=best_cell,
            segment_type=tip.segment_type,
            order=tip.order,
            accumulated_length=tip.accumulated_length + 1.0,
        )
        new_tips.append(new_tip)

        plant.cellulose -= cost
        spent += cost
        if is_root:
            allocation["root"] = allocation.get("root", 0.0) - cost
        else:
            remaining = cost
            if allocation.get("leaf", 0.0) >= remaining:
                allocation["leaf"] -= remaining
            else:
                remaining -= allocation.get("leaf", 0.0)
                allocation["leaf"] = 0.0
                allocation["stem"] = allocation.get("stem", 0.0) - remaining

        if _should_branch(new_tip, plant, rng) and plant.cellulose >= cost:
            lateral_candidates = [
                c for c in candidates if c != best_cell and grid.cell_in_bounds(c)
            ]
            if lateral_candidates:
                lateral_ranked = rank_growth_candidates(
                    tip.cell,
                    lateral_candidates,
                    view,
                    is_root=is_root,
                    gravity_weight=plant.traits.gravitropism_weight * 0.5,
                    hydro_weight=plant.traits.hydrotropism_weight,
                )
                if lateral_ranked:
                    lateral_cell = lateral_ranked[0][0]
                    lat_seg = graph.add_segment(
                        parent_id=seg.id,
                        start=tip.cell,
                        end=lateral_cell,
                        segment_type=tip.segment_type,
                        order=tip.order + 1,
                        accumulated_length=1.0,
                    )
                    new_tips.append(
                        GrowthTip(
                            segment_id=lat_seg.id,
                            cell=lateral_cell,
                            segment_type=tip.segment_type,
                            order=tip.order + 1,
                            accumulated_length=1.0,
                        )
                    )
                    plant.cellulose -= cost
                    spent += cost

    graph._tips = tips_to_keep + new_tips
    return spent


class GrowthPhase:
    """Photosynthesize, allocate cellulose, and extend the plant body."""

    def __init__(self, population: PlantPopulation, grid: HexGrid) -> None:
        self._pop = population
        self._grid = grid

    @property
    def name(self) -> PhaseName:
        return PhaseName.GROWTH

    def execute(
        self, view: WorldView, mutator: WorldMutator, ctx: TurnContext
    ) -> PhaseResult:
        rng = random.Random(ctx.weather_seed + ctx.tick)
        total_cellulose = 0.0
        total_spent = 0.0

        for plant in self._pop:
            if plant.body is None:
                continue
            leaves = plant.body.leaf_hexes
            if not leaves:
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

            allocation = allocate_cellulose(plant.cellulose, plant.traits)
            spent = _grow_tips(plant, allocation, view, self._grid, rng)
            total_spent += spent

        return PhaseResult(
            phase_name=self.name.name,
            diagnostics={
                "cellulose_produced": total_cellulose,
                "cellulose_spent_on_growth": total_spent,
            },
        )
