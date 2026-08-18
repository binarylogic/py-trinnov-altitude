"""Client state model for Trinnov Altitude."""

from __future__ import annotations

import re
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
    SetUpmixerModeEvent,
    SetVolumeEvent,
    SetWelcomeEvent,
    SourcesChangedEvent,
    UpsertPresetEvent,
    UpsertSourceEvent,
)
from trinnov_altitude.normalizer import normalize_message, select_profile
from trinnov_altitude.protocol import (
    Message,
    PresetMessage,
    PresetsClearMessage,
    SourceMessage,
    SourcesClearMessage,
)

GENERIC_SOURCE_NAME_PATTERN = re.compile(r"^source\s+\d+$", re.IGNORECASE)


def _is_generic_source_name(value: str) -> bool:
    return bool(GENERIC_SOURCE_NAME_PATTERN.match(value.strip()))


def _should_replace_source_name(existing: str | None, incoming: str) -> bool:
    if existing is None:
        return True
    return not (_is_generic_source_name(incoming) and not _is_generic_source_name(existing))


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
    _source_label_quality: dict[int, int] = field(default_factory=dict)
    _pending_presets: dict[int, str] | None = field(default=None, init=False, repr=False, compare=False)
    _pending_sources: dict[int, str] | None = field(default=None, init=False, repr=False, compare=False)
    _pending_source_label_quality: dict[int, int] | None = field(default=None, init=False, repr=False, compare=False)
    active_upmixer: str | None = None
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
        self._source_label_quality = {}
        self._pending_presets = None
        self._pending_sources = None
        self._pending_source_label_quality = None
        self.active_upmixer = None
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
        self._commit_completed_catalogs(message)
        profile = select_profile(self.features)
        for event in normalize_message(message, profile):
            self._apply_event(event)

    @property
    def has_pending_catalogs(self) -> bool:
        """Return whether a catalog refresh is still being assembled."""
        return self._pending_presets is not None or self._pending_sources is not None

    def commit_pending_catalogs(self) -> bool:
        """Publish complete staged catalogs after the protocol stream goes idle."""
        committed = False
        if self._pending_presets is not None:
            self._commit_pending_presets()
            committed = True
        if self._pending_sources is not None:
            self._commit_pending_sources()
            committed = True
        return committed

    def _commit_completed_catalogs(self, message: Message) -> None:
        if self._pending_presets is not None and not isinstance(message, (PresetsClearMessage, PresetMessage)):
            self._commit_pending_presets()

        if self._pending_sources is not None and not isinstance(message, (SourcesClearMessage, SourceMessage)):
            self._commit_pending_sources()

    def _commit_pending_presets(self) -> None:
        if self._pending_presets is None:
            return
        self.presets = self._pending_presets
        self._pending_presets = None
        self.preset = self.presets.get(self.current_preset_index) if self.current_preset_index is not None else None

    def _commit_pending_sources(self) -> None:
        if self._pending_sources is None:
            return
        self.sources = self._pending_sources
        self._source_label_quality = self._pending_source_label_quality or {}
        self._pending_sources = None
        self._pending_source_label_quality = None
        self.source = self.sources.get(self.current_source_index) if self.current_source_index is not None else None

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
            if event.index >= 0:
                self.current_source_index = event.index
                self.source = self.sources.get(event.index)
            elif self.current_source_index is None or self.current_source_index < 0:
                self.current_source_index = None
                self.source = None
            self._seen_current_source = True
        elif isinstance(event, SetFeaturesEvent):
            self.features = set(event.features)
        elif isinstance(event, SetDecoderEvent):
            self.decoder = event.decoder
            self.active_upmixer = event.active_upmixer
        elif isinstance(event, SetDimEvent):
            self.dim = event.state
        elif isinstance(event, SetUpmixerModeEvent):
            self.upmixer = event.mode
        elif isinstance(event, UpsertPresetEvent):
            presets = self._pending_presets if self._pending_presets is not None else self.presets
            presets[event.index] = event.name
            self._seen_preset_catalog = True
            if self._pending_presets is None and self.current_preset_index == event.index:
                self.preset = event.name
        elif isinstance(event, ClearPresetsEvent):
            self._pending_presets = {}
            self._seen_preset_catalog = True
        elif isinstance(event, SetMuteEvent):
            self.mute = event.state
        elif isinstance(event, UpsertSourceEvent):
            sources = self._pending_sources if self._pending_sources is not None else self.sources
            label_quality = (
                self._pending_source_label_quality
                if self._pending_source_label_quality is not None
                else self._source_label_quality
            )
            existing = sources.get(event.index)
            existing_quality = label_quality.get(event.index, -1)
            should_replace = event.quality > existing_quality
            if event.quality == existing_quality:
                should_replace = _should_replace_source_name(existing, event.name)
            if should_replace:
                sources[event.index] = event.name
                label_quality[event.index] = event.quality
            self._seen_source_catalog = True
            if self._pending_sources is None and self.current_source_index == event.index:
                self.source = sources.get(event.index)
        elif isinstance(event, ClearSourcesEvent):
            self._pending_sources = {}
            self._pending_source_label_quality = {}
            self._seen_source_catalog = True
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
            not self.has_pending_catalogs
            and self._seen_welcome
            and self._seen_current_preset
            and self._seen_current_source
            and (self._seen_preset_catalog or self.current_preset_index is not None)
            and (self._seen_source_catalog or self.current_source_index is not None)
        )
