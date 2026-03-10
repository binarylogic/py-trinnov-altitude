from trinnov_altitude.adapter import AltitudeStateAdapter, snapshot_from_state
from trinnov_altitude.protocol import (
    CurrentPresetMessage,
    CurrentSourceMessage,
    DecoderMessage,
    MuteMessage,
    PresetMessage,
    SourceMessage,
    UpmixerModeMessage,
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


def test_adapter_tracks_configured_and_active_upmixer_separately():
    state = _state_for_adapter()
    adapter = AltitudeStateAdapter()

    adapter.update(state)

    state.apply(DecoderMessage(nonaudio=False, playable=True, decoder="Dolby Atmos", upmixer="none"))
    state.apply(UpmixerModeMessage(mode="auto"))
    snapshot, deltas, events = adapter.update(state)

    changed_fields = {delta.field for delta in deltas}
    event_kinds = {event.kind for event in events}

    assert snapshot.active_upmixer == "none"
    assert snapshot.upmixer == "auto"
    assert "active_upmixer" in changed_fields
    assert "upmixer" in changed_fields
    assert "active_upmixer_changed" in event_kinds
    assert "upmixer_changed" in event_kinds
