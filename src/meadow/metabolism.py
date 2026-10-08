"""Pure functions for plant photosynthesis and assimilate allocation."""

from __future__ import annotations

from meadow.plant import TraitBundle

LEAF_AREA_UNIT: float = 100.0


def compute_light_limited_assimilation(*, light: float, leaf_area: float) -> float:
    """Return potential assimilate from incident light and active leaf area."""
    if light <= 0.0 or leaf_area <= 0.0:
        return 0.0
    return light * leaf_area / LEAF_AREA_UNIT


def compute_photosynthesis(*, water: float, light: float, leaf_area: float) -> float:
    """Return actual assimilate constrained by light capture and delivered water."""
    potential = compute_light_limited_assimilation(light=light, leaf_area=leaf_area)
    return min(max(water, 0.0), potential)


def allocate_assimilate(assimilate: float, traits: TraitBundle) -> dict[str, float]:
    """Split spendable assimilate into organ and reproduction budgets."""
    total_weight = (
        traits.alloc_root + traits.alloc_leaf + traits.alloc_stem + traits.alloc_reproduce
    )
    if total_weight <= 0.0 or assimilate <= 0.0:
        return {"root": 0.0, "leaf": 0.0, "stem": 0.0, "reproduce": 0.0}
    return {
        "root": assimilate * traits.alloc_root / total_weight,
        "leaf": assimilate * traits.alloc_leaf / total_weight,
        "stem": assimilate * traits.alloc_stem / total_weight,
        "reproduce": assimilate * traits.alloc_reproduce / total_weight,
    }
