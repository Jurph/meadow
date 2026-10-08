# Plant Functional Model

## Status

This document defines Meadow's target simulation business rules. The implemented foundation now
includes:

- water, mineral, and assimilate reserves
- persistent trait-weighted assimilate allocation
- per-tick balance sheets for potential and actual uptake, photosynthesis, and construction
- atomic water/mineral/assimilate construction costs
- explicit leaf organs attached to stem nodes
- leaf-area photosynthesis from canopy-cell light and available water
- schema-v2 snapshots and Godot rendering for leaves, reserves, fluxes, costs, and constraints

The current implementation still uses uniform rain and light, 2D world-resource columns,
plant-wide reserves, sequential root uptake, and unconstrained graph transport. Transpiration,
canopy interception, simultaneous competition, maintenance, and lifecycle rules remain targets.

The model favors visible ecological tradeoffs and deterministic accounting over biochemical
detail. Python remains authoritative; Godot only renders snapshots and diagnostics.

## Decisions

The authoritative model uses:

- water, mineral nutrients, and assimilate as the three internal plant resources
- a capacity-constrained organ graph for transport
- simultaneous proportional sharing when organisms contest a cell resource
- explicit leaf organs attached to stem nodes

Actual organ output is never a fixed yield. An organ has capacity; its actual flux is computed from capacity, local conditions, graph connectivity, competition, and plant demand.

## Spatial environment

`z = 0` is the surface, `z < 0` is soil, and `z > 0` is canopy.

Each soil cell stores:

- soil water
- mineral nutrients
- root occupancy and uptake capacity by plant
- properties used by flow and percolation

Each canopy cell stores or derives:

- incident light before interception
- leaf area and interception capacity by plant
- light remaining after interception
- local or world-level humidity and wind inputs

Rain enters surface cells. Surface flow and downward percolation redistribute water before roots submit uptake claims. The current 2D world fields are an implementation simplification, not the target rule.

## Plant state

A plant owns:

- a stable identity and heritable trait values
- one connected organ graph rooted at its seed or crown
- water, mineral, and assimilate reserves
- finite reserve capacities derived from living tissue
- organ health and accumulated maintenance deficits
- allocation preferences for roots, stems, leaves, and reproduction

In the target model, reserve quantities are located at organ nodes or storage tissue. Plant-level
reserve values are accounting totals, not a path around graph transport. An intermediate
implementation may retain aggregate reserves only while its diagnostics distinguish where each
resource entered, where it is demanded, and which future path constrains delivery.

### Root segments

A root segment has geometry, occupied soil cells, health, uptake capacity, and transport capacity. Its potential uptake depends on its active surface contribution in each occupied cell. Additional root area can increase capacity, but never creates soil resources.

### Stem segments

A stem segment has length, diameter, health, support capacity, and transport capacity. It is not a resource source. A narrow, long, damaged, or disconnected stem may limit delivery between roots and leaves.

### Leaf organs

A leaf is attached to a stem node rather than represented as a stem tip. It has area, canopy position, orientation or projected-area factor, health, photosynthetic capacity, and transpiration capacity.

## Resource semantics

| Resource | External source | Transfers | Principal sinks |
|---|---|---|---|
| Soil water / plant water | rainfall | soil flow, root uptake, graph transport | transpiration, construction, runoff, evaporation |
| Mineral nutrients | initial soil, deposition, decay | soil flow, root uptake, graph transport | construction, reproduction, loss from the simulated area |
| Assimilate | photosynthesis | graph transport, reserve allocation | maintenance, construction, reproduction, respiration or decay |

Root uptake transfers water or minerals from the world to a plant; it does not create either resource. Photosynthesis creates assimilate from environmental carbon and captured light, constrained by delivered water. Structural biomass is represented by constructed organs rather than by a fourth spendable reserve.

## Tick contract

All competition uses state captured at the start of its phase. Claims are resolved before mutations are committed, so plant registration or iteration order cannot change ecological outcomes.

1. **Weather** supplies rainfall, incident sunlight, humidity, and wind.
2. **Soil movement** applies surface flow and percolation to water and mobile minerals.
3. **Canopy interception** resolves light from the highest canopy cells downward using current leaf geometry.
4. **Potential root uptake** calculates water and mineral claims from root capacity, local availability, plant demand, and remaining reserve capacity.
5. **Cell competition** divides contested soil resources proportionally among claims and deducts only the resolved totals.
6. **Upward transport** routes absorbed water and minerals through connected root and stem paths, subject to edge capacity and health.
7. **Leaf gas exchange** calculates transpiration and photosynthesis from leaf area, captured light, humidity, wind, health, and delivered water.
8. **Assimilate transport** routes new assimilate from leaves toward maintenance, storage, construction sites, and reproductive sinks.
9. **Maintenance** pays existing organs before discretionary construction. Unpaid demand damages the affected organ.
10. **Allocation and construction** distribute spendable resources among root, stem, leaf, and reproductive proposals according to plant traits.
11. **Commit** applies accepted construction and occupancy changes. New organs become functional on the next tick.
12. **Death and decay** disable dead organs and transfer their material to the world's detrital or soil-resource system.

## Competition rules

### Soil resources

For one cell and one resource, each plant submits a non-negative potential claim `claim[p]`. If total claims do not exceed the available amount, every claim is satisfied. Otherwise:

