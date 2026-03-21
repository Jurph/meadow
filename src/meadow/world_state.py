"""Concrete world state backed by numpy arrays.

Implements both WorldView (reads) and WorldMutator (writes).
Arrays are flat, indexed by (q * grid.height + r).
"""

from __future__ import annotations

import numpy as np

from meadow.hex import Axial, HexGrid

_NO_OCCUPANT: int = -1


class WorldState:
    """Numpy-backed tile fields for a HexGrid."""

    def __init__(self, grid: HexGrid) -> None:
        self.grid = grid
        n = len(grid)
        self.moisture = np.zeros(n, dtype=np.float64)
        self.nutrients = np.zeros(n, dtype=np.float64)
        self.light = np.zeros(n, dtype=np.float64)
        self.drainage = np.ones(n, dtype=np.float64)
        self.slope_q = np.zeros(n, dtype=np.float64)
        self.slope_r = np.zeros(n, dtype=np.float64)
        self._occupants = np.full(n, _NO_OCCUPANT, dtype=np.int64)

    def _idx(self, h: Axial) -> int:
        return h.q * self.grid.height + h.r

    # --- WorldView ---

    def moisture_at(self, h: Axial) -> float:
        return float(self.moisture[self._idx(h)])

    def nutrients_at(self, h: Axial) -> float:
        return float(self.nutrients[self._idx(h)])

    def light_at(self, h: Axial) -> float:
        return float(self.light[self._idx(h)])

    def occupant_id_at(self, h: Axial) -> int | None:
        v = int(self._occupants[self._idx(h)])
        return None if v == _NO_OCCUPANT else v

    # --- WorldMutator ---

    def apply_flow_delta(
        self, h: Axial, moisture_delta: float, nutrient_delta: float
    ) -> None:
        i = self._idx(h)
        self.moisture[i] += moisture_delta
        self.nutrients[i] += nutrient_delta

    def set_light(self, h: Axial, value: float) -> None:
        self.light[self._idx(h)] = value

    def set_occupant(self, h: Axial, plant_id: int | None) -> None:
        self._occupants[self._idx(h)] = _NO_OCCUPANT if plant_id is None else plant_id

    # --- Aggregate queries (for diagnostics / tests) ---

    def total_moisture(self) -> float:
        return float(np.sum(self.moisture))

    def total_nutrients(self) -> float:
        return float(np.sum(self.nutrients))
