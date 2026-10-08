# Meadow Domain

Meadow models plants competing for spatially distributed resources in a changing environment. This glossary names the ecological quantities and structures that simulation rules exchange.

## Space and organisms

**Soil cell**:
An underground hex volume containing soil water and mineral nutrients and capable of being occupied by root segments.
_Avoid_: Root tile, underground column

**Canopy cell**:
An aboveground hex volume through which light passes and in which leaf organs may intercept it.
_Avoid_: Leaf tile

**Plant**:
One living organism with a stable identity, a connected organ graph, internal reserves, and heritable traits.
_Avoid_: Agent when referring to the organism itself

**Organ graph**:
A plant's connected structure of root segments, stem segments, and leaf organs, rooted at its seed or crown.
_Avoid_: Body plan, segment list

**Root segment**:
An organ-graph edge that occupies soil cells and provides resource-uptake and transport capacity.
_Avoid_: Root tile

**Stem segment**:
An organ-graph edge that provides support and transport capacity between attached organs.
_Avoid_: Branch when the rule applies equally to trunks and stems

**Leaf organ**:
A surface organ attached to a stem node, with explicit area, canopy position, health, and gas-exchange capacity.
_Avoid_: Leaf segment, stem tip

## Resources and rates

**Soil water**:
Water stored in a soil cell and available for root uptake.
_Avoid_: Moisture when a conserved quantity is meant

**Mineral nutrients**:
Non-carbon resources absorbed from soil and incorporated into living tissue.
_Avoid_: Nutrients when the term could be confused with assimilate

**Assimilate**:
The plant's internal pool of photosynthetic carbon and usable chemical energy, spent on maintenance, construction, and reproduction.
_Avoid_: Cellulose, energy, nutrients

**Reserve**:
A resource held inside a plant but not yet committed to a particular sink.
_Avoid_: Yield, inventory

**Capacity**:
The maximum resource uptake, transport, or processing rate an organ could support under otherwise unconstrained conditions.
_Avoid_: Yield

**Potential flux**:
The resource transfer requested by an organ before environmental availability, competition, connectivity, and downstream capacity are applied.
_Avoid_: Yield, production

**Actual flux**:
The resource transfer that occurs after all constraints and competition are resolved.
_Avoid_: Potential, capacity

**Construction cost**:
The complete assimilate, water, and mineral requirement for creating or enlarging an organ.
_Avoid_: Cellulose cost

**Maintenance demand**:
The per-tick resource requirement for keeping existing living tissue healthy.
_Avoid_: Upkeep cost

**Plant balance sheet**:
A per-tick accounting of opening reserves, actual source and sink fluxes, limiting factors, and closing reserves.
_Avoid_: Debug stats
