"""Plant resource stocks, fluxes, and per-tick accounting."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isclose, isfinite

RESOURCE_EPSILON = 1e-12


@dataclass(frozen=True, slots=True)
class ResourceVector:
    """A non-negative quantity of each authoritative plant resource."""

    water: float = 0.0
    minerals: float = 0.0
    assimilate: float = 0.0

    def __post_init__(self) -> None:
        for name, value in (
            ("water", self.water),
            ("minerals", self.minerals),
            ("assimilate", self.assimilate),
        ):
            if not isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be non-negative finite, got {value}")

    def __add__(self, other: ResourceVector) -> ResourceVector:
        return ResourceVector(
            water=self.water + other.water,
            minerals=self.minerals + other.minerals,
            assimilate=self.assimilate + other.assimilate,
        )


@dataclass(slots=True)
class ResourcePool:
    """Mutable plant reserves with atomic, non-negative spending."""

    water: float = 0.0
    minerals: float = 0.0
    assimilate: float = 0.0

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        _ = ResourceVector(
            water=self.water,
            minerals=self.minerals,
            assimilate=self.assimilate,
        )

    def snapshot(self) -> ResourceVector:
        """Copy the current reserves into an immutable value."""
        return ResourceVector(
            water=self.water,
            minerals=self.minerals,
            assimilate=self.assimilate,
        )

    def credit(self, amount: ResourceVector) -> None:
        """Add a recorded non-negative source flux."""
        self.water += amount.water
        self.minerals += amount.minerals
        self.assimilate += amount.assimilate
        self._validate()

    def can_afford(self, cost: ResourceVector) -> bool:
        return (
            self.water + RESOURCE_EPSILON >= cost.water
            and self.minerals + RESOURCE_EPSILON >= cost.minerals
            and self.assimilate + RESOURCE_EPSILON >= cost.assimilate
        )

    def try_spend(self, cost: ResourceVector) -> bool:
        """Pay a complete cost or leave every reserve unchanged."""
        if not self.can_afford(cost):
            return False
        self.water = max(0.0, self.water - cost.water)
        self.minerals = max(0.0, self.minerals - cost.minerals)
        self.assimilate = max(0.0, self.assimilate - cost.assimilate)
        self._validate()
        return True


@dataclass(slots=True)
class AssimilateAllocation:
    """Persistent assimilate budgets for competing construction strategies."""

    root: float = 0.0
    leaf: float = 0.0
    stem: float = 0.0
    reproduce: float = 0.0

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        for category, amount in (
            ("root", self.root),
            ("leaf", self.leaf),
            ("stem", self.stem),
            ("reproduce", self.reproduce),
        ):
            if not isfinite(amount) or amount < 0.0:
                raise ValueError(f"{category} allocation must be non-negative finite, got {amount}")

    @property
    def total(self) -> float:
        return self.root + self.leaf + self.stem + self.reproduce

    def credit(self, amounts: Mapping[str, float]) -> None:
        expected = {"root", "leaf", "stem", "reproduce"}
        if set(amounts) != expected:
            raise ValueError(f"allocation must contain exactly {sorted(expected)}")
        for category, amount in amounts.items():
            if not isfinite(amount) or amount < 0.0:
                raise ValueError(f"{category} allocation must be non-negative finite, got {amount}")
        self.root += amounts["root"]
        self.leaf += amounts["leaf"]
        self.stem += amounts["stem"]
        self.reproduce += amounts["reproduce"]
        self._validate()

    def available(self, category: str) -> float:
        if category == "root":
            return self.root
        if category == "leaf":
            return self.leaf
        if category == "stem":
            return self.stem
        if category == "reproduce":
            return self.reproduce
        raise ValueError(f"unknown allocation category {category!r}")

    def try_spend(self, category: str, amount: float) -> bool:
        if not isfinite(amount) or amount < 0.0:
            raise ValueError(f"allocation spend must be non-negative finite, got {amount}")
        if self.available(category) + RESOURCE_EPSILON < amount:
            return False
        if category == "root":
            self.root = max(0.0, self.root - amount)
        elif category == "leaf":
            self.leaf = max(0.0, self.leaf - amount)
        elif category == "stem":
            self.stem = max(0.0, self.stem - amount)
        else:
            self.reproduce = max(0.0, self.reproduce - amount)
        return True


@dataclass(slots=True)
class ResourceFlux:
    """Potential and actual transfer totals for one named process."""

    potential: ResourceVector = field(default_factory=ResourceVector)
    actual: ResourceVector = field(default_factory=ResourceVector)
    limiting_factors: set[str] = field(default_factory=set)

    def record(
        self,
        *,
        potential: ResourceVector,
        actual: ResourceVector,
        limiter: str | None = None,
    ) -> None:
        pairs = (
            ("water", actual.water, potential.water),
            ("minerals", actual.minerals, potential.minerals),
            ("assimilate", actual.assimilate, potential.assimilate),
        )
        for resource, actual_value, potential_value in pairs:
            if actual_value > potential_value + RESOURCE_EPSILON:
                raise ValueError(f"actual {resource} flux cannot exceed potential flux")
        self.potential = self.potential + potential
        self.actual = self.actual + actual
        if limiter is not None:
            self.limiting_factors.add(limiter)


@dataclass(slots=True)
class PlantBalanceSheet:
    """Auditable sources, sinks, and reserves for one plant tick."""

    tick: int
    opening: ResourceVector
    root_uptake: ResourceFlux = field(default_factory=ResourceFlux)
    photosynthesis: ResourceFlux = field(default_factory=ResourceFlux)
    photosynthesis_water: float = 0.0
    construction_potential: ResourceVector = field(default_factory=ResourceVector)
    organ_proposals: dict[str, int] = field(default_factory=dict)
    construction: ResourceVector = field(default_factory=ResourceVector)
    organs_constructed: dict[str, int] = field(default_factory=dict)
    construction_limiting_factors: set[str] = field(default_factory=set)
    closing: ResourceVector = field(default_factory=ResourceVector)
    _closed: bool = False

    @classmethod
    def open(cls, *, tick: int, reserves: ResourceVector) -> PlantBalanceSheet:
        if tick < 0:
            raise ValueError(f"tick must be non-negative, got {tick}")
        return cls(tick=tick, opening=reserves, closing=reserves)

    @property
    def closed(self) -> bool:
        return self._closed

    def _require_open(self) -> None:
        if self._closed:
            raise RuntimeError("plant balance sheet is already closed")

    def record_root_uptake(
        self,
        *,
        potential: ResourceVector,
        actual: ResourceVector,
        limiter: str | None = None,
    ) -> None:
        self._require_open()
        self.root_uptake.record(potential=potential, actual=actual, limiter=limiter)

    def record_photosynthesis(
        self,
        *,
        potential: float,
        actual: float,
        water_used: float,
        limiter: str | None = None,
    ) -> None:
        self._require_open()
        if water_used < 0.0 or not isfinite(water_used):
            raise ValueError(f"water_used must be non-negative finite, got {water_used}")
        self.photosynthesis.record(
            potential=ResourceVector(assimilate=potential),
            actual=ResourceVector(assimilate=actual),
            limiter=limiter,
        )
        self.photosynthesis_water += water_used

    def record_construction_proposal(
        self,
        cost: ResourceVector,
        *,
        organ_type: str,
    ) -> None:
        self._require_open()
        self.construction_potential = self.construction_potential + cost
        self.organ_proposals[organ_type] = self.organ_proposals.get(organ_type, 0) + 1

    def record_construction(self, cost: ResourceVector, *, organ_type: str) -> None:
        self._require_open()
        next_count = self.organs_constructed.get(organ_type, 0) + 1
        if next_count > self.organ_proposals.get(organ_type, 0):
            raise ValueError(f"constructed {organ_type!r} without a recorded proposal")
        next_total = self.construction + cost
        if (
            next_total.water > self.construction_potential.water + RESOURCE_EPSILON
            or next_total.minerals > self.construction_potential.minerals + RESOURCE_EPSILON
            or next_total.assimilate > self.construction_potential.assimilate + RESOURCE_EPSILON
        ):
            raise ValueError("actual construction cost cannot exceed potential cost")
        self.construction = next_total
        self.organs_constructed[organ_type] = next_count

    def record_construction_blocked(self, *limiting_factors: str) -> None:
        self._require_open()
        self.construction_limiting_factors.update(limiting_factors)

    def close(self, reserves: ResourceVector) -> None:
        """Close the ledger only if all reserve changes are accounted for."""
        self._require_open()
        expected_water = (
            self.opening.water
            + self.root_uptake.actual.water
            - self.photosynthesis_water
            - self.construction.water
        )
        expected_minerals = (
            self.opening.minerals + self.root_uptake.actual.minerals - self.construction.minerals
        )
        expected_assimilate = (
            self.opening.assimilate
            + self.photosynthesis.actual.assimilate
            - self.construction.assimilate
        )
        if min(expected_water, expected_minerals, expected_assimilate) < -RESOURCE_EPSILON:
            raise ValueError("plant balance sheet records spending beyond available resources")
        expected = ResourceVector(
            water=max(0.0, expected_water),
            minerals=max(0.0, expected_minerals),
            assimilate=max(0.0, expected_assimilate),
        )
        pairs = (
            (expected.water, reserves.water),
            (expected.minerals, reserves.minerals),
            (expected.assimilate, reserves.assimilate),
        )
        if any(
            not isclose(expected_value, actual_value, rel_tol=1e-9, abs_tol=1e-9)
            for expected_value, actual_value in pairs
        ):
            raise ValueError(
                f"plant balance sheet does not reconcile: expected {expected}, got {reserves}"
            )
        self.closing = reserves
        self._closed = True
