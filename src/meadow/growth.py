"""Growth phase: leaf photosynthesis, allocation, and organ construction.

Photosynthesis produces assimilate from explicit leaf organs. Growth proposals
pay complete resource costs before mutating the organ graph.
"""

from __future__ import annotations

import random

from meadow.hex import HexGrid, neighbors_3d
from meadow.metabolism import allocate_assimilate, compute_light_limited_assimilation
from meadow.phases import PhaseName
from meadow.plant import Plant, PlantPopulation
from meadow.plant_graph import GrowthTip, PlantGraph, SegmentType
from meadow.resources import RESOURCE_EPSILON, PlantBalanceSheet, ResourceVector
from meadow.tropisms import rank_growth_candidates
from meadow.world import PhaseResult, TurnContext, WorldMutator, WorldView


def _in_branching_zone(tip: GrowthTip, plant: Plant) -> bool:
    """Check if a tip's accumulated length is in the branching zone."""
    traits = plant.traits
    after_basal = tip.accumulated_length > traits.basal_length
    before_apical = tip.accumulated_length < (traits.max_root_length - traits.apical_length)
    return after_basal and before_apical


def _should_branch(tip: GrowthTip, plant: Plant, rng: random.Random) -> bool:
    """Decide whether to create a lateral branch at the current tip position."""
    if not _in_branching_zone(tip, plant):
        return False
    traits = plant.traits
    if traits.branch_spacing <= 0.0:
        return False
    at_branch_point = (tip.accumulated_length % traits.branch_spacing) < 1.0
    return at_branch_point and rng.random() < traits.branch_probability


def _resource_limiters(plant: Plant, cost: ResourceVector) -> tuple[str, ...]:
    reserves = plant.reserves
    return tuple(
        name
        for name, available, required in (
            ("water", reserves.water, cost.water),
            ("minerals", reserves.minerals, cost.minerals),
            ("assimilate", reserves.assimilate, cost.assimilate),
        )
        if available + RESOURCE_EPSILON < required
    )


def _fund_assimilate_allocation(plant: Plant) -> None:
    """Earmark newly available assimilate without resetting older budgets."""
    unallocated = plant.reserves.assimilate - plant.assimilate_allocation.total
    if unallocated < -1e-9:
        raise RuntimeError(f"plant {plant.id} allocated more assimilate than it holds")
    if unallocated > RESOURCE_EPSILON:
        plant.assimilate_allocation.credit(allocate_assimilate(unallocated, plant.traits))


def _pay_construction(
    plant: Plant,
    category: str,
    organ_type: str,
    cost: ResourceVector,
    sheet: PlantBalanceSheet,
) -> bool:
    """Pay one complete organ cost from its persistent budget and reserves."""
    sheet.record_construction_proposal(cost, organ_type=organ_type)
    allocation = plant.assimilate_allocation
    if allocation.available(category) + RESOURCE_EPSILON < cost.assimilate:
        sheet.record_construction_blocked(f"{category}_allocation")
        return False

    limiters = _resource_limiters(plant, cost)
    if limiters:
        sheet.record_construction_blocked(*limiters)
        return False

    if not plant.reserves.try_spend(cost):
        raise RuntimeError("affordable construction cost could not be spent")
    if not allocation.try_spend(category, cost.assimilate):
        raise RuntimeError("funded construction allocation could not be spent")
    sheet.record_construction(cost, organ_type=organ_type)
    return True


def _has_leaf_at_attachment(graph: PlantGraph, segment_id: int) -> bool:
    return any(leaf.attachment_segment_id == segment_id for leaf in graph.leaves.values())


def _try_attach_leaf(
    plant: Plant,
    tip: GrowthTip,
    sheet: PlantBalanceSheet,
) -> ResourceVector:
    if (
        plant.body is None
        or tip.segment_type != SegmentType.STEM
        or tip.segment_id < 0
        or _has_leaf_at_attachment(plant.body.graph, tip.segment_id)
    ):
        return ResourceVector()

    cost = plant.traits.leaf_construction_cost
    if not _pay_construction(plant, "leaf", "leaf", cost, sheet):
        return ResourceVector()
    plant.body.graph.add_leaf(
        tip.segment_id,
        tip.cell,
        area=plant.traits.effective_leaf_area,
    )
    return cost


