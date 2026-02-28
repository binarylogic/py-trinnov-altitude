"""Protocol parser and message models for Trinnov Altitude."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

AUDIO_FORMAT_MAPPING = {
    "ATMOS TrueHD": "Dolby Atmos/Dolby TrueHD",
    "DTS:X MA": "DTS:X Master Audio",
    "DTS-HD MA": "DTS-HD Master Audio",
    "ATMOS DD+": "Dolby Atmos/Dolby Digital Plus",
    "DD": "Dolby Digital",
    "TrueHD": "Dolby TrueHD",
}


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
class DecoderMessage(Message):
    nonaudio: bool
    playable: bool
    decoder: str
    upmixer: str


@dataclass(frozen=True)
class DimMessage(Message):
    state: bool


@dataclass(frozen=True)
class ErrorMessage(Message):
    error: str


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
class SamplingRateMessage(Message):
    rate: int


@dataclass(frozen=True)
class SourceMessage(Message):
    index: int
    name: str


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


def _to_current_source(match: re.Match[str]) -> Message:
    return CurrentSourceMessage(int(match.group(1)))


def _to_current_source_format(match: re.Match[str]) -> Message:
    return CurrentSourceFormatMessage(match.group(1))


def _to_decoder(match: re.Match[str]) -> Message:
    decoder = match.group(3)
    return DecoderMessage(
        nonaudio=bool(int(match.group(1))),
        playable=bool(int(match.group(2))),
        decoder=AUDIO_FORMAT_MAPPING.get(decoder, decoder),
        upmixer=match.group(4),
    )


def _to_dim(match: re.Match[str]) -> Message:
    return DimMessage(bool(int(match.group(1))))


def _to_error(match: re.Match[str]) -> Message:
    return ErrorMessage(match.group(1))


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
    return SourceMessage(int(match.group(1)), match.group(2))


def _to_sources_clear(match: re.Match[str]) -> Message:
    return SourcesClearMessage()


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


PARSER_RULES: tuple[Rule, ...] = (
    (re.compile(r"^AUDIOSYNC STATUS\s(0|1)$"), _to_audiosync_status),
    (re.compile(r"^AUDIOSYNC\s(.*)$"), _to_audiosync),
    (re.compile(r"^BYPASS\s(0|1)$"), _to_bypass),
    (re.compile(r"^BYE$"), _to_bye),
    (re.compile(r"^CURRENT_PRESET\s(-?\d+)$"), _to_current_preset),
    (re.compile(r"^META_PRESET_LOADED\s(-?\d+)$"), _to_current_preset),
    (re.compile(r"^CURRENT_PROFILE\s(-?\d+)$"), _to_current_source),
    (re.compile(r"^CURRENT_SOURCE_FORMAT_NAME\s(.*)$"), _to_current_source_format),
    (re.compile(r"^DECODER NONAUDIO (\d+) PLAYABLE (\d+) DECODER (.*) UPMIXER (.*)$"), _to_decoder),
    (re.compile(r"^DIM\s(-?\d+)$"), _to_dim),
    (re.compile(r"^ERROR: (.*)$"), _to_error),
    (re.compile(r"^LABEL\s(-?\d+): (.*)$"), _to_preset),
    (re.compile(r"^LABELS_CLEAR$"), _to_presets_clear),
    (re.compile(r"^MUTE\s(0|1)$"), _to_mute),
    (re.compile(r"^OK$"), _to_ok),
    (re.compile(r"^PROFILE\s(-?\d+)$"), _to_current_source),
    (re.compile(r"^PROFILE\s(-?\d+): (.*)$"), _to_source),
    (re.compile(r"^PROFILES_CLEAR$"), _to_sources_clear),
    (
        re.compile(r"^SPEAKER_INFO\s(\d+)\s(-?\d+(?:\.\d+)?)\s(-?\d+(?:\.\d+)?)\s(-?\d+(?:\.\d+)?)$"),
        _to_speaker_info,
    ),
    (re.compile(r"^SRATE\s(\d+)$"), _to_srate),
    (re.compile(r"^START_RUNNING$"), _to_start_running),
    (re.compile(r"^VOLUME\s(-?\d+(?:\.\d+)?)$"), _to_volume),
    (re.compile(r"^Welcome on Trinnov Optimizer \(Version (\S+), ID (\d+)\)$"), _to_welcome),
)


def parse_message(line: str) -> Message:
    """Parse one line from the Trinnov protocol stream."""
    for pattern, parser in PARSER_RULES:
        match = pattern.match(line)
        if match is not None:
            return parser(match)
    return UnknownMessage(line)
