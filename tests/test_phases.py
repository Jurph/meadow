"""Tests for phase contracts and ordering."""

from meadow.hex import Axial, HexCell
from meadow.phases import PHASE_ORDER, NoOpPhase, Phase, PhaseName
from meadow.world import PhaseResult, TurnContext


class TestPhaseName:
    def test_phase_order_has_six_phases(self):
        assert len(PHASE_ORDER) == 6

    def test_phase_order_matches_vision_doc_sequence(self):
        names = [p.name for p in PHASE_ORDER]
        assert names == ["WEATHER", "FLOW", "LIGHT", "UPTAKE", "DEPLETION", "GROWTH"]


class TestNoOpPhase:
    def test_satisfies_phase_protocol(self):
        phase = NoOpPhase(PhaseName.WEATHER)
        assert isinstance(phase, Phase)

    def test_execute_returns_phase_result(self):
        phase = NoOpPhase(PhaseName.FLOW)

        class StubView:
            def moisture_at(self, h: HexCell) -> float:
                return 0.0

            def nutrients_at(self, h: HexCell) -> float:
                return 0.0

            def light_at(self, h: HexCell) -> float:
                return 0.0

            def occupant_id_at(self, col: Axial) -> int | None:
                return None

        class StubMutator:
            def apply_flow_delta(self, h: HexCell, md: float, nd: float) -> None:
                pass

            def set_light(self, h: HexCell, v: float) -> None:
                pass

            def set_occupant(self, col: Axial, pid: int | None) -> None:
                pass

        ctx = TurnContext(tick=0, weather_seed=1)
        result = phase.execute(StubView(), StubMutator(), ctx)
        assert isinstance(result, PhaseResult)
        assert result.phase_name == "FLOW"

    def test_name_property_returns_assigned_name(self):
        phase = NoOpPhase(PhaseName.LIGHT)
        assert phase.name == PhaseName.LIGHT
