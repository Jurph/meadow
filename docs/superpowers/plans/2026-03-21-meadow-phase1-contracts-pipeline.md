# Meadow Phase 1: Contracts + Empty Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish typed contracts (protocols), hex topology, and a turn pipeline with no-op phases — the foundation that all later simulation code plugs into.

**Architecture:** Two-layer domain split (world engine vs plant domain) connected through narrow protocol interfaces. Orchestration lives in `TurnPipeline`; pure logic lives in `hex` module. All modules exist in `src/meadow/`. Phase 1 uses no numpy — that arrives in Phase 2 when field arrays appear.

**Tech Stack:** Python 3.11+, pytest, ruff, mypy. No new runtime dependencies in Phase 1.

**Spec:** `docs/superpowers/specs/2026-03-21-meadow-simulation-architecture-design.md`

---

## Chunk 1: Hex coordinates and topology

### Task 1: Axial coordinate type and validation

**Files:**
- Create: `src/meadow/hex.py`
- Create: `tests/test_hex.py`

- [ ] **Step 1: Write failing tests for Axial creation and equality**

```python
# tests/test_hex.py
"""Tests for hex coordinate system and topology."""

from meadow.hex import Axial


class TestAxial:
    def test_create_and_unpack(self):
        h = Axial(3, 5)
        assert h.q == 3
        assert h.r == 5

    def test_equality(self):
        assert Axial(1, 2) == Axial(1, 2)
        assert Axial(1, 2) != Axial(2, 1)

    def test_usable_as_dict_key(self):
        d = {Axial(0, 0): "origin"}
        assert d[Axial(0, 0)] == "origin"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --extra dev pytest tests/test_hex.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'meadow.hex'` or `ImportError`

- [ ] **Step 3: Implement Axial**

```python
# src/meadow/hex.py
"""Hex coordinate system, topology, and footprint math.

Uses axial coordinates (q, r) with pointy-top orientation.
A rectangular grid patch maps q in [0, width) and r in [0, height).
"""

from __future__ import annotations

from typing import NamedTuple


class Axial(NamedTuple):
    """An axial hex coordinate (q, r)."""

    q: int
    r: int
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --extra dev pytest tests/test_hex.py::TestAxial -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```
git add src/meadow/hex.py tests/test_hex.py
git commit -m "feat(hex): add Axial coordinate type"
```

---

### Task 2: Hex distance and neighbor functions

**Files:**
- Modify: `src/meadow/hex.py`
- Modify: `tests/test_hex.py`

- [ ] **Step 1: Write failing tests for distance and neighbors**

Append to `tests/test_hex.py`:

```python
from meadow.hex import Axial, distance, neighbors


class TestDistance:
    def test_distance_to_self_is_zero(self):
        assert distance(Axial(3, 4), Axial(3, 4)) == 0

    def test_distance_to_neighbor_is_one(self):
        origin = Axial(0, 0)
        for n in neighbors(origin):
            assert distance(origin, n) == 1

    def test_distance_symmetry(self):
        a, b = Axial(0, 0), Axial(3, -2)
        assert distance(a, b) == distance(b, a)

    def test_known_distance(self):
        assert distance(Axial(0, 0), Axial(2, -1)) == 2


class TestNeighbors:
    def test_origin_has_six_neighbors(self):
        assert len(neighbors(Axial(0, 0))) == 6

    def test_neighbors_are_all_distinct(self):
        ns = neighbors(Axial(5, 5))
        assert len(set(ns)) == 6

    def test_neighbors_are_distance_one(self):
        center = Axial(3, 3)
        for n in neighbors(center):
            assert distance(center, n) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --extra dev pytest tests/test_hex.py -v`
Expected: FAIL — `ImportError: cannot import name 'distance'`

- [ ] **Step 3: Implement distance and neighbors**

Add to `src/meadow/hex.py`:

```python
DIRECTIONS: tuple[Axial, ...] = (
    Axial(+1, 0),
    Axial(+1, -1),
    Axial(0, -1),
    Axial(-1, 0),
    Axial(-1, +1),
    Axial(0, +1),
)


