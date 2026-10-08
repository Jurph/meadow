"""Tests for plant domain."""

import pytest

from meadow.hex import HexCell
from meadow.plant import PlantPopulation, TraitBundle
from meadow.resources import ResourceVector


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


class TestTraitBundle:
    def test_defaults_represent_generic_grass(self):
        t = TraitBundle()
        assert t.number_of_lobes == 1.0
        assert t.lobe_aspect_ratio > 5.0
        assert t.lobe_length > 0.0

    def test_effective_leaf_area_grass(self):
        t = TraitBundle(number_of_lobes=1.0, lobe_aspect_ratio=20.0, lobe_length=15.0)
        area = t.effective_leaf_area
        assert 5.0 < area < 15.0

    def test_effective_leaf_area_maple(self):
        t = TraitBundle(number_of_lobes=5.0, lobe_aspect_ratio=1.5, lobe_length=8.0)
        area = t.effective_leaf_area
        assert 100.0 < area < 250.0

    def test_effective_leaf_area_zero_lobes(self):
        t = TraitBundle(number_of_lobes=0.0)
        assert t.effective_leaf_area == pytest.approx(0.0)

    def test_allocation_weights_default_equal(self):
        t = TraitBundle()
        assert t.alloc_root == t.alloc_leaf == t.alloc_stem == t.alloc_reproduce

    def test_zone_based_trait_defaults(self):
        traits = TraitBundle()
        assert traits.basal_length > 0
        assert traits.branch_spacing > 0
        assert traits.max_root_length > 0
        assert traits.gravitropism_weight > 0
        assert traits.root_construction_cost.assimilate > 0
        assert traits.stem_construction_cost.assimilate > 0
        assert traits.leaf_construction_cost.assimilate > 0


class TestPlantBody:
    def test_seed_body_has_crown_root_and_explicit_leaf(self):
        home = HexCell(3, 3, 0)
        plant = PlantPopulation().register(home=home)

        assert plant.body is not None
        assert home in plant.body.root_cells
        assert {leaf.cell for leaf in plant.body.graph.leaves.values()} == {home}


class TestPlantWithBody:
    def test_register_with_home_creates_body(self):
        pop = PlantPopulation()
        p = pop.register(home=HexCell(2, 2, 0))
        assert p.body is not None
        assert p.body.home == HexCell(2, 2, 0)

    def test_register_without_home_has_no_body(self):
        pop = PlantPopulation()
        p = pop.register()
        assert p.body is None

    def test_plant_reserves_start_at_zero(self):
        plant = PlantPopulation().register(home=HexCell(0, 0, 0))
        assert plant.reserves.snapshot() == ResourceVector()

    def test_register_with_home_creates_graph(self):
        pop = PlantPopulation()
        p = pop.register(home=HexCell(2, 2, 0))
        assert p.body is not None
        assert p.body.graph is not None
        assert len(p.body.graph.tips) == 2  # root + stem

    def test_root_cells_from_graph(self):
        plant = PlantPopulation().register(home=HexCell(3, 3, 0))
        assert plant.body is not None
        assert HexCell(3, 3, 0) in plant.body.root_cells

    def test_leaf_organs_from_graph(self):
        plant = PlantPopulation().register(home=HexCell(3, 3, 0))
        assert plant.body is not None
        assert len(plant.body.graph.leaves) == 1
