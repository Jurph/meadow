# Vision

Tiny green plants sprouting on a dense hex mesh of green, struggling when there's no rain, thriving when there is. Harsh conditions routinely kill off the least fit, and the strong evolve and thrive. Offspring vary within predictable limits from their parents, occasionally mutating to be wildly different in one or two ways. Dead plants decay and feed their former neighbors. Life goes on.

# Systems

Fundamentally we're tracking interactions between the Plant class and the HexTile class.

**Plants** consume moisture and nutrients from every HexTile where they can place roots. They collect sunlight from every tile where they grow leaves. The moisture and nutrients flow up to the leaves, photosynthesize, and having completed their trip generate energy and cellulose that can be used to grow the plant -- either extending roots, lengthening a stem, growing a leaf, hardening a stem, or reproducing. The "choices" a plant makes with extra cellulose are governed by its layout and traits. (This is going to take some design work: how do we encode the difference between a clump of grass, which grows a mesh of roots and throws dozens of leaves/blades up from the soil, and a dandelion, which grows a deep taproot and horizontal leaves? How do we encode bushes which choose to create woody stems with some of their cellulose?) Reproduction strategies will require "betting" an energy surplus across 1, 2, 4, or hundreds of seeds/spores. All of these will ultimately be numeric values with a mean and variance, and **mutations** in offspring drive the value to the top or bottom of the range, and narrow the variance. (Perhaps propensity for mutations starts at 1% but can increase as a mutation...?!)

**Hex Tiles** have water flowing through them, as well as nutrients. The slope they're on governs how water and nutrients get carried through the soil, and the soil's drainage limits or expedites the flow. Each hex tile can support one plant being its primary resident, although roots from other plants can come in laterally. As more roots fill a hex tile the drainage changes. Water can come from a daily weather check. Nutrients come from a random sprinkling of bird droppings & dead insects and plants, or from animal spoor, or from fruits that are packed with surplus nutrients for their seeds on purpose, or even from a large animal corpse or decaying log.

The **game loop** needs to handle generation of water and nutrients at the start of a turn, then propagation of both. Sunlight is generated and distributed top-down onto plants based on which hexes they cover. Once the resources are moved around the board, the plants should take turns grabbing them up (perhaps smaller plants have an advantage in speed here?). Then nutrient depletion or damage (evaporation? predation?) and then the plants get a chance to use any surplus they have.

# Gameplay

For now just encoding the systems and building out a 200x200 grid of hexes should be enough. The scale we're looking at is maybe ... centimeter hexes, so this is only a 2m x 2m piece of a lawn. Thriving plants will definitely crowd out neighbors and we'll need a mechanic for "the plant in this hex has grown its diameter so much that it now occupies (1, 4, 7, 19, etc.) hexes.

Pretty early on, though, we'll need click-to-plop seeds, a plant design sidebar, and other debugging tools that will eventually make their way into being fun gameplay elements.