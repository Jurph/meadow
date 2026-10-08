"""Plant domain: identity, traits, body plan, and population registry.

Growth forms (grass, taproot, woody) are parameter-driven, not subclass-driven.
Leaf shape is encoded via number_of_lobes, lobe_aspect_ratio, and lobe_length
so that grass (1 narrow lobe) and maple (5-7 wide lobes) use the same model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from meadow.hex import HexCell
from meadow.plant_graph import PlantGraph
from meadow.resources import (
    AssimilateAllocation,
    PlantBalanceSheet,
    ResourcePool,
    ResourceVector,
)

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

    # Zone-based branching (per Mußmann et al. 2024)
    basal_length: float = 1.0
    branch_spacing: float = 0.8
    apical_length: float = 1.0
    max_root_length: float = 15.0
    branch_probability: float = 0.5

    # Tropism weights
    gravitropism_weight: float = 1.0
    hydrotropism_weight: float = 0.3
    gsa_root: float = 60.0

    # Construction cost vectors
    root_construction_cost: ResourceVector = field(
        default_factory=lambda: ResourceVector(water=0.1, minerals=0.1, assimilate=1.0)
    )
    stem_construction_cost: ResourceVector = field(
        default_factory=lambda: ResourceVector(water=0.1, minerals=0.1, assimilate=1.0)
    )
    leaf_construction_cost: ResourceVector = field(
        default_factory=lambda: ResourceVector(water=0.05, minerals=0.05, assimilate=0.25)
    )

    @property
    def effective_leaf_area(self) -> float:
        """Approximate single-leaf area in cm^2 from lobe geometry."""
        if self.number_of_lobes <= 0 or self.lobe_length <= 0:
            return 0.0
        lobe_width = self.lobe_length / max(self.lobe_aspect_ratio, 0.01)
        return self.number_of_lobes * self.lobe_length * lobe_width * _LOBE_SHAPE_FACTOR


@dataclass
class PlantBody:
    """A plant's crown and connected organ graph."""

    home: HexCell
    graph: PlantGraph

    @property
    def root_cells(self) -> set[HexCell]:
        return self.graph.root_cells


@dataclass
class Plant:
    id: int
    traits: TraitBundle = field(default_factory=TraitBundle)
    body: PlantBody | None = None
    reserves: ResourcePool = field(default_factory=ResourcePool)
    assimilate_allocation: AssimilateAllocation = field(default_factory=AssimilateAllocation)
    balance_sheet: PlantBalanceSheet | None = None

    def balance_sheet_for_tick(self, tick: int) -> PlantBalanceSheet:
        """Return the open ledger for *tick*, creating it from current reserves."""
        current = self.balance_sheet
        if current is not None and current.tick == tick:
            if current.closed:
                raise RuntimeError(f"plant {self.id} balance sheet for tick {tick} is closed")
            return current
        if current is not None and not current.closed:
            current.close(self.reserves.snapshot())
        self.balance_sheet = PlantBalanceSheet.open(
            tick=tick,
            reserves=self.reserves.snapshot(),
        )
        return self.balance_sheet


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
        plant_traits = traits or TraitBundle()
        if home is not None:
            graph = PlantGraph.create_seed(
                home,
                leaf_area=plant_traits.effective_leaf_area,
            )
            body = PlantBody(home=home, graph=graph)
        else:
            body = None
        plant = Plant(id=self._next_id, traits=plant_traits, body=body)
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
