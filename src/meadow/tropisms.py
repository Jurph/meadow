"""Tropism scoring: pure functions for growth direction preference.

Roots and stems choose which neighboring cell to grow into based on
weighted tropism scores. Inspired by the weighted-sum-of-tropisms
model from Mußmann et al. 2024 (Swarm Grammar root simulation).

Gravitropism: roots prefer downward (lower z), stems prefer upward.
Hydrotropism: roots grow toward moisture.
"""

from __future__ import annotations

from meadow.hex import HexCell
from meadow.world import WorldView


def score_gravitropism(candidate: HexCell, current: HexCell, is_root: bool) -> float:
    """Score a candidate cell by gravitropic preference.

    Roots prefer lower z (score increases as candidate.z decreases).
    Stems prefer higher z. Lateral moves (same z) score 0.
    Returns a value in [-1, 1].
    """
    dz = current.z - candidate.z if is_root else candidate.z - current.z
    return max(-1.0, min(1.0, float(dz)))


def score_hydrotropism(candidate: HexCell, view: WorldView) -> float:
    """Score a candidate cell by moisture availability."""
    return view.moisture_at(candidate)


def rank_growth_candidates(
    current: HexCell,
    candidates: list[HexCell],
    view: WorldView,
    is_root: bool,
    gravity_weight: float = 1.0,
    hydro_weight: float = 0.3,
) -> list[tuple[HexCell, float]]:
    """Score and rank candidate cells by combined tropism weights.

    Returns list of (cell, score) sorted descending by score.
    """
    scored: list[tuple[HexCell, float]] = []
    for c in candidates:
        g = score_gravitropism(c, current, is_root) * gravity_weight
        h = score_hydrotropism(c, view) * hydro_weight
        scored.append((c, g + h))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
