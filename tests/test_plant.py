"""Tests for plant domain stubs."""

import pytest

from meadow.plant import PlantPopulation, TraitBundle


class TestPlantPopulation:
    def test_register_assigns_unique_ids(self):
        pop = PlantPopulation()
        p1 = pop.register()
        p2 = pop.register()
        assert p1.id != p2.id

    def test_len_tracks_living_plants(self):
        pop = PlantPopulation()
        assert len(pop) == 0
        pop.register()
        assert len(pop) == 1

    def test_remove_by_id(self):
        pop = PlantPopulation()
        p = pop.register()
        pop.remove(p.id)
        assert len(pop) == 0

    def test_remove_nonexistent_raises(self):
        pop = PlantPopulation()
        with pytest.raises(KeyError):
            pop.remove(999)

    def test_iteration_is_deterministic_by_id(self):
        pop = PlantPopulation()
        ids = [pop.register().id for _ in range(5)]
        assert [p.id for p in pop] == sorted(ids)

    def test_get_returns_plant_or_none(self):
        pop = PlantPopulation()
        p = pop.register()
        assert pop.get(p.id) is p
        assert pop.get(999) is None

    def test_register_with_custom_traits(self):
        pop = PlantPopulation()
        traits = TraitBundle()
        p = pop.register(traits=traits)
        assert p.traits is traits
