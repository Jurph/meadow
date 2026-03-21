# Meadow Phase 2: World Fields + Flow + Light — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put numpy arrays behind WorldView/WorldMutator, implement weather (rainfall), simplified slope-driven flow with mass-conservation invariants, and uniform sunlight. Uptake/depletion/growth stay as NoOps until Phase 3 adds plants with metabolism.

**Architecture:** `WorldState` is the single concrete implementation of both `WorldView` and `WorldMutator`, owning flat numpy arrays indexed by `(q * height + r)`. Each real phase (Weather, Flow, Light) is a standalone class satisfying the `Phase` protocol. Flow uses simultaneous delta application for conservation.

**Tech Stack:** Python 3.11+, numpy, pytest, ruff, mypy.

**Spec:** `docs/superpowers/specs/2026-03-21-meadow-simulation-architecture-design.md`  
**Depends on:** Phase 1 contracts (hex, world, phases, sim modules all passing)

---

## Chunk 1: Numpy dependency + WorldState

### Task 1: Add numpy to project dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add numpy to dependencies**

In `pyproject.toml`, change:
```
dependencies = []
```
to:
```
dependencies = ["numpy>=2.0"]
```

- [ ] **Step 2: Sync the lockfile**

Run: `uv lock`
Run: `uv sync --extra dev`

- [ ] **Step 3: Verify numpy imports**

Run: `uv run python -c "import numpy; print(numpy.__version__)"`

- [ ] **Step 4: Commit**

```
git add pyproject.toml uv.lock
git commit -m "build: add numpy as core dependency"
```

---

### Task 2: WorldState — numpy-backed WorldView + WorldMutator

**Files:**
- Create: `src/meadow/world_state.py`
- Create: `tests/test_world_state.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_world_state.py
"""Tests for the numpy-backed WorldState."""

import numpy as np
import pytest

from meadow.hex import Axial, HexGrid
from meadow.world import WorldMutator, WorldView
from meadow.world_state import WorldState


class TestWorldStateProtocols:
    def test_satisfies_world_view(self):
        ws = WorldState(HexGrid(3, 3))
        assert isinstance(ws, WorldView)

    def test_satisfies_world_mutator(self):
        ws = WorldState(HexGrid(3, 3))
        assert isinstance(ws, WorldMutator)


class TestWorldStateReadWrite:
    def test_moisture_round_trip(self):
        ws = WorldState(HexGrid(5, 5))
        h = Axial(2, 3)
        ws.apply_flow_delta(h, moisture_delta=1.5, nutrient_delta=0.0)
        assert ws.moisture_at(h) == pytest.approx(1.5)

    def test_nutrients_round_trip(self):
        ws = WorldState(HexGrid(5, 5))
        h = Axial(1, 1)
        ws.apply_flow_delta(h, moisture_delta=0.0, nutrient_delta=3.7)
        assert ws.nutrients_at(h) == pytest.approx(3.7)

    def test_light_round_trip(self):
        ws = WorldState(HexGrid(5, 5))
        h = Axial(0, 0)
        ws.set_light(h, 0.85)
        assert ws.light_at(h) == pytest.approx(0.85)

    def test_occupant_default_is_none(self):
        ws = WorldState(HexGrid(3, 3))
        assert ws.occupant_id_at(Axial(1, 1)) is None

    def test_occupant_set_and_clear(self):
        ws = WorldState(HexGrid(3, 3))
        h = Axial(1, 1)
        ws.set_occupant(h, 42)
        assert ws.occupant_id_at(h) == 42
        ws.set_occupant(h, None)
        assert ws.occupant_id_at(h) is None

    def test_initial_fields_are_zero(self):
        ws = WorldState(HexGrid(4, 4))
        for h in ws.grid:
            assert ws.moisture_at(h) == 0.0
            assert ws.nutrients_at(h) == 0.0
            assert ws.light_at(h) == 0.0

    def test_flow_delta_accumulates(self):
        ws = WorldState(HexGrid(3, 3))
        h = Axial(1, 1)
        ws.apply_flow_delta(h, 2.0, 1.0)
        ws.apply_flow_delta(h, 3.0, 0.5)
        assert ws.moisture_at(h) == pytest.approx(5.0)
        assert ws.nutrients_at(h) == pytest.approx(1.5)


class TestWorldStateArrayAccess:
    def test_total_moisture_property(self):
        ws = WorldState(HexGrid(3, 3))
        ws.apply_flow_delta(Axial(0, 0), 10.0, 0.0)
        ws.apply_flow_delta(Axial(1, 1), 5.0, 0.0)
        assert ws.total_moisture() == pytest.approx(15.0)

    def test_total_nutrients_property(self):
        ws = WorldState(HexGrid(3, 3))
        ws.apply_flow_delta(Axial(0, 0), 0.0, 7.0)
        assert ws.total_nutrients() == pytest.approx(7.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --extra dev pytest tests/test_world_state.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement WorldState**

```python
# src/meadow/world_state.py
"""Concrete world state backed by numpy arrays.

Implements both WorldView (reads) and WorldMutator (writes).
Arrays are flat, indexed by (q * grid.height + r).
"""

