# Meadow Phase 3: Plant Traits, Body, and Metabolism — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill in the plant domain — real trait values (leaf geometry, root reach, allocation weights), plant body (root/leaf hex sets), pure metabolism functions, and working Uptake + Growth phases — so a plant placed on a grid accumulates cellulose through one tick.

**Architecture:** TraitBundle gets numeric fields (all defaulted so Phase 1 tests keep passing). PlantBody is a new dataclass on Plant. Metabolism is a set of **pure functions** in `src/meadow/metabolism.py`. UptakePhase and GrowthPhase hold a PlantPopulation reference, iterate plants, and call the pure helpers. Existing WorldMutator interface (`apply_flow_delta` with negative deltas) handles resource deduction.

**Tech Stack:** Python 3.11+, numpy, pytest, ruff, mypy.

**Spec:** `docs/superpowers/specs/2026-03-21-meadow-simulation-architecture-design.md` §5.4, §8 Phase 3  
**User design input:** Leaf shape encoded as `number_of_lobes`, `lobe_aspect_ratio`, `lobe_length` — grass (1, ~20, ~15) vs maple (5-7, ~1.5, ~8).

---

## Task 1: TraitBundle with leaf/root/allocation traits + PlantBody

**Files:**
- Modify: `src/meadow/plant.py`
- Modify: `tests/test_plant.py`

- [ ] **Step 1: Write failing tests for new trait fields and PlantBody**

Append to `tests/test_plant.py`:

```python
from meadow.hex import Axial
from meadow.plant import PlantBody


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


class TestPlantBody:
    def test_home_in_root_and_leaf_sets(self):
        home = Axial(3, 3)
        body = PlantBody(home=home)
        assert home in body.root_hexes
        assert home in body.leaf_hexes

    def test_body_starts_single_hex(self):
        body = PlantBody(home=Axial(0, 0))
        assert len(body.root_hexes) == 1
        assert len(body.leaf_hexes) == 1


class TestPlantWithBody:
    def test_register_with_home_creates_body(self):
        pop = PlantPopulation()
        p = pop.register(home=Axial(2, 2))
        assert p.body is not None
        assert p.body.home == Axial(2, 2)

    def test_register_without_home_has_no_body(self):
        pop = PlantPopulation()
        p = pop.register()
        assert p.body is None

    def test_plant_reserves_start_at_zero(self):
        pop = PlantPopulation()
        p = pop.register(home=Axial(0, 0))
        assert p.moisture_reserve == 0.0
        assert p.nutrient_reserve == 0.0
        assert p.cellulose == 0.0
```

- [ ] **Step 2: Run tests to verify failures**

- [ ] **Step 3: Implement updated plant.py**

```python
# src/meadow/plant.py
"""Plant domain: identity, traits, body plan, and population registry.

Growth forms (grass, taproot, woody) are parameter-driven, not subclass-driven.
Leaf shape is encoded via number_of_lobes, lobe_aspect_ratio, and lobe_length
so that grass (1 narrow lobe) and maple (5-7 wide lobes) use the same model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from meadow.hex import Axial

_LOBE_SHAPE_FACTOR: float = 0.7


@dataclass
class TraitBundle:
    """Numeric traits governing plant behavior. All floats for continuous mutation."""

    # Leaf geometry
    number_of_lobes: float = 1.0
    lobe_aspect_ratio: float = 10.0
    lobe_length: float = 12.0

    # Root
    root_reach: float = 0.3

    # Allocation weights (relative; normalized at use)
    alloc_root: float = 0.25
    alloc_leaf: float = 0.25
    alloc_stem: float = 0.25
    alloc_reproduce: float = 0.25

    @property
    def effective_leaf_area(self) -> float:
        """Approximate single-leaf area in cm^2 from lobe geometry."""
        if self.number_of_lobes <= 0 or self.lobe_length <= 0:
            return 0.0
        lobe_width = self.lobe_length / max(self.lobe_aspect_ratio, 0.01)
        return self.number_of_lobes * self.lobe_length * lobe_width * _LOBE_SHAPE_FACTOR


@dataclass
class PlantBody:
    """Spatial footprint of a plant on the hex grid."""

    home: Axial
    root_hexes: set[Axial] = field(default=None)
    leaf_hexes: set[Axial] = field(default=None)

    def __post_init__(self):
        if self.root_hexes is None:
            self.root_hexes = {self.home}
        if self.leaf_hexes is None:
            self.leaf_hexes = {self.home}


@dataclass
class Plant:
    id: int
    traits: TraitBundle = field(default_factory=TraitBundle)
    body: PlantBody | None = None
    moisture_reserve: float = 0.0
    nutrient_reserve: float = 0.0
    cellulose: float = 0.0


class PlantPopulation:
    """Registry of living plants with deterministic iteration order."""

    def __init__(self) -> None:
        self._plants: dict[int, Plant] = {}
        self._next_id: int = 0

    def register(
        self,
        traits: TraitBundle | None = None,
        home: Axial | None = None,
    ) -> Plant:
        body = PlantBody(home=home) if home is not None else None
        plant = Plant(id=self._next_id, traits=traits or TraitBundle(), body=body)
        self._plants[self._next_id] = plant
        self._next_id += 1
        return plant

    def remove(self, plant_id: int) -> None:
        del self._plants[plant_id]

    def get(self, plant_id: int) -> Plant | None:
        return self._plants.get(plant_id)

    def __iter__(self):
        return iter(sorted(self._plants.values(), key=lambda p: p.id))

    def __len__(self) -> int:
        return len(self._plants)
```

