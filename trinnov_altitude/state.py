"""Client state model for Trinnov Altitude."""

from __future__ import annotations

from dataclasses import dataclass, field

from trinnov_altitude.protocol import (
    AudiosyncMessage,
    AudiosyncStatusMessage,
    BypassMessage,
    CurrentPresetMessage,
    CurrentSourceFormatMessage,
    CurrentSourceMessage,
    DecoderMessage,
    DimMessage,
    Message,
    MuteMessage,
    PresetMessage,
    PresetsClearMessage,
    SamplingRateMessage,
    SourceMessage,
    SourcesChangedMessage,
    SourcesClearMessage,
    VolumeMessage,
    WelcomeMessage,
)


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

        self._seen_welcome = False
        self._seen_preset_catalog = False
        self._seen_source_catalog = False
        self._seen_current_preset = False
        self._seen_current_source = False

    def apply(self, message: Message) -> None:  # noqa: C901
        if isinstance(message, AudiosyncMessage):
            self.audiosync = message.mode
        elif isinstance(message, AudiosyncStatusMessage):
            self.audiosync_status = message.synchronized
        elif isinstance(message, BypassMessage):
            self.bypass = message.state
        elif isinstance(message, CurrentPresetMessage):
            self.current_preset_index = message.index
            self.preset = self.presets.get(message.index)
            self._seen_current_preset = True
        elif isinstance(message, CurrentSourceFormatMessage):
            self.source_format = message.format
        elif isinstance(message, CurrentSourceMessage):
            self.current_source_index = message.index
            self.source = self.sources.get(message.index)
            self._seen_current_source = True
        elif isinstance(message, DecoderMessage):
            self.decoder = message.decoder
            self.upmixer = message.upmixer
        elif isinstance(message, DimMessage):
            self.dim = message.state
        elif isinstance(message, PresetMessage):
            self.presets[message.index] = message.name
            self._seen_preset_catalog = True
            if self.current_preset_index == message.index:
                self.preset = message.name
        elif isinstance(message, PresetsClearMessage):
            self.presets = {}
            self._seen_preset_catalog = True
            if self.current_preset_index is not None:
                self.preset = None
        elif isinstance(message, MuteMessage):
            self.mute = message.state
        elif isinstance(message, SourceMessage):
            self.sources[message.index] = message.name
            self._seen_source_catalog = True
            if self.current_source_index == message.index:
                self.source = message.name
        elif isinstance(message, SourcesClearMessage):
            self.sources = {}
            self._seen_source_catalog = True
            if self.current_source_index is not None:
                self.source = None
        elif isinstance(message, SourcesChangedMessage):
            # Informational marker emitted by some firmware variants.
            pass
        elif isinstance(message, SamplingRateMessage):
            self.sampling_rate = message.rate
        elif isinstance(message, VolumeMessage):
            self.volume = message.volume
        elif isinstance(message, WelcomeMessage):
            self.version = message.version
            self.id = message.id
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
