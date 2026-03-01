"""Normalize raw protocol messages into canonical state events."""

from __future__ import annotations

from collections.abc import Iterable

from trinnov_altitude.canonical import (
    SOURCE_LABEL_QUALITY_OPTSOURCE,
    SOURCE_LABEL_QUALITY_PROFILE,
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
from trinnov_altitude.protocol import (
    AudiosyncMessage,
    AudiosyncStatusMessage,
    BypassMessage,
    CurrentPresetMessage,
    CurrentSourceFormatMessage,
    CurrentSourceMessage,
    DecoderMessage,
    DimMessage,
    IdentsMessage,
    Message,
    MetaPresetLoadedMessage,
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

PROFILE_DEFAULT = "default"
PROFILE_ALTITUDE_CI = "altitude_ci"


def select_profile(features: Iterable[str]) -> str:
    """Select quirk profile from protocol feature flags."""
    return PROFILE_ALTITUDE_CI if "altitude_ci" in set(features) else PROFILE_DEFAULT


def normalize_message(message: Message, profile: str) -> list[CanonicalEvent]:  # noqa: C901
    """Map one raw protocol message to zero or more canonical events."""
    if isinstance(message, AudiosyncMessage):
        return [SetAudiosyncEvent(mode=message.mode)]
    if isinstance(message, AudiosyncStatusMessage):
        return [SetAudiosyncStatusEvent(synchronized=message.synchronized)]
    if isinstance(message, BypassMessage):
        return [SetBypassEvent(state=message.state)]
    if isinstance(message, CurrentPresetMessage):
        return [SetCurrentPresetEvent(index=message.index)]
    if isinstance(message, CurrentSourceFormatMessage):
        return [SetSourceFormatEvent(format=message.format)]
    if isinstance(message, CurrentSourceMessage):
        return [SetCurrentSourceEvent(index=message.index)]
    if isinstance(message, DecoderMessage):
        return [SetDecoderEvent(decoder=message.decoder, upmixer=message.upmixer)]
    if isinstance(message, DimMessage):
        return [SetDimEvent(state=message.state)]
    if isinstance(message, IdentsMessage):
        return [SetFeaturesEvent(features=message.features)]
    if isinstance(message, MetaPresetLoadedMessage):
        if profile == PROFILE_ALTITUDE_CI:
            return [SetCurrentSourceEvent(index=message.index)]
        return [SetCurrentPresetEvent(index=message.index)]
    if isinstance(message, PresetMessage):
        return [UpsertPresetEvent(index=message.index, name=message.name)]
    if isinstance(message, PresetsClearMessage):
        return [ClearPresetsEvent()]
    if isinstance(message, MuteMessage):
        return [SetMuteEvent(state=message.state)]
    if isinstance(message, SourceMessage):
        quality = SOURCE_LABEL_QUALITY_OPTSOURCE if message.origin == "optsource" else SOURCE_LABEL_QUALITY_PROFILE
        return [UpsertSourceEvent(index=message.index, name=message.name, quality=quality)]
    if isinstance(message, SourcesClearMessage):
        return [ClearSourcesEvent()]
    if isinstance(message, SourcesChangedMessage):
        return [SourcesChangedEvent()]
    if isinstance(message, SamplingRateMessage):
        return [SetSamplingRateEvent(rate=message.rate)]
    if isinstance(message, VolumeMessage):
        return [SetVolumeEvent(volume=message.volume)]
    if isinstance(message, WelcomeMessage):
        return [SetWelcomeEvent(version=message.version, id=message.id)]
    return []
