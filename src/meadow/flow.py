"""Flow phase: slope-driven moisture and nutrient redistribution.

v1 simplification: for each hex, outflow to in-bounds neighbors is proportional
to (slope dot direction-to-neighbor) * drainage.  Deltas are computed
simultaneously then applied, preserving mass conservation on a closed grid.

Physics assumptions documented for later refinement:
- No sub-tile pressure gradients.
- Nutrients travel proportionally with moisture (concentration-based).
- Boundary is closed: nothing flows off the edge.
"""

from __future__ import annotations

import numpy as np

from meadow.hex import DIRECTIONS, Axial
from meadow.phases import PhaseName
from meadow.world import PhaseResult, TurnContext, WorldMutator, WorldView
from meadow.world_state import WorldState


def _compute_flow_deltas(ws: WorldState) -> tuple[np.ndarray, np.ndarray]:
    """Return (moisture_deltas, nutrient_deltas) arrays preserving mass."""
    grid = ws.grid
    n = len(grid)
    m_delta = np.zeros(n, dtype=np.float64)
    n_delta = np.zeros(n, dtype=np.float64)

    for h in grid:
        i = ws._idx(h)
        m_here = ws.moisture[i]
        n_here = ws.nutrients[i]
        if m_here <= 0:
            continue

        sq = ws.slope_q[i]
        sr = ws.slope_r[i]
        drain = ws.drainage[i]

        weights: list[tuple[int, float]] = []
        total_weight = 0.0
        for d in DIRECTIONS:
            nb = Axial(h.q + d.q, h.r + d.r)
            if not grid.in_bounds(nb):
                continue
            dot = sq * d.q + sr * d.r
            if dot > 0:
                w = dot * drain
                weights.append((ws._idx(nb), w))
                total_weight += w

        if total_weight <= 0:
            continue

        outflow_frac = min(total_weight, 1.0)
        m_out = m_here * outflow_frac
        concentration = n_here / m_here if m_here > 0 else 0.0
        n_out = m_out * concentration

        m_delta[i] -= m_out
        n_delta[i] -= n_out
        for nb_idx, w in weights:
            share = w / total_weight
            m_delta[nb_idx] += m_out * share
            n_delta[nb_idx] += n_out * share

    return m_delta, n_delta


class FlowPhase:
    """Redistribute moisture and nutrients according to slope and drainage."""

    @property
    def name(self) -> PhaseName:
        return PhaseName.FLOW

    def execute(
        self, view: WorldView, mutator: WorldMutator, ctx: TurnContext
    ) -> PhaseResult:
        if not isinstance(mutator, WorldState):
            raise TypeError("FlowPhase requires a WorldState mutator")
        m_delta, n_delta = _compute_flow_deltas(mutator)
        mutator.moisture += m_delta
        mutator.nutrients += n_delta
        return PhaseResult(
            phase_name=self.name.name,
            diagnostics={
                "moisture_moved": float(np.sum(np.abs(m_delta)) / 2),
                "nutrient_moved": float(np.sum(np.abs(n_delta)) / 2),
            },
        )
