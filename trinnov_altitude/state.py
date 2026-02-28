"""Client state model for Trinnov Altitude."""

from __future__ import annotations

from dataclasses import dataclass, field

from trinnov_altitude.canonical import (
    CanonicalEvent,
    ClearPresetsEvent,
    ClearSourcesEvent,
    SetAudiosyncEvent,
    SetAudiosyncStatusEvent,
    SetBypassEvent,
    SetCurrentPresetEvent,
    SetCurrentSourceEvent,
    SetDecoderEvent,
    SetDimEvent,
    SetFeaturesEvent,
    SetMuteEvent,
    SetSamplingRateEvent,
    SetSourceFormatEvent,
    SetVolumeEvent,
    SetWelcomeEvent,
    SourcesChangedEvent,
    UpsertPresetEvent,
    UpsertSourceEvent,
)
from trinnov_altitude.normalizer import normalize_message, select_profile
from trinnov_altitude.protocol import Message


@dataclass
class AltitudeState:
    audiosync: str | None = None
    audiosync_status: bool | None = None
    bypass: bool | None = None
    decoder: str | None = None
    dim: bool | None = None
    id: str | None = None
    mute: bool | None = None
    preset: str | None = None
    presets: dict[int, str] = field(default_factory=dict)
    sampling_rate: int | None = None
    source: str | None = None
    source_format: str | None = None
    sources: dict[int, str] = field(default_factory=dict)
    upmixer: str | None = None
    version: str | None = None
    volume: float | None = None

    current_preset_index: int | None = None
    current_source_index: int | None = None
    features: set[str] = field(default_factory=set)

    _seen_welcome: bool = False
    _seen_preset_catalog: bool = False
    _seen_source_catalog: bool = False
    _seen_current_preset: bool = False
    _seen_current_source: bool = False

    def reset_runtime_values(self) -> None:
        self.audiosync = None
        self.audiosync_status = None
        self.bypass = None
        self.decoder = None
        self.dim = None
        self.id = None
        self.mute = None
        self.preset = None
        self.presets = {}
        self.sampling_rate = None
        self.source = None
        self.source_format = None
        self.sources = {}
        self.upmixer = None
        self.version = None
        self.volume = None

        self.current_preset_index = None
        self.current_source_index = None
        self.features = set()

        self._seen_welcome = False
        self._seen_preset_catalog = False
        self._seen_source_catalog = False
        self._seen_current_preset = False
        self._seen_current_source = False

    def apply(self, message: Message) -> None:
        """Normalize one raw message and reduce it into state."""
        profile = select_profile(self.features)
        for event in normalize_message(message, profile):
            self._apply_event(event)

    def _apply_event(self, event: CanonicalEvent) -> None:  # noqa: C901
        if isinstance(event, SetAudiosyncEvent):
            self.audiosync = event.mode
        elif isinstance(event, SetAudiosyncStatusEvent):
            self.audiosync_status = event.synchronized
        elif isinstance(event, SetBypassEvent):
            self.bypass = event.state
        elif isinstance(event, SetCurrentPresetEvent):
            self.current_preset_index = event.index
            self.preset = self.presets.get(event.index)
            self._seen_current_preset = True
        elif isinstance(event, SetSourceFormatEvent):
            self.source_format = event.format
        elif isinstance(event, SetCurrentSourceEvent):
            self.current_source_index = event.index
            self.source = self.sources.get(event.index)
            self._seen_current_source = True
        elif isinstance(event, SetFeaturesEvent):
            self.features = set(event.features)
        elif isinstance(event, SetDecoderEvent):
            self.decoder = event.decoder
            self.upmixer = event.upmixer
        elif isinstance(event, SetDimEvent):
            self.dim = event.state
        elif isinstance(event, UpsertPresetEvent):
            self.presets[event.index] = event.name
            self._seen_preset_catalog = True
            if self.current_preset_index == event.index:
                self.preset = event.name
        elif isinstance(event, ClearPresetsEvent):
            self.presets = {}
            self._seen_preset_catalog = True
            if self.current_preset_index is not None:
                self.preset = None
        elif isinstance(event, SetMuteEvent):
            self.mute = event.state
        elif isinstance(event, UpsertSourceEvent):
            self.sources[event.index] = event.name
            self._seen_source_catalog = True
            if self.current_source_index == event.index:
                self.source = event.name
        elif isinstance(event, ClearSourcesEvent):
            self.sources = {}
            self._seen_source_catalog = True
            if self.current_source_index is not None:
                self.source = None
        elif isinstance(event, SourcesChangedEvent):
            # Informational marker emitted by some firmware variants.
            pass
        elif isinstance(event, SetSamplingRateEvent):
            self.sampling_rate = event.rate
        elif isinstance(event, SetVolumeEvent):
            self.volume = event.volume
        elif isinstance(event, SetWelcomeEvent):
            self.version = event.version
            self.id = event.id
            self._seen_welcome = True

    @property
    def synced(self) -> bool:
        return (
            self._seen_welcome
            and self._seen_current_preset
            and self._seen_current_source
            and (self._seen_preset_catalog or self.current_preset_index is not None)
            and (self._seen_source_catalog or self.current_source_index is not None)
        )
