"""Canonical protocol events used by the state reducer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CanonicalEvent:
    """Base canonical event type."""


@dataclass(frozen=True)
class SetAudiosyncEvent(CanonicalEvent):
    mode: str


@dataclass(frozen=True)
class SetAudiosyncStatusEvent(CanonicalEvent):
    synchronized: bool


@dataclass(frozen=True)
class SetBypassEvent(CanonicalEvent):
    state: bool


@dataclass(frozen=True)
class SetCurrentPresetEvent(CanonicalEvent):
    index: int


@dataclass(frozen=True)
class SetCurrentSourceEvent(CanonicalEvent):
    index: int


@dataclass(frozen=True)
class SetSourceFormatEvent(CanonicalEvent):
    format: str


@dataclass(frozen=True)
class SetDecoderEvent(CanonicalEvent):
    decoder: str
    upmixer: str


@dataclass(frozen=True)
class SetDimEvent(CanonicalEvent):
    state: bool


@dataclass(frozen=True)
class SetFeaturesEvent(CanonicalEvent):
    features: tuple[str, ...]


@dataclass(frozen=True)
class UpsertPresetEvent(CanonicalEvent):
    index: int
    name: str


@dataclass(frozen=True)
class ClearPresetsEvent(CanonicalEvent):
    pass


@dataclass(frozen=True)
class SetMuteEvent(CanonicalEvent):
    state: bool


@dataclass(frozen=True)
class UpsertSourceEvent(CanonicalEvent):
    index: int
    name: str


@dataclass(frozen=True)
class ClearSourcesEvent(CanonicalEvent):
    pass


@dataclass(frozen=True)
class SourcesChangedEvent(CanonicalEvent):
    pass


@dataclass(frozen=True)
class SetSamplingRateEvent(CanonicalEvent):
    rate: int


@dataclass(frozen=True)
class SetVolumeEvent(CanonicalEvent):
    volume: float


@dataclass(frozen=True)
class SetWelcomeEvent(CanonicalEvent):
    version: str
    id: str

