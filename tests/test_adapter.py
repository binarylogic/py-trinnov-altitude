from trinnov_altitude.adapter import AltitudeStateAdapter, snapshot_from_state
from trinnov_altitude.protocol import (
    CurrentPresetMessage,
    CurrentSourceMessage,
    MuteMessage,
    PresetMessage,
    SourceMessage,
    WelcomeMessage,
)
from trinnov_altitude.state import AltitudeState


def _state_for_adapter() -> AltitudeState:
    state = AltitudeState()
    state.apply(WelcomeMessage(version="4.3.2", id="42"))
    state.apply(PresetMessage(index=0, name="Builtin"))
    state.apply(SourceMessage(index=0, name="Apple TV"))
    state.apply(CurrentPresetMessage(index=0))
    state.apply(CurrentSourceMessage(index=0))
    return state


def test_snapshot_from_state_collects_expected_fields():
    snapshot = snapshot_from_state(_state_for_adapter())
    assert snapshot.synced is True
    assert snapshot.version == "4.3.2"
    assert snapshot.id == "42"
    assert snapshot.preset == "Builtin"
    assert snapshot.source == "Apple TV"


def test_adapter_emits_deltas_and_events():
    state = _state_for_adapter()
    adapter = AltitudeStateAdapter()

    _, first_deltas, first_events = adapter.update(state)
    assert first_deltas == []
    assert first_events == []

    state.apply(MuteMessage(state=True))
    _, deltas, events = adapter.update(state)

    changed_fields = {delta.field for delta in deltas}
    event_kinds = {event.kind for event in events}

    assert "mute" in changed_fields
    assert "mute_changed" in event_kinds