from __future__ import annotations

import numpy as np

from meadow.hex import Axial, HexGrid

_NO_OCCUPANT: int = -1


class WorldState:
    """Numpy-backed tile fields for a HexGrid."""

    def __init__(self, grid: HexGrid) -> None:
        self.grid = grid
        n = len(grid)
        self.moisture = np.zeros(n, dtype=np.float64)
        self.nutrients = np.zeros(n, dtype=np.float64)
        self.light = np.zeros(n, dtype=np.float64)
        self.drainage = np.ones(n, dtype=np.float64)
        self.slope_q = np.zeros(n, dtype=np.float64)
        self.slope_r = np.zeros(n, dtype=np.float64)
        self._occupants = np.full(n, _NO_OCCUPANT, dtype=np.int64)

    def _idx(self, h: Axial) -> int:
        return h.q * self.grid.height + h.r

    # --- WorldView ---

    def moisture_at(self, h: Axial) -> float:
        return float(self.moisture[self._idx(h)])

    def nutrients_at(self, h: Axial) -> float:
        return float(self.nutrients[self._idx(h)])

    def light_at(self, h: Axial) -> float:
        return float(self.light[self._idx(h)])

    def occupant_id_at(self, h: Axial) -> int | None:
        v = int(self._occupants[self._idx(h)])
        return None if v == _NO_OCCUPANT else v

    # --- WorldMutator ---

    def apply_flow_delta(
        self, h: Axial, moisture_delta: float, nutrient_delta: float
    ) -> None:
        i = self._idx(h)
        self.moisture[i] += moisture_delta
        self.nutrients[i] += nutrient_delta

    def set_light(self, h: Axial, value: float) -> None:
        self.light[self._idx(h)] = value

    def set_occupant(self, h: Axial, plant_id: int | None) -> None:
        self._occupants[self._idx(h)] = _NO_OCCUPANT if plant_id is None else plant_id

    # --- Aggregate queries (for diagnostics / tests) ---

    def total_moisture(self) -> float:
        return float(np.sum(self.moisture))

    def total_nutrients(self) -> float:
        return float(np.sum(self.nutrients))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --extra dev pytest tests/test_world_state.py -v`
Expected: all passed

- [ ] **Step 5: Lint and type-check**

Run: `uv run --extra dev ruff check src/meadow/world_state.py tests/test_world_state.py`
Run: `uv run --extra dev mypy src/meadow/world_state.py`

- [ ] **Step 6: Commit**

```
git add src/meadow/world_state.py tests/test_world_state.py
git commit -m "feat(world_state): add numpy-backed WorldState implementing WorldView and WorldMutator"
```

---

## Chunk 2: Weather, Flow, and Light phases

### Task 3: WeatherPhase — rainfall

**Files:**
- Create: `src/meadow/weather.py`
- Create: `tests/test_weather.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_weather.py
"""Tests for the weather phase."""

import pytest

from meadow.hex import HexGrid
from meadow.phases import PhaseName
from meadow.weather import WeatherPhase
from meadow.world import TurnContext
from meadow.world_state import WorldState