- [ ] **Step 4: Run all plant tests**

Run: `uv run --extra dev pytest tests/test_plant.py -v`

- [ ] **Step 5: Lint and commit**

```
git add src/meadow/plant.py tests/test_plant.py
git commit -m "feat(plant): add leaf/root/allocation traits, PlantBody, and reserves"
```

---

## Task 2: Metabolism pure functions

**Files:**
- Create: `src/meadow/metabolism.py`
- Create: `tests/test_metabolism.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_metabolism.py
"""Tests for metabolism pure functions."""

import pytest

from meadow.metabolism import allocate_cellulose, compute_photosynthesis
from meadow.plant import TraitBundle

LEAF_AREA_UNIT = 100.0


class TestPhotosynthesis:
    def test_limited_by_moisture(self):
        result = compute_photosynthesis(
            moisture=0.5, nutrients=10.0, light=1.0, leaf_area=200.0
        )
        assert result == pytest.approx(0.5)

    def test_limited_by_nutrients(self):
        result = compute_photosynthesis(
            moisture=10.0, nutrients=0.3, light=1.0, leaf_area=200.0
        )
        assert result == pytest.approx(0.3)

    def test_limited_by_effective_light(self):
        result = compute_photosynthesis(
            moisture=10.0, nutrients=10.0, light=1.0, leaf_area=50.0
        )
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
```

- [ ] **Step 2: Implement metabolism.py**

```python
# src/meadow/metabolism.py
"""Pure functions for plant metabolism.

Photosynthesis: Liebig's law — output limited by the scarcest input.
Allocation: split cellulose by normalized trait weights.

Physics simplifications (v1):
- 100 cm^2 of leaf area captures all light from one hex (LEAF_AREA_UNIT).
- Moisture and nutrients consumed 1:1 with cellulose produced.
"""

from __future__ import annotations

from meadow.plant import TraitBundle

LEAF_AREA_UNIT: float = 100.0


def compute_photosynthesis(
    moisture: float, nutrients: float, light: float, leaf_area: float
) -> float:
    """Cellulose produced from available resources (Liebig's law)."""
    effective_light = light * leaf_area / LEAF_AREA_UNIT
    return min(moisture, nutrients, effective_light)


def allocate_cellulose(cellulose: float, traits: TraitBundle) -> dict[str, float]:
    """Split cellulose into growth categories by trait weights."""
    total_w = traits.alloc_root + traits.alloc_leaf + traits.alloc_stem + traits.alloc_reproduce
    if total_w <= 0 or cellulose <= 0:
        return {"root": 0.0, "leaf": 0.0, "stem": 0.0, "reproduce": 0.0}
    return {
        "root": cellulose * traits.alloc_root / total_w,
        "leaf": cellulose * traits.alloc_leaf / total_w,
        "stem": cellulose * traits.alloc_stem / total_w,
        "reproduce": cellulose * traits.alloc_reproduce / total_w,
    }
```

