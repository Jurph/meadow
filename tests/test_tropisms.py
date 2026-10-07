"""Tests for tropism scoring functions."""

from meadow.hex import Axial, HexCell
from meadow.tropisms import rank_growth_candidates, score_gravitropism, score_hydrotropism


class FakeView:
    """Minimal WorldView stub for tropism tests."""

    def __init__(self, moisture_map: dict[HexCell, float] | None = None):
        self._moisture = moisture_map or {}

    def moisture_at(self, h: HexCell) -> float:
        return self._moisture.get(h, 0.0)

    def nutrients_at(self, h: HexCell) -> float:
        return 0.0

    def light_at(self, h: HexCell) -> float:
        return 0.0

    def occupant_id_at(self, col: Axial) -> int | None:
        return None


class TestGravitropism:
    def test_root_prefers_lower_z(self):
        current = HexCell(5, 5, 0)
        down = HexCell(5, 5, -1)
        up = HexCell(5, 5, 1)
        assert score_gravitropism(down, current, is_root=True) > 0
        assert score_gravitropism(up, current, is_root=True) < 0

    def test_stem_prefers_higher_z(self):
        current = HexCell(5, 5, 0)
        up = HexCell(5, 5, 1)
        down = HexCell(5, 5, -1)
        assert score_gravitropism(up, current, is_root=False) > 0
        assert score_gravitropism(down, current, is_root=False) < 0

    def test_lateral_scores_zero(self):
        current = HexCell(5, 5, 0)
        lateral = HexCell(6, 5, 0)
        assert score_gravitropism(lateral, current, is_root=True) == 0.0

    def test_score_clamped(self):
        current = HexCell(5, 5, 0)
        far_down = HexCell(5, 5, -10)
        assert score_gravitropism(far_down, current, is_root=True) == 1.0


class TestHydrotropism:
    def test_wetter_cell_scores_higher(self):
        wet = HexCell(5, 5, -1)
        dry = HexCell(6, 5, 0)
        view = FakeView({wet: 10.0, dry: 1.0})
        assert score_hydrotropism(wet, view) > score_hydrotropism(dry, view)

    def test_zero_moisture_scores_zero(self):
        cell = HexCell(3, 3, 0)
        view = FakeView()
        assert score_hydrotropism(cell, view) == 0.0


class TestRankCandidates:
    def test_sorts_by_combined_score(self):
        current = HexCell(5, 5, 0)
        down = HexCell(5, 5, -1)
        lateral = HexCell(6, 5, 0)
        up = HexCell(5, 5, 1)
        view = FakeView()

        ranked = rank_growth_candidates(
            current, [up, lateral, down], view, is_root=True, gravity_weight=1.0, hydro_weight=0.0
        )
        assert ranked[0][0] == down
        assert ranked[-1][0] == up

    def test_hydrotropism_can_override_gravity(self):
        current = HexCell(5, 5, 0)
        dry_down = HexCell(5, 5, -1)
        wet_lateral = HexCell(6, 5, 0)
        view = FakeView({wet_lateral: 100.0, dry_down: 0.0})

        ranked = rank_growth_candidates(
            current,
            [dry_down, wet_lateral],
            view,
            is_root=True,
            gravity_weight=0.1,
            hydro_weight=1.0,
        )
        assert ranked[0][0] == wet_lateral

    def test_zero_weights_all_score_zero(self):
        current = HexCell(5, 5, 0)
        candidates = [HexCell(5, 5, -1), HexCell(6, 5, 0)]
        view = FakeView()
        ranked = rank_growth_candidates(
            current, candidates, view, is_root=True, gravity_weight=0.0, hydro_weight=0.0
        )
        assert all(score == 0.0 for _, score in ranked)
