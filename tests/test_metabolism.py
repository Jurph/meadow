"""Tests for metabolism pure functions."""

import pytest

from meadow.metabolism import LEAF_AREA_UNIT, allocate_cellulose, compute_photosynthesis
from meadow.plant import TraitBundle


class TestPhotosynthesis:
    def test_limited_by_moisture(self):
        result = compute_photosynthesis(moisture=0.5, nutrients=10.0, light=1.0, leaf_area=200.0)
        assert result == pytest.approx(0.5)

    def test_limited_by_nutrients(self):
        result = compute_photosynthesis(moisture=10.0, nutrients=0.3, light=1.0, leaf_area=200.0)
        assert result == pytest.approx(0.3)

    def test_limited_by_effective_light(self):
        result = compute_photosynthesis(moisture=10.0, nutrients=10.0, light=1.0, leaf_area=50.0)
        assert result == pytest.approx(1.0 * 50.0 / LEAF_AREA_UNIT)

    def test_zero_moisture_produces_nothing(self):
        assert compute_photosynthesis(0.0, 5.0, 1.0, 100.0) == 0.0

    def test_zero_light_produces_nothing(self):
        assert compute_photosynthesis(5.0, 5.0, 0.0, 100.0) == 0.0

    def test_zero_leaf_area_produces_nothing(self):
        assert compute_photosynthesis(5.0, 5.0, 1.0, 0.0) == 0.0


class TestAllocateCellulose:
    def test_equal_weights_split_evenly(self):
        t = TraitBundle()
        alloc = allocate_cellulose(4.0, t)
        assert alloc["root"] == pytest.approx(1.0)
        assert alloc["leaf"] == pytest.approx(1.0)
        assert alloc["stem"] == pytest.approx(1.0)
        assert alloc["reproduce"] == pytest.approx(1.0)

    def test_sum_equals_input(self):
        t = TraitBundle(alloc_root=3.0, alloc_leaf=1.0, alloc_stem=0.5, alloc_reproduce=0.5)
        alloc = allocate_cellulose(10.0, t)
        assert sum(alloc.values()) == pytest.approx(10.0)

    def test_zero_cellulose_returns_zeros(self):
        alloc = allocate_cellulose(0.0, TraitBundle())
        assert all(v == 0.0 for v in alloc.values())

    def test_heavy_root_allocation(self):
        t = TraitBundle(alloc_root=8.0, alloc_leaf=1.0, alloc_stem=0.5, alloc_reproduce=0.5)
        alloc = allocate_cellulose(10.0, t)
        assert alloc["root"] == pytest.approx(8.0)