def neighbors(h: Axial) -> list[Axial]:
    """Return the six axial neighbors of *h*."""
    return [Axial(h.q + d.q, h.r + d.r) for d in DIRECTIONS]


def distance(a: Axial, b: Axial) -> int:
    """Hex distance between two axial coordinates."""
    dq = a.q - b.q
    dr = a.r - b.r
    return (abs(dq) + abs(dq + dr) + abs(dr)) // 2
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --extra dev pytest tests/test_hex.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```
git add src/meadow/hex.py tests/test_hex.py
git commit -m "feat(hex): add distance and neighbor functions"
```

---

### Task 3: Disk footprint and HexGrid with bounds

**Files:**
- Modify: `src/meadow/hex.py`
- Modify: `tests/test_hex.py`

- [ ] **Step 1: Write failing tests for disk and HexGrid**

Append to `tests/test_hex.py`:

```python
import pytest

from meadow.hex import Axial, HexGrid, disk


class TestDisk:
    def test_disk_radius_zero_is_single_hex(self):
        assert disk(Axial(5, 5), 0) == {Axial(5, 5)}

    def test_disk_radius_one_has_seven_hexes(self):
        assert len(disk(Axial(0, 0), 1)) == 7

    def test_disk_radius_two_has_nineteen_hexes(self):
        assert len(disk(Axial(0, 0), 2)) == 19

    def test_disk_negative_radius_is_empty(self):
        assert disk(Axial(0, 0), -1) == set()


class TestHexGrid:
    def test_grid_size(self):
        g = HexGrid(10, 10)
        assert len(g) == 100

    def test_in_bounds(self):
        g = HexGrid(5, 5)
        assert g.in_bounds(Axial(0, 0))
        assert g.in_bounds(Axial(4, 4))
        assert not g.in_bounds(Axial(-1, 0))
        assert not g.in_bounds(Axial(5, 0))

    def test_iteration_yields_all_coords(self):
        g = HexGrid(3, 3)
        coords = list(g)
        assert len(coords) == 9
        assert Axial(0, 0) in coords
        assert Axial(2, 2) in coords

    def test_neighbors_in_bounds_filters_edges(self):
        g = HexGrid(5, 5)
        corner_neighbors = g.neighbors_in_bounds(Axial(0, 0))
        assert all(g.in_bounds(n) for n in corner_neighbors)
        assert len(corner_neighbors) < 6

    def test_invalid_dimensions_rejected(self):
        with pytest.raises(ValueError):
            HexGrid(0, 5)
        with pytest.raises(ValueError):
            HexGrid(5, -1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --extra dev pytest tests/test_hex.py -v`
Expected: FAIL — `ImportError: cannot import name 'disk'`

- [ ] **Step 3: Implement disk and HexGrid**

Add to `src/meadow/hex.py`:

```python
def disk(center: Axial, radius: int) -> set[Axial]:
    """Return the set of hexes within *radius* steps of *center*."""
    if radius < 0:
        return set()
    results: set[Axial] = set()
    for q in range(center.q - radius, center.q + radius + 1):
        for r in range(center.r - radius, center.r + radius + 1):
            candidate = Axial(q, r)
            if distance(center, candidate) <= radius:
                results.add(candidate)
    return results


class HexGrid:
    """A rectangular patch in axial space: q in [0, width), r in [0, height)."""

    def __init__(self, width: int, height: int) -> None:
        if width < 1 or height < 1:
            raise ValueError(f"Grid dimensions must be positive, got {width}x{height}")
        self.width = width
        self.height = height

    def in_bounds(self, h: Axial) -> bool:
        return 0 <= h.q < self.width and 0 <= h.r < self.height

    def neighbors_in_bounds(self, h: Axial) -> list[Axial]:
        return [n for n in neighbors(h) if self.in_bounds(n)]

    def __iter__(self):
        for q in range(self.width):
            for r in range(self.height):
                yield Axial(q, r)

    def __len__(self) -> int:
        return self.width * self.height
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --extra dev pytest tests/test_hex.py -v`
Expected: all passed

