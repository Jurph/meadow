"""Behavior tests for plant resource accounting."""

import pytest

from meadow.resources import (
    AssimilateAllocation,
    PlantBalanceSheet,
    ResourcePool,
    ResourceVector,
)


def test_resource_pool_spending_is_atomic() -> None:
    pool = ResourcePool(water=1.0, minerals=2.0, assimilate=3.0)
    opening = pool.snapshot()

    assert not pool.try_spend(ResourceVector(water=2.0, minerals=0.5, assimilate=0.5))
    assert pool.snapshot() == opening

    assert pool.try_spend(ResourceVector(water=0.5, minerals=1.0, assimilate=2.0))
    assert pool.snapshot() == ResourceVector(water=0.5, minerals=1.0, assimilate=1.0)

    rounding_pool = ResourcePool(water=0.3)
    assert rounding_pool.try_spend(ResourceVector(water=0.2))
    assert rounding_pool.try_spend(ResourceVector(water=0.1))
    assert rounding_pool.water == 0.0


def test_resource_vectors_reject_negative_or_non_finite_values() -> None:
    with pytest.raises(ValueError, match="non-negative finite"):
        ResourceVector(water=-1.0)
    with pytest.raises(ValueError, match="non-negative finite"):
        ResourceVector(assimilate=float("inf"))
    with pytest.raises(ValueError, match="non-negative finite"):
        AssimilateAllocation(root=-1.0)


def test_assimilate_allocations_accumulate_without_category_starvation() -> None:
    allocation = AssimilateAllocation()
    allocation.credit({"root": 0.5, "leaf": 0.25, "stem": 0.25, "reproduce": 0.0})
    allocation.credit({"root": 0.5, "leaf": 0.25, "stem": 0.25, "reproduce": 0.0})

    assert allocation.try_spend("root", 1.0)
    assert allocation.stem == 0.5
    assert allocation.leaf == 0.5


def test_plant_balance_sheet_reconciles_sources_and_sinks() -> None:
    pool = ResourcePool(water=5.0, minerals=4.0, assimilate=1.0)
    sheet = PlantBalanceSheet.open(tick=7, reserves=pool.snapshot())

    uptake = ResourceVector(water=2.0, minerals=1.0)
    pool.credit(uptake)
    sheet.record_root_uptake(potential=uptake, actual=uptake)

    assert pool.try_spend(ResourceVector(water=2.0))
    pool.credit(ResourceVector(assimilate=2.0))
    sheet.record_photosynthesis(potential=3.0, actual=2.0, water_used=2.0, limiter="water")

    construction = ResourceVector(water=0.5, minerals=1.0, assimilate=2.0)
    sheet.record_construction_proposal(construction, organ_type="root")
    assert pool.try_spend(construction)
    sheet.record_construction(construction, organ_type="root")
    sheet.close(pool.snapshot())

    assert sheet.root_uptake.potential == uptake
    assert sheet.root_uptake.actual == uptake
    assert sheet.photosynthesis.potential.assimilate == 3.0
    assert sheet.photosynthesis.actual.assimilate == 2.0
    assert sheet.photosynthesis.limiting_factors == {"water"}
    assert sheet.closing == ResourceVector(water=4.5, minerals=4.0, assimilate=1.0)
    assert sheet.organs_constructed == {"root": 1}
    assert sheet.construction_potential == construction
    assert sheet.organ_proposals == {"root": 1}


def test_balance_sheet_clamps_epsilon_roundoff_when_a_reserve_is_exhausted() -> None:
    pool = ResourcePool(water=0.3)
    sheet = PlantBalanceSheet.open(tick=0, reserves=pool.snapshot())
    cost = ResourceVector(water=0.1)

    for _ in range(3):
        sheet.record_construction_proposal(cost, organ_type="root")
        assert pool.try_spend(cost)
        sheet.record_construction(cost, organ_type="root")

    sheet.close(pool.snapshot())

    assert sheet.closing.water == 0.0


def test_balance_sheet_rejects_unproposed_construction() -> None:
    sheet = PlantBalanceSheet.open(tick=0, reserves=ResourceVector())

    with pytest.raises(ValueError, match="without a recorded proposal"):
        sheet.record_construction(ResourceVector(), organ_type="root")


def test_balance_sheet_rejects_an_unrecorded_resource_change() -> None:
    pool = ResourcePool(water=1.0)
    sheet = PlantBalanceSheet.open(tick=0, reserves=pool.snapshot())
    pool.credit(ResourceVector(water=1.0))

    with pytest.raises(ValueError, match="does not reconcile"):
        sheet.close(pool.snapshot())
