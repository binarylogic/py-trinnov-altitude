from trinnov_altitude.adapter import AdapterEvent, AltitudeStateAdapter, StateDelta, snapshot_from_state
from trinnov_altitude.ha_bridge import HABridgeDispatcher, build_bridge_update, coordinator_payload, to_ha_events
from trinnov_altitude.protocol import CurrentPresetMessage, CurrentSourceMessage, PresetMessage, SourceMessage, WelcomeMessage
from trinnov_altitude.state import AltitudeState


def _state_for_bridge() -> AltitudeState:
    state = AltitudeState()
    state.apply(WelcomeMessage(version="4.3.2", id="42"))
    state.apply(PresetMessage(index=0, name="Builtin"))
    state.apply(SourceMessage(index=0, name="Apple TV"))
    state.apply(CurrentPresetMessage(index=0))
    state.apply(CurrentSourceMessage(index=0))
    return state


def test_coordinator_payload_contains_normalized_fields():
    snapshot = snapshot_from_state(_state_for_bridge())
    payload = coordinator_payload(snapshot)
    assert payload["available"] is True
    assert payload["version"] == "4.3.2"
    assert payload["device_id"] == "42"
    assert payload["preset"] == "Builtin"
    assert payload["source"] == "Apple TV"


def test_to_ha_events_maps_event_namespaces():
    mapped = to_ha_events([AdapterEvent(kind="source_changed", payload={"source": "Blu-ray"})])
    assert mapped[0].event_type == "trinnov_altitude.source_changed"
    assert mapped[0].event_data == {"source": "Blu-ray"}


def test_build_bridge_update_collects_changed_fields_and_events():
    snapshot = snapshot_from_state(_state_for_bridge())
    deltas = [StateDelta(field="source", old="Apple TV", new="Blu-ray")]
    events = [AdapterEvent(kind="source_changed", payload={"source": "Blu-ray"})]
    update = build_bridge_update(snapshot, deltas, events)

    assert update.changed_fields == ("source",)
    assert update.bus_events[0].event_type == "trinnov_altitude.source_changed"


def test_dispatcher_handles_update_and_emits_events():
    state = _state_for_bridge()
    adapter = AltitudeStateAdapter()
    snapshot, deltas, _ = adapter.update(state)

    emitted: list[tuple[str, dict[str, object]]] = []

    def emitter(event_type: str, event_data: dict[str, object]) -> None:
        emitted.append((event_type, event_data))

    dispatcher = HABridgeDispatcher(event_emitter=emitter)
    update = dispatcher.handle_adapter_update(
        snapshot,
        deltas,
        [AdapterEvent(kind="source_changed", payload={"source": "Blu-ray"})],
    )

    assert update.bus_events[0].event_type == "trinnov_altitude.source_changed"
    assert emitted == [("trinnov_altitude.source_changed", {"source": "Blu-ray"})]