- [ ] **Step 3: Run tests, lint, commit**

```
git add src/meadow/metabolism.py tests/test_metabolism.py
git commit -m "feat(metabolism): add photosynthesis and allocation pure functions"
```

---

## Task 3: UptakePhase — plants pull moisture/nutrients from root tiles

**Files:**
- Create: `src/meadow/uptake.py`
- Create: `tests/test_uptake.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_uptake.py
"""Tests for the uptake phase."""

import pytest

from meadow.hex import Axial, HexGrid
from meadow.phases import PhaseName
from meadow.plant import PlantPopulation, TraitBundle
from meadow.uptake import UptakePhase
from meadow.world import TurnContext
from meadow.world_state import WorldState


class TestUptakePhase:
    def test_name_is_uptake(self):
        pop = PlantPopulation()
        assert UptakePhase(pop).name == PhaseName.UPTAKE

    def test_plant_absorbs_moisture_and_nutrients(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        pop = PlantPopulation()
        home = Axial(2, 2)
        plant = pop.register(home=home, traits=TraitBundle(root_reach=0.5))
        ws.moisture[ws._idx(home)] = 10.0
        ws.nutrients[ws._idx(home)] = 6.0

        UptakePhase(pop).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert ws.moisture_at(home) == pytest.approx(5.0)
        assert ws.nutrients_at(home) == pytest.approx(3.0)
        assert plant.moisture_reserve == pytest.approx(5.0)
        assert plant.nutrient_reserve == pytest.approx(3.0)

    def test_no_body_plant_skipped(self):
        ws = WorldState(HexGrid(3, 3))
        pop = PlantPopulation()
        pop.register()
        UptakePhase(pop).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

    def test_reserves_accumulate_across_ticks(self):
        grid = HexGrid(3, 3)
        ws = WorldState(grid)
        pop = PlantPopulation()
        home = Axial(1, 1)
        plant = pop.register(home=home, traits=TraitBundle(root_reach=0.5))

        for tick in range(3):
            ws.moisture[ws._idx(home)] = 4.0
            ws.nutrients[ws._idx(home)] = 2.0
            UptakePhase(pop).execute(ws, ws, TurnContext(tick=tick, weather_seed=0))

        assert plant.moisture_reserve == pytest.approx(6.0)
        assert plant.nutrient_reserve == pytest.approx(3.0)

    def test_result_has_diagnostics(self):
        ws = WorldState(HexGrid(3, 3))
        pop = PlantPopulation()
        pop.register(home=Axial(1, 1))
        ws.moisture[:] = 5.0
        ws.nutrients[:] = 3.0
        result = UptakePhase(pop).execute(ws, ws, TurnContext(tick=0, weather_seed=0))
        assert result.phase_name == "UPTAKE"
        assert result.diagnostics is not None
```

- [ ] **Step 2: Implement uptake.py**

```python
# src/meadow/uptake.py
"""Uptake phase: plants absorb moisture and nutrients from root tiles.

Each root hex contributes: available_resource * root_reach.
Absorbed amounts are deducted from the tile and added to plant reserves.
"""

from __future__ import annotations

from meadow.hex import Axial
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

    def execute(
        self, view: WorldView, mutator: WorldMutator, ctx: TurnContext
    ) -> PhaseResult:
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
```

- [ ] **Step 3: Run tests, lint, commit**

```
git add src/meadow/uptake.py tests/test_uptake.py
git commit -m "feat(uptake): add UptakePhase — plants absorb from root tiles"
```

---

## Task 4: GrowthPhase — photosynthesis + allocation (stub actions)