class TestWeatherPhase:
    def test_name_is_weather(self):
        phase = WeatherPhase(rainfall_per_tick=1.0)
        assert phase.name == PhaseName.WEATHER

    def test_rainfall_adds_moisture_uniformly(self):
        grid = HexGrid(3, 3)
        ws = WorldState(grid)
        phase = WeatherPhase(rainfall_per_tick=2.5)
        ctx = TurnContext(tick=0, weather_seed=0)

        phase.execute(ws, ws, ctx)

        for h in grid:
            assert ws.moisture_at(h) == pytest.approx(2.5)

    def test_rainfall_accumulates_over_ticks(self):
        grid = HexGrid(3, 3)
        ws = WorldState(grid)
        phase = WeatherPhase(rainfall_per_tick=1.0)

        for tick in range(3):
            phase.execute(ws, ws, TurnContext(tick=tick, weather_seed=tick))

        assert ws.total_moisture() == pytest.approx(3.0 * 9)

    def test_total_moisture_increase_matches_expected(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        phase = WeatherPhase(rainfall_per_tick=0.5)

        before = ws.total_moisture()
        phase.execute(ws, ws, TurnContext(tick=0, weather_seed=0))
        after = ws.total_moisture()

        assert after - before == pytest.approx(0.5 * 25)

    def test_result_has_diagnostics(self):
        ws = WorldState(HexGrid(2, 2))
        phase = WeatherPhase(rainfall_per_tick=1.0)
        result = phase.execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert result.phase_name == "WEATHER"
        assert result.diagnostics is not None
        assert result.diagnostics["rainfall_total"] == pytest.approx(4.0)
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement WeatherPhase**

```python
# src/meadow/weather.py
"""Weather phase: generates moisture inputs each tick.

v1 simplification: uniform rainfall across the entire grid.
"""

from __future__ import annotations

from meadow.phases import PhaseName
from meadow.world import PhaseResult, TurnContext, WorldMutator, WorldView
from meadow.world_state import WorldState


class WeatherPhase:
    """Adds uniform rainfall to every tile each tick."""

    def __init__(self, rainfall_per_tick: float = 1.0) -> None:
        self._rainfall = rainfall_per_tick

    @property
    def name(self) -> PhaseName:
        return PhaseName.WEATHER

    def execute(
        self, view: WorldView, mutator: WorldMutator, ctx: TurnContext
    ) -> PhaseResult:
        if not isinstance(mutator, WorldState):
            raise TypeError("WeatherPhase requires a WorldState mutator for array access")
        mutator.moisture += self._rainfall
        total = self._rainfall * len(mutator.grid)
        return PhaseResult(
            phase_name=self.name.name,
            diagnostics={"rainfall_total": total},
        )
```

- [ ] **Step 4: Run tests, lint, commit**

Run: `uv run --extra dev pytest tests/test_weather.py -v`
Run: `uv run --extra dev ruff check src/meadow/weather.py tests/test_weather.py`
Run: `uv run --extra dev mypy src/meadow/weather.py`

```
git add src/meadow/weather.py tests/test_weather.py
git commit -m "feat(weather): add WeatherPhase with uniform rainfall"
```

---

### Task 4: FlowPhase — slope-driven redistribution with mass conservation

**Files:**
- Create: `src/meadow/flow.py`
- Create: `tests/test_flow.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_flow.py
"""Tests for the flow phase — slope-driven moisture/nutrient redistribution.

Key invariant: total moisture and nutrients are conserved (closed boundary).
"""

import numpy as np
import pytest

from meadow.hex import Axial, HexGrid
from meadow.flow import FlowPhase
from meadow.phases import PhaseName
from meadow.world import TurnContext
from meadow.world_state import WorldState


class TestFlowPhaseContract:
    def test_name_is_flow(self):
        assert FlowPhase().name == PhaseName.FLOW

    def test_result_has_diagnostics(self):
        ws = WorldState(HexGrid(3, 3))
        result = FlowPhase().execute(ws, ws, TurnContext(tick=0, weather_seed=0))
        assert result.phase_name == "FLOW"
        assert result.diagnostics is not None


class TestFlowConservation:
    """Mass conservation: total moisture/nutrients before == after."""

    def test_moisture_conserved_on_flat_terrain(self):
        ws = WorldState(HexGrid(5, 5))
        ws.moisture[::2] = 10.0
        before = ws.total_moisture()

        FlowPhase().execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert ws.total_moisture() == pytest.approx(before)

    def test_moisture_conserved_on_sloped_terrain(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        ws.moisture[:] = 5.0
        for h in grid:
            i = ws._idx(h)
            ws.slope_q[i] = 0.3
            ws.slope_r[i] = -0.1
        before = ws.total_moisture()

        FlowPhase().execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert ws.total_moisture() == pytest.approx(before)

    def test_nutrients_conserved(self):
        grid = HexGrid(4, 4)
        ws = WorldState(grid)
        ws.nutrients[:] = 2.0
        ws.moisture[:] = 5.0
        for h in grid:
            ws.slope_q[ws._idx(h)] = 0.5
        before = ws.total_nutrients()

        FlowPhase().execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert ws.total_nutrients() == pytest.approx(before)


class TestFlowBehavior:
    def test_no_flow_on_flat_terrain(self):
        ws = WorldState(HexGrid(3, 3))
        ws.moisture[:] = 5.0
        snapshot = ws.moisture.copy()

        FlowPhase().execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        np.testing.assert_array_almost_equal(ws.moisture, snapshot)

    def test_moisture_moves_downhill(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        center = Axial(2, 2)
        ci = ws._idx(center)
        ws.moisture[ci] = 100.0
        ws.slope_q[ci] = 1.0

        FlowPhase().execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert ws.moisture_at(center) < 100.0
        assert ws.moisture_at(Axial(3, 2)) > 0.0 or ws.moisture_at(Axial(3, 1)) > 0.0

    def test_no_negative_moisture(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        ws.moisture[:] = 0.1
        for h in grid:
            ws.slope_q[ws._idx(h)] = 1.0
        
        for _ in range(10):
            FlowPhase().execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert np.all(ws.moisture >= -1e-12)
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement FlowPhase**

```python
# src/meadow/flow.py
"""Flow phase: slope-driven moisture and nutrient redistribution.

v1 simplification: for each hex, outflow to in-bounds neighbors is proportional
to (slope dot direction-to-neighbor) * drainage.  Deltas are computed
simultaneously then applied, preserving mass conservation on a closed grid.

Physics assumptions documented for later refinement:
- No sub-tile pressure gradients.
- Nutrients travel proportionally with moisture (concentration-based).
- Boundary is closed: nothing flows off the edge.
"""

from __future__ import annotations

import numpy as np

from meadow.hex import DIRECTIONS, Axial, HexGrid
from meadow.phases import PhaseName
from meadow.world import PhaseResult, TurnContext, WorldMutator, WorldView
from meadow.world_state import WorldState


def _compute_flow_deltas(ws: WorldState) -> tuple[np.ndarray, np.ndarray]:
    """Return (moisture_deltas, nutrient_deltas) arrays preserving mass."""
    grid = ws.grid
    n = len(grid)
    m_delta = np.zeros(n, dtype=np.float64)
    n_delta = np.zeros(n, dtype=np.float64)

    for h in grid:
        i = ws._idx(h)
        m_here = ws.moisture[i]
        n_here = ws.nutrients[i]
        if m_here <= 0:
            continue

        sq = ws.slope_q[i]
        sr = ws.slope_r[i]
        drain = ws.drainage[i]

        weights: list[tuple[int, float]] = []
        total_weight = 0.0
        for d in DIRECTIONS:
            nb = Axial(h.q + d.q, h.r + d.r)
            if not grid.in_bounds(nb):
                continue
            dot = sq * d.q + sr * d.r
            if dot > 0:
                w = dot * drain
                weights.append((ws._idx(nb), w))
                total_weight += w

        if total_weight <= 0:
            continue

        outflow_frac = min(total_weight, 1.0)
        m_out = m_here * outflow_frac
        concentration = n_here / m_here if m_here > 0 else 0.0
        n_out = m_out * concentration

        m_delta[i] -= m_out
        n_delta[i] -= n_out
        for nb_idx, w in weights:
            share = w / total_weight
            m_delta[nb_idx] += m_out * share
            n_delta[nb_idx] += n_out * share

    return m_delta, n_delta


class FlowPhase:
    """Redistribute moisture and nutrients according to slope and drainage."""

    @property
    def name(self) -> PhaseName:
        return PhaseName.FLOW

    def execute(
        self, view: WorldView, mutator: WorldMutator, ctx: TurnContext
    ) -> PhaseResult:
        if not isinstance(mutator, WorldState):
            raise TypeError("FlowPhase requires a WorldState mutator")
        m_delta, n_delta = _compute_flow_deltas(mutator)
        mutator.moisture += m_delta
        mutator.nutrients += n_delta
        return PhaseResult(
            phase_name=self.name.name,
            diagnostics={
                "moisture_moved": float(np.sum(np.abs(m_delta)) / 2),
                "nutrient_moved": float(np.sum(np.abs(n_delta)) / 2),
            },
        )
```

- [ ] **Step 4: Run tests, lint, commit**

Run: `uv run --extra dev pytest tests/test_flow.py -v`
Run: `uv run --extra dev ruff check src/meadow/flow.py tests/test_flow.py`
Run: `uv run --extra dev mypy src/meadow/flow.py`

```
git add src/meadow/flow.py tests/test_flow.py
git commit -m "feat(flow): add FlowPhase with slope-driven redistribution and mass conservation"
```

---

### Task 5: LightPhase — uniform sunlight

**Files:**
- Create: `src/meadow/light.py`
- Create: `tests/test_light.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_light.py
"""Tests for the light phase."""

import pytest

from meadow.hex import HexGrid
from meadow.light import LightPhase
from meadow.phases import PhaseName
from meadow.world import TurnContext
from meadow.world_state import WorldState


class TestLightPhase:
    def test_name_is_light(self):
        assert LightPhase().name == PhaseName.LIGHT

    def test_uniform_sunlight(self):
        grid = HexGrid(4, 4)
        ws = WorldState(grid)
        LightPhase(base_sunlight=1.0).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        for h in grid:
            assert ws.light_at(h) == pytest.approx(1.0)

    def test_configurable_intensity(self):
        grid = HexGrid(3, 3)
        ws = WorldState(grid)
        LightPhase(base_sunlight=0.6).execute(ws, ws, TurnContext(tick=0, weather_seed=0))

        for h in grid:
            assert ws.light_at(h) == pytest.approx(0.6)

    def test_result_has_diagnostics(self):
        ws = WorldState(HexGrid(2, 2))
        result = LightPhase().execute(ws, ws, TurnContext(tick=0, weather_seed=0))
        assert result.phase_name == "LIGHT"
```

- [ ] **Step 2: Implement LightPhase**

```python
# src/meadow/light.py
"""Light phase: distribute sunlight to tiles.

v1 simplification: uniform sunlight everywhere, no canopy occlusion.
Canopy-based shading will be added when plants have leaf coverage.
"""

from __future__ import annotations

from meadow.phases import PhaseName
from meadow.world import PhaseResult, TurnContext, WorldMutator, WorldView
from meadow.world_state import WorldState


class LightPhase:
    """Set sunlight to a uniform base value across all tiles."""

    def __init__(self, base_sunlight: float = 1.0) -> None:
        self._base = base_sunlight

    @property
    def name(self) -> PhaseName:
        return PhaseName.LIGHT

    def execute(
        self, view: WorldView, mutator: WorldMutator, ctx: TurnContext
    ) -> PhaseResult:
        if not isinstance(mutator, WorldState):
            raise TypeError("LightPhase requires a WorldState mutator")
        mutator.light[:] = self._base
        return PhaseResult(phase_name=self.name.name)
```

- [ ] **Step 3: Run tests, lint, commit**

Run: `uv run --extra dev pytest tests/test_light.py -v`

```
git add src/meadow/light.py tests/test_light.py
git commit -m "feat(light): add LightPhase with uniform sunlight distribution"
```

---

## Chunk 3: Integration with real WorldState

### Task 6: Full tick with real phases + invariant tests

**Files:**
- Create: `tests/test_integration_phase2.py`

- [ ] **Step 1: Write integration tests**

```python
# tests/test_integration_phase2.py
"""Phase 2 integration: full tick with real WorldState and weather/flow/light.

Key invariants tested:
- Mass conservation through a complete tick
- No negative moisture after flow
- All hexes receive light
"""

import numpy as np
import pytest

from meadow.flow import FlowPhase
from meadow.hex import HexGrid
from meadow.light import LightPhase
from meadow.phases import NoOpPhase, PhaseName
from meadow.sim import TurnPipeline
from meadow.weather import WeatherPhase
from meadow.world import TurnContext
from meadow.world_state import WorldState


def _build_phase2_pipeline(
    rainfall: float = 1.0, sunlight: float = 1.0
) -> TurnPipeline:
    return TurnPipeline({
        PhaseName.WEATHER: WeatherPhase(rainfall_per_tick=rainfall),
        PhaseName.FLOW: FlowPhase(),
        PhaseName.LIGHT: LightPhase(base_sunlight=sunlight),
        PhaseName.UPTAKE: NoOpPhase(PhaseName.UPTAKE),
        PhaseName.DEPLETION: NoOpPhase(PhaseName.DEPLETION),
        PhaseName.GROWTH: NoOpPhase(PhaseName.GROWTH),
    })


class TestPhase2Integration:
    def test_full_tick_completes_on_10x10(self):
        ws = WorldState(HexGrid(10, 10))
        pipeline = _build_phase2_pipeline()
        results = pipeline.run_tick(ws, ws, TurnContext(tick=0, weather_seed=0))
        assert len(results) == 6

    def test_moisture_conservation_across_tick(self):
        grid = HexGrid(8, 8)
        ws = WorldState(grid)
        for h in grid:
            ws.slope_q[ws._idx(h)] = 0.2
        pipeline = _build_phase2_pipeline(rainfall=2.0)

        expected_added = 2.0 * len(grid)
        pipeline.run_tick(ws, ws, TurnContext(tick=0, weather_seed=0))

        assert ws.total_moisture() == pytest.approx(expected_added)

    def test_no_negative_moisture_after_tick(self):
        grid = HexGrid(6, 6)
        ws = WorldState(grid)
        for h in grid:
            ws.slope_q[ws._idx(h)] = 0.8
            ws.slope_r[ws._idx(h)] = 0.3
        pipeline = _build_phase2_pipeline(rainfall=0.1)

        for tick in range(20):
            pipeline.run_tick(ws, ws, TurnContext(tick=tick, weather_seed=tick))

        assert np.all(ws.moisture >= -1e-12)

    def test_light_set_every_tick(self):
        grid = HexGrid(4, 4)
        ws = WorldState(grid)
        pipeline = _build_phase2_pipeline(sunlight=0.9)

        pipeline.run_tick(ws, ws, TurnContext(tick=0, weather_seed=0))

        for h in grid:
            assert ws.light_at(h) == pytest.approx(0.9)

    def test_multi_tick_moisture_accumulates(self):
        grid = HexGrid(5, 5)
        ws = WorldState(grid)
        pipeline = _build_phase2_pipeline(rainfall=1.0)

        for tick in range(5):
            pipeline.run_tick(ws, ws, TurnContext(tick=tick, weather_seed=tick))

        assert ws.total_moisture() == pytest.approx(5.0 * 25)
```

- [ ] **Step 2: Run integration tests**

Run: `uv run --extra dev pytest tests/test_integration_phase2.py -v`

- [ ] **Step 3: Run full suite + linters**

Run: `uv run --extra dev pytest tests/ -v`
Run: `uv run --extra dev ruff check src/meadow/ tests/`
Run: `uv run --extra dev mypy src/meadow/`

- [ ] **Step 4: Commit**

```
git add tests/test_integration_phase2.py
git commit -m "test: add Phase 2 integration tests with mass-conservation invariants"
```

- [ ] **Step 5: Final full-suite verification**

Run: `uv run --extra dev pytest tests/ -v --tb=short`
Expected: all green.