def _grow_tips(
    plant: Plant,
    view: WorldView,
    grid: HexGrid,
    rng: random.Random,
    sheet: PlantBalanceSheet,
) -> ResourceVector:
    """Extend active tips and construct leaves after paying full costs."""
    if plant.body is None:
        return ResourceVector()

    graph = plant.body.graph
    spent = ResourceVector()
    new_tips: list[GrowthTip] = []
    tips_to_keep: list[GrowthTip] = []

    for tip in graph.tips:
        spent = spent + _try_attach_leaf(plant, tip, sheet)
        is_root = tip.segment_type == SegmentType.ROOT
        if tip.accumulated_length >= plant.traits.max_root_length and is_root:
            continue

        candidates = [cell for cell in neighbors_3d(tip.cell) if grid.cell_in_bounds(cell)]
        if not candidates:
            sheet.record_construction_blocked("space")
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
            sheet.record_construction_blocked("space")
            tips_to_keep.append(tip)
            continue

        category = "root" if is_root else "stem"
        organ_type = category
        cost = (
            plant.traits.root_construction_cost if is_root else plant.traits.stem_construction_cost
        )
        if not _pay_construction(
            plant,
            category,
            organ_type,
            cost,
            sheet,
        ):
            tips_to_keep.append(tip)
            continue

        best_cell = ranked[0][0]
        segment = graph.add_segment(
            parent_id=None if tip.segment_id < 0 else tip.segment_id,
            start=tip.cell,
            end=best_cell,
            segment_type=tip.segment_type,
            order=tip.order,
            accumulated_length=tip.accumulated_length + 1.0,
        )
        new_tip = GrowthTip(
            segment_id=segment.id,
            cell=best_cell,
            segment_type=tip.segment_type,
            order=tip.order,
            accumulated_length=tip.accumulated_length + 1.0,
        )
        new_tips.append(new_tip)
        spent = spent + cost

        if not is_root:
            leaf_cost = plant.traits.leaf_construction_cost
            if _pay_construction(
                plant,
                "leaf",
                "leaf",
                leaf_cost,
                sheet,
            ):
                graph.add_leaf(
                    segment.id,
                    best_cell,
                    area=plant.traits.effective_leaf_area,
                )
                spent = spent + leaf_cost

        if not _should_branch(new_tip, plant, rng):
            continue

        lateral_candidates = [cell for cell in candidates if cell != best_cell]
        if not lateral_candidates:
            sheet.record_construction_blocked("space")
            continue
        lateral_ranked = rank_growth_candidates(
            tip.cell,
            lateral_candidates,
            view,
            is_root=is_root,
            gravity_weight=plant.traits.gravitropism_weight * 0.5,
            hydro_weight=plant.traits.hydrotropism_weight,
        )
        if not lateral_ranked or not _pay_construction(
            plant,
            category,
            organ_type,
            cost,
            sheet,
        ):
            continue

        lateral_cell = lateral_ranked[0][0]
        lateral_segment = graph.add_segment(
            parent_id=segment.id,
            start=tip.cell,
            end=lateral_cell,
            segment_type=tip.segment_type,
            order=tip.order + 1,
            accumulated_length=1.0,
        )
        new_tips.append(
            GrowthTip(
                segment_id=lateral_segment.id,
                cell=lateral_cell,
                segment_type=tip.segment_type,
                order=tip.order + 1,
                accumulated_length=1.0,
            )
        )
        spent = spent + cost
        if not is_root:
            leaf_cost = plant.traits.leaf_construction_cost
            if _pay_construction(
                plant,
                "leaf",
                "leaf",
                leaf_cost,
                sheet,
            ):
                graph.add_leaf(
                    lateral_segment.id,
                    lateral_cell,
                    area=plant.traits.effective_leaf_area,
                )
                spent = spent + leaf_cost

    graph._tips = tips_to_keep + new_tips
    return spent


def _photosynthesize(
    plant: Plant,
    view: WorldView,
    sheet: PlantBalanceSheet,
) -> tuple[float, float]:
    if plant.body is None:
        return 0.0, 0.0

    leaves = tuple(plant.body.graph.leaves.values())
    active_leaf_area = sum(leaf.area * leaf.health for leaf in leaves)
    potential = sum(
        compute_light_limited_assimilation(
            light=view.light_at(leaf.cell),
            leaf_area=leaf.area * leaf.health,
        )
        for leaf in leaves
    )
    actual = min(potential, plant.reserves.water)
    limiter: str | None = None
    if actual + RESOURCE_EPSILON < potential:
        limiter = "water"
    elif active_leaf_area <= 0.0:
        limiter = "leaf_area"
    elif potential <= 0.0:
        limiter = "light"

    if actual > 0.0:
        water_cost = ResourceVector(water=actual)
        if not plant.reserves.try_spend(water_cost):
            raise RuntimeError("photosynthesis exceeded available water")
        plant.reserves.credit(ResourceVector(assimilate=actual))
    sheet.record_photosynthesis(
        potential=potential,
        actual=actual,
        water_used=actual,
        limiter=limiter,
    )
    return potential, actual


class GrowthPhase:
    """Photosynthesize, allocate assimilate, and construct organs."""

    def __init__(self, population: PlantPopulation, grid: HexGrid) -> None:
        self._pop = population
        self._grid = grid

    @property
    def name(self) -> PhaseName:
        return PhaseName.GROWTH

    def execute(self, view: WorldView, mutator: WorldMutator, ctx: TurnContext) -> PhaseResult:
        del mutator
        rng = random.Random(ctx.weather_seed + ctx.tick)
        total_potential = 0.0
        total_assimilate = 0.0
        total_spent = ResourceVector()
        total_organs = 0

        for plant in self._pop:
            sheet = plant.balance_sheet_for_tick(ctx.tick)
            potential, actual = _photosynthesize(plant, view, sheet)
            total_potential += potential
            total_assimilate += actual

            if plant.body is not None:
                _fund_assimilate_allocation(plant)
                spent = _grow_tips(
                    plant,
                    view,
                    self._grid,
                    rng,
                    sheet,
                )
                total_spent = total_spent + spent
                total_organs += sum(sheet.organs_constructed.values())
            sheet.close(plant.reserves.snapshot())

        return PhaseResult(
            phase_name=self.name.name,
            diagnostics={
                "assimilate_potential": total_potential,
                "assimilate_produced": total_assimilate,
                "water_used_for_photosynthesis": total_assimilate,
                "water_spent_on_growth": total_spent.water,
                "minerals_spent_on_growth": total_spent.minerals,
                "assimilate_spent_on_growth": total_spent.assimilate,
                "organs_constructed": float(total_organs),
            },
        )
