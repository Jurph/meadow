"""Tests for world contracts and value types."""

from meadow.hex import Axial
from meadow.world import (
    SIM_API_VERSION,
    PhaseResult,
    TurnContext,
    WorldMutator,
    WorldView,
)


class TestValueTypes:
    def test_turn_context_is_frozen(self):
        ctx = TurnContext(tick=0, weather_seed=42)
        assert ctx.tick == 0
        assert ctx.weather_seed == 42

    def test_phase_result_stores_diagnostics(self):
        r = PhaseResult(phase_name="FLOW", diagnostics={"total_water": 100.0})
        assert r.phase_name == "FLOW"
        assert r.diagnostics["total_water"] == 100.0

    def test_phase_result_diagnostics_default_none(self):
        r = PhaseResult(phase_name="LIGHT")
        assert r.diagnostics is None


class TestSIMAPIVersion:
    def test_version_is_positive_integer(self):
        assert isinstance(SIM_API_VERSION, int)
        assert SIM_API_VERSION >= 1


class TestProtocolsAreRuntimeCheckable:
    """Verify protocols can be used with isinstance at runtime."""

    def test_world_view_is_protocol(self):
        class FakeView:
            def moisture_at(self, h: Axial) -> float:
                return 0.0

            def nutrients_at(self, h: Axial) -> float:
                return 0.0

            def light_at(self, h: Axial) -> float:
                return 0.0

            def occupant_id_at(self, h: Axial) -> int | None:
                return None

        assert isinstance(FakeView(), WorldView)

    def test_world_mutator_is_protocol(self):
        class FakeMutator:
            def apply_flow_delta(
                self, h: Axial, moisture_delta: float, nutrient_delta: float
            ) -> None:
                pass

            def set_light(self, h: Axial, value: float) -> None:
                pass

            def set_occupant(self, h: Axial, plant_id: int | None) -> None:
                pass

        assert isinstance(FakeMutator(), WorldMutator)