- [ ] **Step 5: Run linters and type checker**

Run: `uv run --extra dev ruff check src/meadow/hex.py tests/test_hex.py`
Run: `uv run --extra dev mypy src/meadow/hex.py`
Expected: no errors

- [ ] **Step 6: Commit**

```
git add src/meadow/hex.py tests/test_hex.py
git commit -m "feat(hex): add disk footprint and HexGrid with bounds checking"
```

---

## Chunk 2: World and phase contracts

### Task 4: World contracts — WorldView, WorldMutator, TurnContext, PhaseResult

**Files:**
- Create: `src/meadow/world.py`
- Create: `tests/test_world.py`

- [ ] **Step 1: Write failing tests for contract types**

```python
# tests/test_world.py
"""Tests for world contracts and value types."""

from meadow.hex import Axial
from meadow.world import (
    SIM_API_VERSION,
    PhaseResult,
    TurnContext,
    WorldMutator,
    WorldView,
)


class TestValueTypes:
    def test_turn_context_is_frozen(self):
        ctx = TurnContext(tick=0, weather_seed=42)
        assert ctx.tick == 0
        assert ctx.weather_seed == 42

    def test_phase_result_stores_diagnostics(self):
        r = PhaseResult(phase_name="FLOW", diagnostics={"total_water": 100.0})
        assert r.phase_name == "FLOW"
        assert r.diagnostics["total_water"] == 100.0

    def test_phase_result_diagnostics_default_none(self):
        r = PhaseResult(phase_name="LIGHT")
        assert r.diagnostics is None


class TestSIMAPIVersion:
    def test_version_is_positive_integer(self):
        assert isinstance(SIM_API_VERSION, int)
        assert SIM_API_VERSION >= 1


class TestProtocolsAreRuntimeCheckable:
    """Verify protocols can be used with isinstance at runtime."""

    def test_world_view_is_protocol(self):
        class FakeView:
            def moisture_at(self, h: Axial) -> float:
                return 0.0

            def nutrients_at(self, h: Axial) -> float:
                return 0.0

            def light_at(self, h: Axial) -> float:
                return 0.0

            def occupant_id_at(self, h: Axial) -> int | None:
                return None

        assert isinstance(FakeView(), WorldView)

    def test_world_mutator_is_protocol(self):
        class FakeMutator:
            def apply_flow_delta(
                self, h: Axial, moisture_delta: float, nutrient_delta: float
            ) -> None:
                pass

            def set_light(self, h: Axial, value: float) -> None:
                pass

            def set_occupant(self, h: Axial, plant_id: int | None) -> None:
                pass

        assert isinstance(FakeMutator(), WorldMutator)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --extra dev pytest tests/test_world.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'meadow.world'`

- [ ] **Step 3: Implement world contracts**

```python
# src/meadow/world.py
"""World-layer contracts: read/write protocols, turn context, phase results.

Plant code interacts with the world ONLY through WorldView (reads)
and WorldMutator (writes). Implementations live elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from meadow.hex import Axial

SIM_API_VERSION: int = 1


@dataclass(frozen=True)
class TurnContext:
    """Read-only snapshot passed to every phase in a tick."""

    tick: int
    weather_seed: int


@dataclass
class PhaseResult:
    """Returned by each phase for diagnostics and testing."""

    phase_name: str
    diagnostics: dict[str, float] | None = None


@runtime_checkable
class WorldView(Protocol):
    """Read surface exposed to plants and phases."""

    def moisture_at(self, h: Axial) -> float: ...
    def nutrients_at(self, h: Axial) -> float: ...
    def light_at(self, h: Axial) -> float: ...
    def occupant_id_at(self, h: Axial) -> int | None: ...


@runtime_checkable
class WorldMutator(Protocol):
    """Write surface scoped to phase execution."""

    def apply_flow_delta(self, h: Axial, moisture_delta: float, nutrient_delta: float) -> None: ...
    def set_light(self, h: Axial, value: float) -> None: ...
    def set_occupant(self, h: Axial, plant_id: int | None) -> None: ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --extra dev pytest tests/test_world.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```
