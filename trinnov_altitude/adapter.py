"""Home Assistant-friendly state adapter for Trinnov Altitude."""

from __future__ import annotations

from dataclasses import dataclass, fields

from trinnov_altitude.state import AltitudeState


@dataclass(frozen=True)
class AltitudeSnapshot:
    """Immutable, comparison-friendly view of ``AltitudeState``."""

    synced: bool
    version: str | None
    id: str | None
    volume: float | None
    mute: bool | None
    dim: bool | None
    bypass: bool | None
    preset: str | None
    source: str | None
    sampling_rate: int | None
    audiosync: str | None
    audiosync_status: bool | None
    decoder: str | None
    upmixer: str | None
    source_format: str | None
    current_preset_index: int | None
    current_source_index: int | None
    presets: tuple[tuple[int, str], ...]
    sources: tuple[tuple[int, str], ...]


@dataclass(frozen=True)
class StateDelta:
    """One changed field between two snapshots."""

    field: str
    old: object
    new: object


@dataclass(frozen=True)
class AdapterEvent:
    """High-level event for integration consumers."""

    kind: str
    payload: dict[str, object]


def snapshot_from_state(state: AltitudeState) -> AltitudeSnapshot:
    """Build an immutable snapshot from runtime state."""
    return AltitudeSnapshot(
        synced=state.synced,
        version=state.version,
        id=state.id,
        volume=state.volume,
        mute=state.mute,
        dim=state.dim,
        bypass=state.bypass,
        preset=state.preset,
        source=state.source,
        sampling_rate=state.sampling_rate,
        audiosync=state.audiosync,
        audiosync_status=state.audiosync_status,
        decoder=state.decoder,
        upmixer=state.upmixer,
        source_format=state.source_format,
        current_preset_index=state.current_preset_index,
        current_source_index=state.current_source_index,
        presets=tuple(sorted(state.presets.items(), key=lambda item: item[0])),
        sources=tuple(sorted(state.sources.items(), key=lambda item: item[0])),
    )


class AltitudeStateAdapter:
    """Track snapshots and expose stable deltas/events for HA coordinators."""

    def __init__(self) -> None:
        self._last_snapshot: AltitudeSnapshot | None = None

    @property
    def last_snapshot(self) -> AltitudeSnapshot | None:
        return self._last_snapshot

    def update(self, state: AltitudeState) -> tuple[AltitudeSnapshot, list[StateDelta], list[AdapterEvent]]:
        snapshot = snapshot_from_state(state)
        previous = self._last_snapshot
        self._last_snapshot = snapshot

        if previous is None:
            return snapshot, [], []

        deltas = _build_deltas(previous, snapshot)
        events = _build_events(previous, snapshot)
        return snapshot, deltas, events


def _build_deltas(previous: AltitudeSnapshot, current: AltitudeSnapshot) -> list[StateDelta]:
    deltas: list[StateDelta] = []
    for field_def in fields(AltitudeSnapshot):
        name = field_def.name
        old_value = getattr(previous, name)
        new_value = getattr(current, name)
        if old_value != new_value:
            deltas.append(StateDelta(field=name, old=old_value, new=new_value))
    return deltas


def _change_event(kind: str, old: object, new: object, payload_key: str = "value") -> AdapterEvent | None:
    if new is None or new == old:
        return None
    return AdapterEvent(kind=kind, payload={payload_key: new})


def _build_events(previous: AltitudeSnapshot, current: AltitudeSnapshot) -> list[AdapterEvent]:
    events: list[AdapterEvent] = []

    for event in (
        _change_event("volume_changed", previous.volume, current.volume, "db"),
        _change_event("mute_changed", previous.mute, current.mute, "mute"),
        _change_event("dim_changed", previous.dim, current.dim, "dim"),
        _change_event("bypass_changed", previous.bypass, current.bypass, "bypass"),
        _change_event("preset_changed", previous.preset, current.preset, "preset"),
        _change_event("source_changed", previous.source, current.source, "source"),
        _change_event("sampling_rate_changed", previous.sampling_rate, current.sampling_rate, "hz"),
        _change_event("decoder_changed", previous.decoder, current.decoder, "decoder"),
        _change_event("upmixer_changed", previous.upmixer, current.upmixer, "upmixer"),
    ):
        if event is not None:
            events.append(event)

    return events
