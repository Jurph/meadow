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
