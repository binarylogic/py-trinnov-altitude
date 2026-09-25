"""Protocol parser and message models for Trinnov Altitude."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

AUDIO_FORMAT_MAPPING = {
    "ATMOS TrueHD": "Dolby Atmos/Dolby TrueHD",
    "DTS:X MA": "DTS:X Master Audio",
    "DTS-HD MA": "DTS-HD Master Audio",
    "ATMOS DD+": "Dolby Atmos/Dolby Digital Plus",
    "DD": "Dolby Digital",
    "TrueHD": "Dolby TrueHD",
}


_AUDIO_FORMAT_LABELS = {token.casefold(): label for token, label in AUDIO_FORMAT_MAPPING.items()}


@dataclass(frozen=True)
class Message:
    """Base message type."""


@dataclass(frozen=True)
class AudiosyncMessage(Message):
    mode: str


@dataclass(frozen=True)
class AudiosyncStatusMessage(Message):
    synchronized: bool


@dataclass(frozen=True)
class BypassMessage(Message):
    state: bool


@dataclass(frozen=True)
class CurrentPresetMessage(Message):
    index: int


@dataclass(frozen=True)
class CurrentSourceFormatMessage(Message):
    format: str


@dataclass(frozen=True)
class CurrentSourceMessage(Message):
    index: int


@dataclass(frozen=True)
class IdentsMessage(Message):
    features: tuple[str, ...]


@dataclass(frozen=True)
class MetaPresetLoadedMessage(Message):
    index: int


@dataclass(frozen=True)
class DecoderMessage(Message):
    nonaudio: bool
    playable: bool
    decoder: str
    upmixer: str


@dataclass(frozen=True)
class DimMessage(Message):
    state: bool


@dataclass(frozen=True)
class UpmixerModeMessage(Message):
    mode: str


@dataclass(frozen=True)
class ErrorMessage(Message):
    error: str


@dataclass(frozen=True)
class IgnoredMessage(Message):
    raw_message: str


@dataclass(frozen=True)
class ByeMessage(Message):
    pass


@dataclass(frozen=True)
class MuteMessage(Message):
    state: bool


@dataclass(frozen=True)
class OKMessage(Message):
    pass


@dataclass(frozen=True)
class PresetMessage(Message):
    index: int
    name: str


@dataclass(frozen=True)
class PresetsClearMessage(Message):
    pass


@dataclass(frozen=True)
class SourcesChangedMessage(Message):
    pass


@dataclass(frozen=True)
class SamplingRateMessage(Message):
    rate: int


@dataclass(frozen=True)
class SourceMessage(Message):
    index: int
    name: str
    origin: Literal["profile", "optsource"] = "profile"


@dataclass(frozen=True)
class SourcesClearMessage(Message):
    pass


@dataclass(frozen=True)
class SpeakerInfoMessage(Message):
    speaker_number: int
    radius: float
    theta: float
    phi: float


@dataclass(frozen=True)
class StartRunningMessage(Message):
    pass


@dataclass(frozen=True)
class UnknownMessage(Message):
    raw_message: str


@dataclass(frozen=True)
class VolumeMessage(Message):
    volume: float


@dataclass(frozen=True)
class WelcomeMessage(Message):
    version: str
    id: str


Rule = tuple[re.Pattern[str], Callable[[re.Match[str]], Message]]


def _to_audiosync(match: re.Match[str]) -> Message:
    return AudiosyncMessage(match.group(1))


def _to_audiosync_status(match: re.Match[str]) -> Message:
    return AudiosyncStatusMessage(bool(int(match.group(1))))


def _to_bypass(match: re.Match[str]) -> Message:
    return BypassMessage(bool(int(match.group(1))))


def _to_current_preset(match: re.Match[str]) -> Message:
    return CurrentPresetMessage(int(match.group(1)))


def _to_meta_preset_loaded(match: re.Match[str]) -> Message:
    return MetaPresetLoadedMessage(int(match.group(1)))


def _to_current_source(match: re.Match[str]) -> Message:
    return CurrentSourceMessage(int(match.group(1)))


def _to_current_source_format(match: re.Match[str]) -> Message:
    return CurrentSourceFormatMessage(match.group(1))


def _to_decoder(match: re.Match[str]) -> Message:
    decoder = match.group(3)
    return DecoderMessage(
        nonaudio=bool(int(match.group(1))),
        playable=bool(int(match.group(2))),
        decoder=_AUDIO_FORMAT_LABELS.get(decoder.casefold(), decoder),
        upmixer=match.group(4),
    )


def _to_dim(match: re.Match[str]) -> Message:
    return DimMessage(bool(int(match.group(1))))


def _to_upmixer_mode(match: re.Match[str]) -> Message:
    return UpmixerModeMessage(mode=match.group(1).strip())


def _to_idents(match: re.Match[str]) -> Message:
    features = tuple(token.strip() for token in match.group(1).split(",") if token.strip())
    return IdentsMessage(features=features)


def _to_error(match: re.Match[str]) -> Message:
    return ErrorMessage(match.group(1))


def _to_ignored(match: re.Match[str]) -> Message:
    return IgnoredMessage(match.group(0))


def _to_bye(match: re.Match[str]) -> Message:
    return ByeMessage()


def _to_preset(match: re.Match[str]) -> Message:
    return PresetMessage(int(match.group(1)), match.group(2))


def _to_presets_clear(match: re.Match[str]) -> Message:
    return PresetsClearMessage()


def _to_mute(match: re.Match[str]) -> Message:
    return MuteMessage(bool(int(match.group(1))))


def _to_ok(match: re.Match[str]) -> Message:
    return OKMessage()


def _to_source(match: re.Match[str]) -> Message:
    return SourceMessage(int(match.group(1)), match.group(2), origin="profile")


def _to_sources_clear(match: re.Match[str]) -> Message:
    return SourcesClearMessage()


def _to_sources_changed(match: re.Match[str]) -> Message:
    return SourcesChangedMessage()


def _to_speaker_info(match: re.Match[str]) -> Message:
    return SpeakerInfoMessage(
        speaker_number=int(match.group(1)),
        radius=float(match.group(2)),
        theta=float(match.group(3)),
        phi=float(match.group(4)),
    )


def _to_srate(match: re.Match[str]) -> Message:
    return SamplingRateMessage(int(match.group(1)))


def _to_start_running(match: re.Match[str]) -> Message:
    return StartRunningMessage()


def _to_volume(match: re.Match[str]) -> Message:
    return VolumeMessage(float(match.group(1)))


def _to_welcome(match: re.Match[str]) -> Message:
    return WelcomeMessage(version=match.group(1), id=match.group(2))


def _to_optsource(match: re.Match[str]) -> Message:
    return SourceMessage(int(match.group(1)), match.group(2).strip(), origin="optsource")


def _pattern(expression: str) -> re.Pattern[str]:
    """Match ASCII protocol keywords without changing captured payload text."""
    return re.compile(expression, re.IGNORECASE | re.ASCII)


PARSER_RULES: tuple[Rule, ...] = (
    (_pattern(r"^AUDIOSYNC STATUS\s(0|1)$"), _to_audiosync_status),
    (_pattern(r"^AUDIOSYNC_STATUS\s(0|1)$"), _to_audiosync_status),
    (_pattern(r"^AUDIOSYNC\s(.*)$"), _to_audiosync),
    (_pattern(r"^BYPASS\s(0|1)$"), _to_bypass),
    (_pattern(r"^BYE$"), _to_bye),
    (_pattern(r"^CURRENT_PRESET\s(-?\d+)$"), _to_current_preset),
    (_pattern(r"^META_PRESET_LOADED\s(-?\d+)$"), _to_meta_preset_loaded),
    (_pattern(r"^CURRENT_PROFILE\s(-?\d+)$"), _to_current_source),
    # Live Altitude 32 traces emit bare SOURCE <n> during source changes even when the
    # active user-facing input remains on a different CURRENT_PROFILE. Treat it as noise
    # until proven otherwise; CURRENT_PROFILE is the authoritative active input signal.
    (_pattern(r"^SOURCE\s(-?\d+)$"), _to_ignored),
    (_pattern(r"^CURRENT_SOURCE_FORMAT_NAME\s(.*)$"), _to_current_source_format),
    (_pattern(r"^CURRENT_SOURCE_CHANNELS_ORDER_IS_DCI\s(0|1)$"), _to_ignored),
    (_pattern(r"^CURRENT_SOURCE_CHANNELS_ORDER\s(.*)$"), _to_ignored),
    (_pattern(r"^DECODER NONAUDIO (\d+) PLAYABLE (\d+) DECODER (.*) UPMIXER (.*)$"), _to_decoder),
    (_pattern(r"^DIM\s(-?\d+)$"), _to_dim),
    (_pattern(r"^DISPLAY_VOLUME\s(-?\d+(?:\.\d+)?)$"), _to_ignored),
    (_pattern(r"^UPMIXER\s(.*)$"), _to_upmixer_mode),
    (_pattern(r"^IDENTS\s(.*)$"), _to_idents),
    (_pattern(r"^ERROR: (.*)$"), _to_error),
    (_pattern(r"^CALIBRATION_DONE$"), _to_ignored),
    (_pattern(r"^LABEL\s(-?\d+): (.*)$"), _to_preset),
    (_pattern(r"^LABELS_CLEAR$"), _to_presets_clear),
    (_pattern(r"^MUTE\s(0|1)$"), _to_mute),
    (_pattern(r"^MON_VOL\s(-?\d+(?:\.\d+)?)$"), _to_ignored),
    (_pattern(r"^MON_REMOTE_[A-Z0-9_]+\s(-?\d+)$"), _to_ignored),
    (_pattern(r"^OK$"), _to_ok),
    (_pattern(r"^PROFILE\s(-?\d+)$"), _to_current_source),
    (_pattern(r"^PROFILE\s(-?\d+): (.*)$"), _to_source),
    # Seen on some Altitude CI builds; includes source id/name list entries.
    (_pattern(r"^OPTSOURCE\s(-?\d+)\s(.*?)\s+OK$"), _to_optsource),
    (_pattern(r"^OPTSOURCE\s(-?\d+)\s(.*)$"), _to_optsource),
    (_pattern(r"^PROFILES_CLEAR$"), _to_sources_clear),
    (_pattern(r"^REMAPPING_MODE\s(.*)$"), _to_ignored),
    (_pattern(r"^SOURCES_CHANGED$"), _to_sources_changed),
    (
        _pattern(r"^SPEAKER_INFO\s(\d+)\s(-?\d+(?:\.\d+)?)\s(-?\d+(?:\.\d+)?)\s(-?\d+(?:\.\d+)?)$"),
        _to_speaker_info,
    ),
    (_pattern(r"^SRATE\s(\d+)$"), _to_srate),
    (_pattern(r"^START_RUNNING$"), _to_start_running),
    (_pattern(r"^VOLUME\s(-?\d+(?:\.\d+)?)$"), _to_volume),
    (_pattern(r"^Welcome on Trinnov Optimizer \(Version (\S+), ID (\d+)\)$"), _to_welcome),
)


def parse_message(line: str) -> Message:
    """Parse one line from the Trinnov protocol stream."""
    for pattern, parser in PARSER_RULES:
        match = pattern.match(line)
        if match is not None:
            return parser(match)
    return UnknownMessage(line)