git add src/meadow/world.py tests/test_world.py
git commit -m "feat(world): add WorldView/WorldMutator protocols and turn value types"
```

---

### Task 5: Phase contract and NoOpPhase

**Files:**
- Create: `src/meadow/phases.py`
- Create: `tests/test_phases.py`

- [ ] **Step 1: Write failing tests for Phase protocol and NoOpPhase**

```python
# tests/test_phases.py
"""Tests for phase contracts and ordering."""

from meadow.hex import Axial
from meadow.phases import PHASE_ORDER, NoOpPhase, Phase, PhaseName
from meadow.world import PhaseResult, TurnContext, WorldMutator, WorldView


class TestPhaseName:
    def test_phase_order_has_six_phases(self):
        assert len(PHASE_ORDER) == 6

    def test_phase_order_matches_vision_doc_sequence(self):
        names = [p.name for p in PHASE_ORDER]
        assert names == ["WEATHER", "FLOW", "LIGHT", "UPTAKE", "DEPLETION", "GROWTH"]


class TestNoOpPhase:
    def test_satisfies_phase_protocol(self):
        phase = NoOpPhase(PhaseName.WEATHER)
        assert isinstance(phase, Phase)

    def test_execute_returns_phase_result(self):
        phase = NoOpPhase(PhaseName.FLOW)

        class StubView:
            def moisture_at(self, h: Axial) -> float: return 0.0
            def nutrients_at(self, h: Axial) -> float: return 0.0
            def light_at(self, h: Axial) -> float: return 0.0
            def occupant_id_at(self, h: Axial) -> int | None: return None

        class StubMutator:
            def apply_flow_delta(self, h, md, nd): pass
            def set_light(self, h, v): pass
            def set_occupant(self, h, pid): pass

        ctx = TurnContext(tick=0, weather_seed=1)
        result = phase.execute(StubView(), StubMutator(), ctx)
        assert isinstance(result, PhaseResult)
        assert result.phase_name == "FLOW"

    def test_name_property_returns_assigned_name(self):
        phase = NoOpPhase(PhaseName.LIGHT)
        assert phase.name == PhaseName.LIGHT
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --extra dev pytest tests/test_phases.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'meadow.phases'`

- [ ] **Step 3: Implement phases module**

```python
# src/meadow/phases.py
"""Phase contracts and ordering for the turn pipeline.

Each named phase executes once per tick in PHASE_ORDER sequence.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Protocol, runtime_checkable

from meadow.world import PhaseResult, TurnContext, WorldMutator, WorldView


class PhaseName(Enum):
    WEATHER = auto()
    FLOW = auto()
    LIGHT = auto()
    UPTAKE = auto()
    DEPLETION = auto()
    GROWTH = auto()


PHASE_ORDER: tuple[PhaseName, ...] = (
    PhaseName.WEATHER,
    PhaseName.FLOW,
    PhaseName.LIGHT,
    PhaseName.UPTAKE,
    PhaseName.DEPLETION,
    PhaseName.GROWTH,
)


@runtime_checkable
class Phase(Protocol):
    @property
    def name(self) -> PhaseName: ...

    def execute(
        self, view: WorldView, mutator: WorldMutator, ctx: TurnContext
    ) -> PhaseResult: ...


class NoOpPhase:
    """Stub phase that does nothing — placeholder for Phase 1."""

    def __init__(self, phase_name: PhaseName) -> None:
        self._name = phase_name

    @property
    def name(self) -> PhaseName:
        return self._name

    def execute(
        self, view: WorldView, mutator: WorldMutator, ctx: TurnContext
    ) -> PhaseResult:
        return PhaseResult(phase_name=self._name.name)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --extra dev pytest tests/test_phases.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```
git add src/meadow/phases.py tests/test_phases.py
git commit -m "feat(phases): add Phase protocol, PhaseName enum, PHASE_ORDER, and NoOpPhase"
```

---

## Chunk 3: Plant stubs, pipeline, and integration

### Task 6: Plant and PlantPopulation stubs

**Files:**
- Create: `src/meadow/plant.py`
- Create: `tests/test_plant.py`

- [ ] **Step 1: Write failing tests for Plant and PlantPopulation**

```python
# tests/test_plant.py
"""Tests for plant domain stubs."""

import pytest

from meadow.plant import Plant, PlantPopulation, TraitBundle


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --extra dev pytest tests/test_plant.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'meadow.plant'`

- [ ] **Step 3: Implement plant module**

```python
# src/meadow/plant.py
"""Plant domain: identity, traits, and population registry.

