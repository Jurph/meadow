"""Pure functions for plant metabolism.

Photosynthesis: Liebig's law — output limited by the scarcest input.
Allocation: split cellulose by normalized trait weights.

Physics simplifications (v1):
- 100 cm^2 of leaf area captures all light from one hex (LEAF_AREA_UNIT).
- Moisture and nutrients consumed 1:1 with cellulose produced.
"""

from __future__ import annotations

from meadow.plant import TraitBundle

LEAF_AREA_UNIT: float = 100.0


def compute_photosynthesis(
    moisture: float, nutrients: float, light: float, leaf_area: float
) -> float:
    """Cellulose produced from available resources (Liebig's law)."""
    effective_light = light * leaf_area / LEAF_AREA_UNIT
    return min(moisture, nutrients, effective_light)


def allocate_cellulose(cellulose: float, traits: TraitBundle) -> dict[str, float]:
    """Split cellulose into growth categories by trait weights."""
    total_w = traits.alloc_root + traits.alloc_leaf + traits.alloc_stem + traits.alloc_reproduce
    if total_w <= 0 or cellulose <= 0:
        return {"root": 0.0, "leaf": 0.0, "stem": 0.0, "reproduce": 0.0}
    return {
        "root": cellulose * traits.alloc_root / total_w,
        "leaf": cellulose * traits.alloc_leaf / total_w,
        "stem": cellulose * traits.alloc_stem / total_w,
        "reproduce": cellulose * traits.alloc_reproduce / total_w,
    }
