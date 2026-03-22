"""Plant domain: identity, traits, body plan, and population registry.

Growth forms (grass, taproot, woody) are parameter-driven, not subclass-driven.
Leaf shape is encoded via number_of_lobes, lobe_aspect_ratio, and lobe_length
so that grass (1 narrow lobe) and maple (5-7 wide lobes) use the same model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from meadow.hex import HexCell

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

    # Branching geometry (placeholders for fractal growth)
    branching_angle: float = 30.0
    branching_frequency: float = 0.3
    taper_ratio: float = 0.7
    apical_dominance: float = 0.8

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

    home: HexCell
    root_hexes: set[HexCell] | None = None
    leaf_hexes: set[HexCell] | None = None

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
        home: HexCell | None = None,
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