Growth forms (grass, taproot, woody) are parameter-driven, not subclass-driven.
Body plan (root/leaf/stem hex sets) will be added in Phase 3.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TraitBundle:
    """Numeric traits with mean/variance — placeholder for Phase 1.

    Will hold allocation weights, mutation rates, etc.
    """


@dataclass
class Plant:
    id: int
    traits: TraitBundle = field(default_factory=TraitBundle)


class PlantPopulation:
    """Registry of living plants with deterministic iteration order."""

    def __init__(self) -> None:
        self._plants: dict[int, Plant] = {}
        self._next_id: int = 0

    def register(self, traits: TraitBundle | None = None) -> Plant:
        plant = Plant(id=self._next_id, traits=traits or TraitBundle())
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --extra dev pytest tests/test_plant.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```
git add src/meadow/plant.py tests/test_plant.py
git commit -m "feat(plant): add Plant, TraitBundle, and PlantPopulation stubs"
```

---

### Task 7: TurnPipeline orchestrator

**Files:**
- Create: `src/meadow/sim.py`
- Create: `tests/test_sim.py`

- [ ] **Step 1: Write failing tests for TurnPipeline**

```python
# tests/test_sim.py
"""Tests for the turn pipeline orchestrator."""

import pytest

from meadow.hex import Axial
from meadow.phases import PHASE_ORDER, NoOpPhase, PhaseName
from meadow.sim import TurnPipeline
from meadow.world import TurnContext


class StubView:
    def moisture_at(self, h: Axial) -> float: return 0.0
    def nutrients_at(self, h: Axial) -> float: return 0.0
    def light_at(self, h: Axial) -> float: return 0.0
    def occupant_id_at(self, h: Axial) -> int | None: return None


class StubMutator:
    def apply_flow_delta(self, h, md, nd): pass
    def set_light(self, h, v): pass
    def set_occupant(self, h, pid): pass


def _all_noop_phases() -> dict[PhaseName, NoOpPhase]:
    return {name: NoOpPhase(name) for name in PhaseName}


class TestTurnPipeline:
    def test_missing_phase_raises(self):
        incomplete = {PhaseName.WEATHER: NoOpPhase(PhaseName.WEATHER)}
        with pytest.raises(ValueError, match="Missing phases"):
            TurnPipeline(incomplete)

    def test_run_tick_returns_one_result_per_phase(self):
        pipeline = TurnPipeline(_all_noop_phases())
        ctx = TurnContext(tick=0, weather_seed=1)
        results = pipeline.run_tick(StubView(), StubMutator(), ctx)
        assert len(results) == len(PHASE_ORDER)

    def test_run_tick_executes_phases_in_order(self):
        pipeline = TurnPipeline(_all_noop_phases())
        ctx = TurnContext(tick=0, weather_seed=1)
        results = pipeline.run_tick(StubView(), StubMutator(), ctx)
        result_names = [r.phase_name for r in results]
        expected_names = [p.name for p in PHASE_ORDER]
        assert result_names == expected_names

    def test_tick_index_passes_through(self):
        pipeline = TurnPipeline(_all_noop_phases())
        ctx = TurnContext(tick=42, weather_seed=7)
        results = pipeline.run_tick(StubView(), StubMutator(), ctx)
        assert len(results) == 6
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --extra dev pytest tests/test_sim.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'meadow.sim'`

