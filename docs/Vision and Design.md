# Vision

Tiny green plants sprouting on a dense hex mesh of green, struggling when there's no rain, thriving when there is. Harsh conditions routinely kill off the least fit, and the strong evolve and thrive. Offspring vary within predictable limits from their parents, occasionally mutating to be wildly different in one or two ways. Dead plants decay and feed their former neighbors. Life goes on.

# Systems

The central interaction is between spatial environmental cells and plants represented as connected
organ graphs. The detailed terms and rules live in [`CONTEXT.md`](../CONTEXT.md) and the
[`Plant Functional Model`](plant-functional-model.md).

**Plants** place root segments in soil, stem segments through their structure, and leaf organs in
the canopy. Roots absorb soil water and mineral nutrients. Leaves intercept light, transpire water,
and produce assimilate through photosynthesis. Stem and root paths transport these resources with
finite capacity. Existing organs require maintenance; surplus water, minerals, and assimilate can
construct roots, stems, leaves, or reproductive structures. Heritable traits govern geometry,
capacity, and allocation, allowing grass, taproots, rosettes, and woody forms to emerge from one
model rather than plant-type subclasses.

**Environmental cells** hold or derive soil water, mineral nutrients, light, drainage, slope,
humidity, wind, occupancy, and competing organ capacity. Rain, flow, percolation, deposition, and
decay change world resources. Root overlap creates belowground competition; leaf overlap creates
top-down shade.

The **game loop** advances weather and environmental transport, resolves light and soil-resource
claims simultaneously, moves resources through each connected organ graph, computes transpiration
and photosynthesis, pays maintenance, and then constructs new growth or reproduction from the
remainder. Contested resources are shared proportionally to potential claims so simulation results
do not depend on plant iteration order.

# Gameplay

For now just encoding the systems and building out a 200x200 grid of hexes should be enough. The scale we're looking at is maybe ... centimeter hexes, so this is only a 2m x 2m piece of a lawn. Thriving plants will definitely crowd out neighbors and we'll need a mechanic for "the plant in this hex has grown its diameter so much that it now occupies (1, 4, 7, 19, etc.) hexes.

Pretty early on, though, we'll need click-to-plop seeds, a plant design sidebar, and other debugging tools that will eventually make their way into being fun gameplay elements.