**Files:**
- Create: `src/meadow/growth.py`
- Create: `tests/test_growth.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_growth.py
"""Tests for the growth phase."""

import pytest

from meadow.hex import Axial, HexGrid
from meadow.growth import GrowthPhase
from meadow.phases import PhaseName
from meadow.plant import PlantPopulation, TraitBundle
from meadow.world import TurnContext
from meadow.world_state import WorldState


class TestGrowthPhase:
    def test_name_is_growth(self):
        pop = PlantPopulation()
        assert GrowthPhase(pop).name == PhaseName.GROWTH

    def test_plant_produces_cellulose(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        pop = PlantPopulation()
        home = Axial(2, 2)
        plant = pop.register(home=home)
        plant.moisture_reserve = 5.0
        plant.nutrient_reserve = 5.0
        ws.light[ws._idx(home)] = 1.0

        GrowthPhase(pop).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert plant.cellulose > 0.0

    def test_photosynthesis_consumes_reserves(self):
        grid = HexGrid(3, 3)
        ws = WorldState(grid)
        pop = PlantPopulation()
        home = Axial(1, 1)
        plant = pop.register(home=home)
        plant.moisture_reserve = 2.0
        plant.nutrient_reserve = 2.0
        ws.light[ws._idx(home)] = 1.0

        before_m = plant.moisture_reserve
        before_n = plant.nutrient_reserve
        GrowthPhase(pop).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert plant.moisture_reserve < before_m
        assert plant.nutrient_reserve < before_n

    def test_no_light_no_cellulose(self):
        grid = HexGrid(3, 3)
        ws = WorldState(grid)
        pop = PlantPopulation()
        home = Axial(1, 1)
        plant = pop.register(home=home)
        plant.moisture_reserve = 10.0
        plant.nutrient_reserve = 10.0

        GrowthPhase(pop).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert plant.cellulose == 0.0

    def test_no_body_plant_skipped(self):
        ws = WorldState(HexGrid(3, 3))
        pop = PlantPopulation()
        pop.register()
        GrowthPhase(pop).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

    def test_larger_leaf_area_produces_more(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        ws.light[:] = 1.0

        pop_small = PlantPopulation()
        small = pop_small.register(
            home=Axial(2, 2),
            traits=TraitBundle(number_of_lobes=1.0, lobe_aspect_ratio=20.0, lobe_length=5.0),
        )
        small.moisture_reserve = 50.0
        small.nutrient_reserve = 50.0

        pop_big = PlantPopulation()
        big = pop_big.register(
            home=Axial(2, 2),
            traits=TraitBundle(number_of_lobes=5.0, lobe_aspect_ratio=1.5, lobe_length=8.0),
        )
        big.moisture_reserve = 50.0
        big.nutrient_reserve = 50.0

        GrowthPhase(pop_small).execute(ws, ws, TurnContext(tick=0, weather_seed=0))
        GrowthPhase(pop_big).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert big.cellulose > small.cellulose

    def test_result_has_diagnostics(self):
        ws = WorldState(HexGrid(3, 3))
        pop = PlantPopulation()
        result = GrowthPhase(pop).execute(ws, ws, TurnContext(tick=0, weather_seed=0))
        assert result.phase_name == "GROWTH"
```

- [ ] **Step 2: Implement growth.py**

```python
# src/meadow/growth.py
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
        self, view: WorldView, mutator: WorldMutator, ctx: TurnContext
    ) -> PhaseResult:
        total_cellulose = 0.0
        for plant in self._pop:
            if plant.body is None:
                continue
            total_light = sum(view.light_at(h) for h in plant.body.leaf_hexes)
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
            # Allocation computed for future use; Phase 4 will act on it
            allocate_cellulose(produced, plant.traits)
        return PhaseResult(
            phase_name=self.name.name,
            diagnostics={"cellulose_produced": total_cellulose},
        )
```

- [ ] **Step 3: Run tests, lint, commit**

```
git add src/meadow/growth.py tests/test_growth.py
git commit -m "feat(growth): add GrowthPhase with photosynthesis and allocation"
```

---

## Task 5: Phase 3 integration test

