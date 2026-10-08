# TODO

`meadow` has a tested Python simulation core and an early Godot client. This file is the restart
map for turning those pieces into one end-to-end terrarium.

## Vision

Build a plant-evolution terrarium on a hex grid:

- plants are the main agents
- the environment washes over them with pressure
- success at gathering resources lets plants grow, reproduce, and shift lineage traits
- mutations move continuous trait ranges instead of only flipping binary flags
- dead organisms return resources to the world and affect later generations

## Implemented simulation core

- 3D `HexCell(q, r, z)` coordinates over a bounded axial grid
- NumPy-backed moisture, nutrients, light, drainage, slope, and occupancy fields
- weather, slope-driven flow, uniform light, resource uptake, and growth phases
- plant traits, reserves, photosynthesis, and cellulose allocation
- segment-graph root and stem growth guided by gravitropism and hydrotropism
- deterministic phase and population ordering with integration coverage
- production `Simulation` composition root with an owned tick counter
- immutable, versioned renderer/save snapshots
- `meadow simulate` CLI output and a snapshot-driven Godot renderer

## Known constraints

- world fields are still 2D; cells at different `z` levels read the same column resources
- light and rainfall are uniform; humidity, wind, percolation, and canopy interception are absent
- leaves are inferred from stem tips rather than represented as explicit organs
- root uptake is sequential and based on unique occupied columns, not simultaneous capacity claims
- plant-wide moisture and nutrient reserves bypass graph transport constraints
- photosynthesis produces `cellulose` directly; transpiration, maintenance, and resource balance
  sheets are not implemented
- depletion is a no-op
- occupancy and crowding are stored but not enforced during growth
- reproduction, mutation, death, and decay are not implemented
- Python-to-Godot transport is a generated JSON file, not a live process connection
- snapshots are write-only; save loading and replay are not implemented

## UI direction

- Godot 4.6 is the rendering and interaction stack
- Python remains authoritative for simulation state
- the Godot scene renders simulated tile fields and plant segments from a versioned snapshot
- the current debug overlay exposes tick, population, segment, and reserve state
- the world should read like a tilted or isometric hillside with plants growing upward

## Next implementation steps

- [x] Add a production `Simulation` composition root.
- [x] Define a versioned, immutable world snapshot.
- [x] Make the CLI run ticks and emit a snapshot.
- [x] Render Python-produced tile and plant state in Godot.
- [ ] Implement the [`Plant Functional Model`](docs/plant-functional-model.md):
  - [ ] replace `cellulose` with water, mineral, and assimilate balance-sheet semantics
  - [ ] represent leaves as explicit organs attached to stem nodes
  - [ ] derive root uptake capacity and leaf gas-exchange capacity from organ geometry
  - [ ] add humidity, wind, transpiration, and top-down canopy interception
  - [ ] resolve contested soil resources and same-layer light proportionally
  - [ ] constrain water, mineral, and assimilate delivery through the organ graph
  - [ ] add maintenance demand, health, construction cost vectors, and limiting-factor diagnostics
- [ ] Add occupancy and crowding rules against the functional organ model.
- [ ] Complete the lifecycle loop: reproduction, mutation, death, depletion, and decay.
- [ ] Add live snapshot regeneration/reload only after the file seam remains stable.

## Repo setup

- [x] Python project setup and local development wrappers
- [x] CircleCI checks and Codecov upload hooks
- [x] issue templates and starter label definitions
- [x] simulation architecture and phase plans
- [x] simulation phases through graph-based plant growth
- [x] initial Godot project, scene, and visual references

## Repo chores to check after push

- [ ] confirm CircleCI runs on `main`
- [x] confirm the label-sync workflow creates or updates the starter labels
- [ ] add `CODECOV_TOKEN` if Codecov should be active immediately
- [ ] verify README badges resolve

## Guardrails

- keep the Python simulation core testable without Godot
- let rendering consume stable snapshots rather than own simulation state
- keep ecology rules and presentation concerns separate
- avoid duplicate world rules in Python and GDScript
- resolve shared resource claims from phase-start state, never plant iteration order
- record every plant resource source, sink, constraint, and reserve change in its balance sheet
- prefer one observable end-to-end slice over another isolated subsystem
