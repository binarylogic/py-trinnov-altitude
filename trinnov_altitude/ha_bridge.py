"""Helpers for adapting adapter output to Home Assistant-friendly payloads."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from trinnov_altitude.adapter import AdapterEvent, AltitudeSnapshot, StateDelta


@dataclass(frozen=True)
class HABusEvent:
    """Home Assistant event bus payload."""

    event_type: str
    event_data: dict[str, object]


@dataclass(frozen=True)
class HABridgeUpdate:
    """Coordinator update package derived from adapter output."""

    coordinator_data: dict[str, Any]
    changed_fields: tuple[str, ...]
    bus_events: tuple[HABusEvent, ...]


EventEmitter = Callable[[str, dict[str, object]], None]


def coordinator_payload(snapshot: AltitudeSnapshot) -> dict[str, Any]:
    """Build one coordinator payload dictionary from a snapshot."""
    return {
        "available": snapshot.synced,
        "version": snapshot.version,
        "device_id": snapshot.id,
        "volume_db": snapshot.volume,
        "mute": snapshot.mute,
        "dim": snapshot.dim,
        "bypass": snapshot.bypass,
        "preset": snapshot.preset,
        "source": snapshot.source,
        "sampling_rate_hz": snapshot.sampling_rate,
        "audiosync_mode": snapshot.audiosync,
        "audiosync_status": snapshot.audiosync_status,
        "decoder": snapshot.decoder,
        "upmixer": snapshot.upmixer,
        "source_format": snapshot.source_format,
        "current_preset_index": snapshot.current_preset_index,
        "current_source_index": snapshot.current_source_index,
        "presets": dict(snapshot.presets),
        "sources": dict(snapshot.sources),
    }


def to_ha_events(events: list[AdapterEvent]) -> tuple[HABusEvent, ...]:
    """Map adapter events to HA event bus objects."""
    mapped: list[HABusEvent] = []
    for event in events:
        mapped.append(HABusEvent(event_type=f"trinnov_altitude.{event.kind}", event_data=dict(event.payload)))
    return tuple(mapped)


def build_bridge_update(
    snapshot: AltitudeSnapshot,
    deltas: list[StateDelta],
    events: list[AdapterEvent],
) -> HABridgeUpdate:
    """Build one Home Assistant bridge update from adapter output."""
    return HABridgeUpdate(
        coordinator_data=coordinator_payload(snapshot),
        changed_fields=tuple(delta.field for delta in deltas),
        bus_events=to_ha_events(events),
    )


class HABridgeDispatcher:
    """Runtime helper that converts adapter updates and dispatches bus events."""

    def __init__(self, event_emitter: EventEmitter | None = None) -> None:
        self._event_emitter = event_emitter
        self.last_update: HABridgeUpdate | None = None

    def handle_adapter_update(
        self,
        snapshot: AltitudeSnapshot,
        deltas: list[StateDelta],
        events: list[AdapterEvent],
    ) -> HABridgeUpdate:
        update = build_bridge_update(snapshot, deltas, events)
        self.last_update = update

        if self._event_emitter is not None:
            for event in update.bus_events:
                self._event_emitter(event.event_type, event.event_data)

        return update
