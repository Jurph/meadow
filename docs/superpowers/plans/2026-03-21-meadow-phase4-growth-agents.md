# Meadow Phase 4: Growth Agents, PlantGraph, Tropisms — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Plants physically grow by extending root and stem segments into neighboring hex cells, guided by tropisms (gravitropism, hydrotropism) and zone-based branching from the research literature.

**Architecture:** `PlantGraph` is a tree of `Segment`s connecting `HexCell`s, with active tips that extend each tick. Tropism scoring is a set of pure functions that rank candidate neighbor cells. `GrowthPhase` spends allocated cellulose to extend tips via tropisms and create lateral branches according to zone rules. `PlantBody.root_hexes`/`leaf_hexes` become computed properties derived from the graph.

**Tech Stack:** Python 3.11+, numpy, pytest, ruff, mypy.

**Research basis:** Mußmann et al. 2024 (Swarm Grammar root model) — zone-based branching, tropism-weighted direction selection, GSA. Stock et al. 2024 — agent-based plant modeling.

---

## Task 1: PlantGraph + Segment types

**Files:**
- Create: `src/meadow/plant_graph.py`
- Create: `tests/test_plant_graph.py`

**`src/meadow/plant_graph.py`:**
- `SegmentType` enum: `ROOT`, `STEM`
- `Segment` dataclass: `id: int`, `parent_id: int | None`, `start: HexCell`, `end: HexCell`, `segment_type: SegmentType`, `diameter: float`, `order: int` (0=primary, 1=first lateral...), `accumulated_length: float`
- `GrowthTip` dataclass: `segment_id: int`, `cell: HexCell`, `segment_type: SegmentType`, `order: int`, `accumulated_length: float`
- `PlantGraph` class:
  - `_segments: dict[int, Segment]`, `_tips: list[GrowthTip]`, `_next_id: int`
  - `add_segment(parent_id, start, end, segment_type, diameter, order) -> Segment`
  - `tips` property → list of active GrowthTip
  - `root_cells` property → `set[HexCell]` from all ROOT segments (start + end)
  - `leaf_cells` property → `set[HexCell]` at ends of STEM segments, or home cell if no stems
  - `all_cells` property → union of all segment cells
  - `create_seed(home: HexCell) -> PlantGraph` classmethod: creates graph with one ROOT tip at home (z=0) pointing down and one STEM tip pointing up

**Tests:**
- Create seed graph → has 1 root tip, 1 stem tip
- Add segment → appears in root_cells or leaf_cells depending on type
- root_cells returns correct set after multiple segments
- tips tracks active growth points

---

## Task 2: TraitBundle research-informed params + PlantBody→Graph wiring

**Files:**
- Modify: `src/meadow/plant.py`
- Modify: `tests/test_plant.py`

**TraitBundle changes** — replace placeholder branching fields with research-informed ones:
```
# Zone-based branching (per Mußmann et al.)
basal_length: float = 1.0        # cm before first branch zone
branch_spacing: float = 0.8      # cm between branch points
apical_length: float = 1.0       # cm of non-branching tip
max_root_length: float = 15.0    # cm max single root branch
branch_probability: float = 0.5

# Tropism weights
gravitropism_weight: float = 1.0
hydrotropism_weight: float = 0.3
gsa_root: float = 60.0           # gravitropic set-point angle for laterals (degrees)

# Growth cost
cellulose_per_segment: float = 1.0  # cellulose to extend one hex
```

Remove old placeholders: `branching_angle`, `branching_frequency`, `taper_ratio`, `apical_dominance`.

**PlantBody changes:**
- Add `graph: PlantGraph | None = None` field
- `root_hexes` and `leaf_hexes` become `@property` — return from graph if present, else fallback to stored sets
- `PlantPopulation.register` with `home` creates a `PlantGraph.create_seed(home)` on the body

**Tests:**
- Existing tests keep passing (properties return same sets for seed)
- New test: registered plant with home has graph with tips
- TraitBundle new fields have correct defaults

---

## Task 3: Tropism scoring

**Files:**
- Create: `src/meadow/tropisms.py`
- Create: `tests/test_tropisms.py`

**Pure functions:**
- `score_gravitropism(candidate: HexCell, current: HexCell, is_root: bool) -> float` — roots prefer lower z (return `current.z - candidate.z` clamped 0-1); stems prefer higher z
- `score_hydrotropism(candidate: HexCell, view: WorldView) -> float` — return `view.moisture_at(candidate)` normalized
- `rank_growth_candidates(current: HexCell, candidates: list[HexCell], traits: TraitBundle, view: WorldView, is_root: bool) -> list[tuple[HexCell, float]]` — weighted sum of tropism scores, sorted descending

**Tests:**
- Gravitropism: root tip scores lower-z neighbor higher than upper-z
- Gravitropism: stem tip scores higher-z neighbor higher
- Hydrotropism: wetter neighbor scores higher
- rank_growth_candidates: returns sorted by combined score
- Zero weights: tropism has no effect

---

## Task 4: GrowthPhase — spend cellulose to extend graph

**Files:**
- Modify: `src/meadow/growth.py`

**Updated flow in `execute`:**
1. Photosynthesis → cellulose produced (unchanged)
2. Consume reserves (unchanged)
3. Add to plant.cellulose (unchanged)
4. `allocate_cellulose` → get `{"root": X, "leaf": Y, ...}`
5. **NEW**: call `_grow_tips(plant, allocation, view, grid)` which:
   - For each root tip in plant.body.graph.tips where type==ROOT:
     - If allocation["root"] >= traits.cellulose_per_segment:
       - Get 3D neighbors of tip cell, filter by grid.cell_in_bounds
       - Rank via tropisms
       - Pick best, add segment to graph, update tip, deduct cellulose
       - Check zone-based branching: if accumulated_length in branching zone and random < branch_probability, create lateral tip
   - Similar for STEM tips with allocation["leaf"] + allocation["stem"]
6. Deduct spent cellulose from plant.cellulose

**GrowthPhase.__init__** gains `grid: HexGrid` parameter.

**Tests:**
- Plant with cellulose + root tip → root extends downward after growth
- Plant with no cellulose → no growth
- Multiple ticks → root_hexes grows
- Branching creates lateral tips (seeded RNG for determinism)

---

## Task 5: Integration test

**Files:**
- Create: `tests/test_integration_phase4.py`

**Tests:**
- Full pipeline tick: plant grows roots, root_hexes expands
- Root grows preferentially downward (gravitropism)
- After enough ticks, plant has lateral branches
- Plant on wet vs dry side of grid: roots grow toward moisture (hydrotropism)
- All existing Phase 2/3 integration tests still pass
- Full suite green + linters clean
