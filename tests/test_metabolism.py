"""Tests for metabolism pure functions."""

import pytest

from meadow.metabolism import (
    LEAF_AREA_UNIT,
    allocate_assimilate,
    compute_light_limited_assimilation,
    compute_photosynthesis,
)
from meadow.plant import TraitBundle


class TestPhotosynthesis:
    def test_limited_by_water(self):
        result = compute_photosynthesis(water=0.5, light=1.0, leaf_area=200.0)
        assert result == pytest.approx(0.5)

    def test_limited_by_effective_light(self):
        result = compute_photosynthesis(water=10.0, light=1.0, leaf_area=50.0)
        assert result == pytest.approx(1.0 * 50.0 / LEAF_AREA_UNIT)

    def test_potential_is_independent_of_water(self):
        potential = compute_light_limited_assimilation(light=2.0, leaf_area=50.0)
        assert potential == pytest.approx(1.0)

    def test_zero_water_produces_nothing(self):
        assert compute_photosynthesis(water=0.0, light=1.0, leaf_area=100.0) == 0.0

    def test_zero_light_produces_nothing(self):
        assert compute_photosynthesis(water=5.0, light=0.0, leaf_area=100.0) == 0.0

    def test_zero_leaf_area_produces_nothing(self):
        assert compute_photosynthesis(water=5.0, light=1.0, leaf_area=0.0) == 0.0


class TestAllocateAssimilate:
    def test_equal_weights_split_evenly(self):
        allocation = allocate_assimilate(4.0, TraitBundle())
        assert allocation["root"] == pytest.approx(1.0)
        assert allocation["leaf"] == pytest.approx(1.0)
        assert allocation["stem"] == pytest.approx(1.0)
        assert allocation["reproduce"] == pytest.approx(1.0)

    def test_sum_equals_input(self):
        traits = TraitBundle(
            alloc_root=3.0,
            alloc_leaf=1.0,
            alloc_stem=0.5,
            alloc_reproduce=0.5,
        )
        allocation = allocate_assimilate(10.0, traits)
        assert sum(allocation.values()) == pytest.approx(10.0)

    def test_zero_assimilate_returns_zeros(self):
        allocation = allocate_assimilate(0.0, TraitBundle())
        assert all(value == 0.0 for value in allocation.values())

    def test_heavy_root_allocation(self):
        traits = TraitBundle(
            alloc_root=8.0,
            alloc_leaf=1.0,
            alloc_stem=0.5,
            alloc_reproduce=0.5,
        )
        allocation = allocate_assimilate(10.0, traits)
        assert allocation["root"] == pytest.approx(8.0)
