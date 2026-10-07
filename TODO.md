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

## Known constraints

- world fields are still 2D; cells at different `z` levels read the same column resources
- depletion is a no-op
- occupancy and crowding are stored but not enforced during growth
- reproduction, mutation, death, decay, and canopy occlusion are not implemented
- no production composition root, snapshot format, save/replay path, or Python-to-Godot bridge

## UI direction

- Godot 4.6 is the rendering and interaction stack
- Python remains authoritative for simulation state
- the current Godot scene is a static 7×7 hex preview
- development builds should expose a debug-heavy inspector before visual polish
- the world should read like a tilted or isometric hillside with plants growing upward

## Next implementation steps

1. Add a production `Simulation` composition root that owns the world, population, phases, and
   tick counter.
2. Define a versioned, immutable world snapshot for renderer and save/replay consumers.
3. Make the CLI run ticks and emit a snapshot.
4. Replace the Godot demo grid with rendering driven by a Python-produced snapshot.
5. Add occupancy and crowding rules before allowing unrestricted multi-plant growth.
6. Complete the lifecycle loop: reproduction, mutation, death, depletion, and decay.

## Repo setup

- [x] Python project setup and local development wrappers
- [x] CircleCI checks and Codecov upload hooks
- [x] issue templates and starter label definitions
- [x] simulation architecture and phase plans
- [x] simulation phases through graph-based plant growth
- [x] initial Godot project, scene, and visual references

## Repo chores to check after push

- [ ] confirm CircleCI runs on `main`
- [ ] confirm the label-sync workflow creates or updates the starter labels
- [ ] add `CODECOV_TOKEN` if Codecov should be active immediately
- [ ] verify README badges resolve

## Guardrails

- keep the Python simulation core testable without Godot
- let rendering consume stable snapshots rather than own simulation state
- keep ecology rules and presentation concerns separate
- avoid duplicate world rules in Python and GDScript
- prefer one observable end-to-end slice over another isolated subsystem