- [ ] **Step 3: Implement TurnPipeline**

```python
# src/meadow/sim.py
"""Turn pipeline: orchestrates phases in fixed order.

No physics here — just sequencing and validation.
"""

from __future__ import annotations

from meadow.phases import PHASE_ORDER, Phase, PhaseName
from meadow.world import PhaseResult, TurnContext, WorldMutator, WorldView


class TurnPipeline:
    """Executes registered phases in PHASE_ORDER sequence."""

    def __init__(self, phases: dict[PhaseName, Phase]) -> None:
        missing = set(PHASE_ORDER) - set(phases.keys())
        if missing:
            raise ValueError(f"Missing phases: {missing}")
        self._phases = phases

    def run_tick(
        self, view: WorldView, mutator: WorldMutator, ctx: TurnContext
    ) -> list[PhaseResult]:
        results: list[PhaseResult] = []
        for phase_name in PHASE_ORDER:
            result = self._phases[phase_name].execute(view, mutator, ctx)
            results.append(result)
        return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --extra dev pytest tests/test_sim.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```
git add src/meadow/sim.py tests/test_sim.py
git commit -m "feat(sim): add TurnPipeline orchestrator with phase ordering"
```

---

### Task 8: Full linter/type-check pass and integration test

**Files:**
- Modify: `tests/test_sim.py` (add integration test)

- [ ] **Step 1: Write integration test — one tick on a 3×3 grid with all stubs**

Append to `tests/test_sim.py`:

```python
from meadow.hex import HexGrid


class TestIntegration:
    """Contract-level integration: one full tick on a toy grid, all stubs."""

    def test_one_tick_on_3x3_grid_completes(self):
        grid = HexGrid(3, 3)
        pipeline = TurnPipeline(_all_noop_phases())
        ctx = TurnContext(tick=0, weather_seed=0)

        view = StubView()
        mutator = StubMutator()
        results = pipeline.run_tick(view, mutator, ctx)

        assert len(results) == len(PHASE_ORDER)
        for result in results:
            assert result.phase_name in {p.name for p in PhaseName}
            assert result.diagnostics is None

    def test_multiple_ticks_increment(self):
        pipeline = TurnPipeline(_all_noop_phases())
        view = StubView()
        mutator = StubMutator()

        for tick in range(5):
            ctx = TurnContext(tick=tick, weather_seed=tick)
            results = pipeline.run_tick(view, mutator, ctx)
            assert len(results) == len(PHASE_ORDER)
```

- [ ] **Step 2: Run the full test suite**

Run: `uv run --extra dev pytest tests/ -v`
Expected: all tests pass (including existing smoke/scaffold tests)

- [ ] **Step 3: Run ruff and mypy on all new code**

Run: `uv run --extra dev ruff check src/meadow/ tests/`
Run: `uv run --extra dev ruff format --check src/meadow/ tests/`
Run: `uv run --extra dev mypy src/meadow/`
Expected: no errors

Fix any issues found.

- [ ] **Step 4: Commit**

```
git add tests/test_sim.py
git commit -m "test(sim): add integration test — full tick on 3x3 grid with stubs"
```

- [ ] **Step 5: Final verification**

Run: `uv run --extra dev pytest tests/ -v --tb=short`
Expected: all green, including `test_smoke`, `test_repo_scaffold`, `test_uv_workflow`, and all new tests.