```text
actual[p] = available * claim[p] / sum(claims)
```

Consequences:

- total actual uptake never exceeds cell availability
- equal claims receive equal shares
- a plant may increase its share only by increasing relevant root capacity or demand
- changing plant iteration order cannot change the result

Claims from multiple root segments of one plant in one cell are aggregated before inter-plant competition. The plant balance sheet may retain per-organ contributions for diagnosis.

### Light

Light is resolved from upper to lower canopy cells. A leaf's potential interception depends on projected leaf area, health, and an absorption coefficient. Leaves at the same height share insufficient incident light proportionally to potential interception. Uncaptured light continues downward.

No canopy layer may intercept more light than enters it. New leaves affect shading beginning on the following tick.

## Transport rules

The organ graph is the authoritative connectivity structure.

- Water and minerals originate at root sources and move toward consuming or storage sinks.
- Assimilate originates at leaf sources and moves toward maintenance, construction, storage, and reproductive sinks.
- Every traversed root or stem edge imposes a finite capacity derived from diameter, length, type, and health.
- Flow through an edge cannot exceed its capacity for the tick.
- A disconnected organ receives no resource through the broken path and contributes no source flux to the connected plant.
- When equal-priority sinks compete for constrained transport, they receive proportional shares of the available flow.
- Existing-organ maintenance has priority over discretionary growth; growth and reproduction use only the remainder.

The first implementation may calculate aggregate plant reserves while graph fields are introduced, but public rules and snapshots must preserve the distinction between source, sink, path capacity, potential flux, and actual flux so graph-constrained flow can replace aggregation without changing ecological meaning.

## Leaf gas exchange

Potential transpiration increases with:

- active leaf area
- drier air
- stronger wind
- leaf transpiration traits

Actual transpiration is limited by water deliverable through the graph. Water stress reduces gas exchange rather than allowing plant reserves to become negative.

Potential photosynthesis increases with captured light, active leaf area, health, and photosynthetic traits. Actual photosynthesis is constrained by the water-supported gas-exchange rate and transport. It adds assimilate; it does not create mineral nutrients.

Exact response curves and constants are balance parameters. Their required monotonic relationships are business rules:

- more captured light cannot reduce potential photosynthesis
- more active leaf area cannot reduce potential photosynthesis or transpiration
- lower humidity cannot reduce potential transpiration
- stronger wind cannot reduce potential transpiration
- insufficient delivered water cannot increase actual photosynthesis

## Maintenance, construction, and health

Each living organ declares a per-tick maintenance demand. Maintenance is paid from resources deliverable to that organ. A shortfall records a deficit and reduces health according to an explicit damage rule; it is never silently ignored.

Each construction proposal declares its full cost vector:

```text
(assimilate, water, minerals)
```

A proposal is accepted only when:

- its attachment point remains alive and connected
- its destination satisfies spatial and occupancy rules
- its full cost can be delivered through the graph
- the plant's allocation budget for that organ class can pay the cost

Construction is atomic at the model's current organ granularity. Rejected or unfunded proposals do not partially create organs or drive reserves below zero.

## Accounting invariants

For every tick:

- world and plant water, minerals, and assimilate remain finite and non-negative
- uptake cannot exceed the source cell's available resource
- proportional competition is independent of plant iteration order
- intercepted light cannot exceed incident light
- transport cannot cross a disconnected path or exceed edge capacity
- actual flux cannot exceed potential flux
- maintenance and construction spending is recorded against an explicit source
- accepted construction pays its complete cost exactly once
- new geometry cannot contribute uptake, shade, or photosynthesis until the next tick
- opening reserves plus recorded inputs minus recorded outputs equal closing reserves within numeric tolerance

External sources and losses—rain, sunlight, atmospheric carbon, runoff, evaporation, respiration, and export from the simulated area—must be identified as such rather than hidden in a balancing term.

## Plant balance sheet

Each plant's tick diagnostics expose at least:

- opening and closing reserves
- potential and actual root uptake by resource
- incident, intercepted, and shaded light
- potential and actual transpiration
- potential and actual photosynthesis
- transport requested, delivered, and capacity-limited
- maintenance demanded, paid, and unpaid
- construction proposals, potential cost, actual spending, and accepted organ counts by type
- each curtailed flux's limiting factor

These diagnostics are simulation outputs. The renderer may visualize them but must not recompute them.

## Required scenarios

The functional model is not complete until deterministic tests demonstrate:

1. Two equal plants contesting one wet soil cell receive equal water independent of registration order.
2. A plant occupying two equally wet root cells has greater potential uptake than an otherwise equal plant occupying one, subject to demand and transport limits.
3. A lower leaf receives less light beneath an intercepting upper leaf.
4. Lower humidity or stronger wind increases potential transpiration for the same leaf.
5. Water-delivery limits reduce actual transpiration and photosynthesis without producing negative reserves.
6. Narrowing or damaging a stem can bottleneck otherwise sufficient root and leaf capacity.
7. Disconnecting a leaf prevents it from receiving water or contributing assimilate to the connected plant.
8. An organ is constructed only after its complete water, mineral, and assimilate cost is paid.
9. Unpaid maintenance produces explicit damage and eventually organ death.
10. A complete tick satisfies the resource and light accounting invariants.