**Files:**
- Create: `tests/test_integration_phase3.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration_phase3.py
"""Phase 3 integration: full tick with a real plant on a real grid.

Key invariants:
- Plant accumulates cellulose after one tick with moisture, nutrients, and light
- Resources deducted from tiles match what the plant absorbed
- Grass vs maple leaf traits produce different cellulose amounts
"""

import pytest

from meadow.flow import FlowPhase
from meadow.growth import GrowthPhase
from meadow.hex import Axial, HexGrid
from meadow.light import LightPhase
from meadow.phases import NoOpPhase, PhaseName
from meadow.plant import PlantPopulation, TraitBundle
from meadow.sim import TurnPipeline
from meadow.uptake import UptakePhase
from meadow.weather import WeatherPhase
from meadow.world import TurnContext
from meadow.world_state import WorldState


def _build_phase3_pipeline(
    pop: PlantPopulation, rainfall: float = 2.0
) -> TurnPipeline:
    return TurnPipeline({
        PhaseName.WEATHER: WeatherPhase(rainfall_per_tick=rainfall),
        PhaseName.FLOW: FlowPhase(),
        PhaseName.LIGHT: LightPhase(base_sunlight=1.0),
        PhaseName.UPTAKE: UptakePhase(pop),
        PhaseName.DEPLETION: NoOpPhase(PhaseName.DEPLETION),
        PhaseName.GROWTH: GrowthPhase(pop),
    })


class TestPhase3Integration:
    def test_plant_gains_cellulose_after_tick(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        pop = PlantPopulation()
        plant = pop.register(home=Axial(2, 2))
        pipeline = _build_phase3_pipeline(pop)

        pipeline.run_tick(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert plant.cellulose > 0.0

    def test_tile_moisture_reduced_by_uptake(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        pop = PlantPopulation()
        home = Axial(2, 2)
        pop.register(home=home, traits=TraitBundle(root_reach=0.5))
        pipeline = _build_phase3_pipeline(pop, rainfall=4.0)

        pipeline.run_tick(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert ws.moisture_at(home) < 4.0

    def test_grass_vs_maple_cellulose_difference(self):
        grid = HexGrid(5, 5)

        ws_grass = WorldState(grid)
        pop_grass = PlantPopulation()
        grass = pop_grass.register(
            home=Axial(2, 2),
            traits=TraitBundle(
                number_of_lobes=1.0, lobe_aspect_ratio=20.0, lobe_length=15.0,
                root_reach=0.5,
            ),
        )
        pipe_grass = _build_phase3_pipeline(pop_grass, rainfall=10.0)
        pipe_grass.run_tick(ws_grass, ws_grass, TurnContext(tick=0, weather_seed=0))

        ws_maple = WorldState(grid)
        pop_maple = PlantPopulation()
        maple = pop_maple.register(
            home=Axial(2, 2),
            traits=TraitBundle(
                number_of_lobes=5.0, lobe_aspect_ratio=1.5, lobe_length=8.0,
                root_reach=0.5,
            ),
        )
        pipe_maple = _build_phase3_pipeline(pop_maple, rainfall=10.0)
        pipe_maple.run_tick(ws_maple, ws_maple, TurnContext(tick=0, weather_seed=0))

        assert maple.cellulose > grass.cellulose

    def test_five_ticks_cellulose_grows(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        pop = PlantPopulation()
        plant = pop.register(home=Axial(2, 2))
        pipeline = _build_phase3_pipeline(pop)

        for tick in range(5):
            pipeline.run_tick(ws, ws, TurnContext(tick=tick, weather_seed=tick))

        assert plant.cellulose > 0.0

    def test_full_tick_completes_with_6_results(self):
        ws = WorldState(HexGrid(5, 5))
        pop = PlantPopulation()
        pop.register(home=Axial(2, 2))
        pipeline = _build_phase3_pipeline(pop)
        results = pipeline.run_tick(ws, ws, TurnContext(tick=0, weather_seed=0))
        assert len(results) == 6
```

- [ ] **Step 2: Run integration tests and full suite**

Run: `uv run --extra dev pytest tests/test_integration_phase3.py -v`
Run: `uv run --extra dev pytest tests/ -v`
Run: `uv run --extra dev ruff check src/meadow/ tests/`
Run: `uv run --extra dev mypy src/meadow/`

- [ ] **Step 3: Commit**

```
git add tests/test_integration_phase3.py
git commit -m "test: add Phase 3 integration — plant gains cellulose, grass vs maple"
```
