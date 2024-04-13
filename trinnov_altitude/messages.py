from __future__ import annotations

import re


def message_factory(message) -> Message:  # noqa: C901
    if match := re.match(r"^AUDIOSYNC\s(.*)", message):
        mode = match.group(1)
        return AudiosyncMessage(mode)
    elif match := re.match(r"^BYPASS\s(0|1)", message):
        state = bool(int(match.group(1)))
        return BypassMessage(state)
    elif match := re.match(r"^CURRENT_PRESET\s(-?\d+)", message):
        # A -1 will be sent, which means the built-in preset is being used
        state = max(0, int(match.group(1)))
        return CurrentPresetMessage(state)
    elif match := re.match(r"^CURRENT_PROFILE\s(-?\d+)", message):
        state = int(match.group(1))
        return CurrentSourceMessage(state)
    elif match := re.match(r"^CURRENT_SOURCE_FORMAT_NAME\s(.*)", message):
        format = match.group(1)
        return CurrentSourceFormat(format)
    elif match := re.match(
        r"^DECODER NONAUDIO (\d+) PLAYABLE (\d+) DECODER (\w+) UPMIXER (\w+)", message
    ):
        nonaudio = bool(int(match.group(1)))
        playable = bool(int(match.group(2)))
        decoder = match.group(3)
        upmixer = match.group(4)
        return DecoderMessage(nonaudio, playable, decoder, upmixer)
    elif match := re.match(r"^DIM\s(-?\d+)", message):
        state = bool(int(match.group(1)))
        return DimMessage(state)
    elif match := re.match(r"^ERROR: (.*)", message):
        error = match.group(1)
        return ErrorMessage(error)
    elif match := re.match(r"^LABEL\s(-?\d+): (.*)", message):
        index = int(match.group(1))
        name = match.group(2)
        return PresetMessage(index, name)
    elif match := re.match(r"^LABELS_CLEAR", message):
        return PresetsClearMessage()
    elif match := re.match(r"^MUTE\s(0|1)", message):
        state = bool(int(match.group(1)))
        return MuteMessage(state)
    elif match := re.match(r"^OK", message):
        return OKMessage()
    elif match := re.match(r"^PROFILE\s(-?\d+): (.*)", message):
        index = int(match.group(1))
        name = match.group(2)
        return SourceMessage(index, name)
    elif match := re.match(r"^PROFILES_CLEAR", message):
        return SourcesClearMessage()
    elif match := re.match(r"^SRATE (.*)", message):
        rate = int(match.group(1))
        return SamplingRateMessage(rate)
    elif match := re.match(r"^VOLUME\s(-?\d+(\.\d+)?)", message):
        volume = float(match.group(1))
        return VolumeMessage(volume)
    elif match := re.match(
        r"^Welcome on Trinnov Optimizer \(Version (\S+), ID (\d+)\)",
        message,
    ):
        version = match.group(1)
        id = match.group(2)
        return WelcomeMessage(version, id)
    else:
        return UnknownMessage(message)


class Message:
    pass


class AudiosyncMessage(Message):
    def __init__(self, mode: str) -> None:
        self.mode = mode


class BypassMessage(Message):
    def __init__(self, state: bool) -> None:
        self.state = state


class CurrentPresetMessage(Message):
    def __init__(self, index: int) -> None:
        self.index = index


class CurrentSourceFormat(Message):
    def __init__(self, format: str) -> None:
        self.format = format


class CurrentSourceMessage(Message):
    def __init__(self, index: int) -> None:
        self.index = index


class DecoderMessage(Message):
    def __init__(
        self, nonaudio: bool, playable: bool, decoder: str, upmixer: str
    ) -> None:
        self.nonaudio = nonaudio
        self.playable = playable
        self.decoder = decoder
        self.upmixer = upmixer


class DimMessage(Message):
    def __init__(self, state: bool) -> None:
        self.state = state


class ErrorMessage(Message):
    def __init__(self, error: str) -> None:
        self.error = error


class MuteMessage(Message):
    def __init__(self, state: bool) -> None:
        self.state = state


class OKMessage(Message):
    pass


class PresetMessage(Message):
    def __init__(self, index: int, name: str) -> None:
        self.index = index
        self.name = name


class PresetsClearMessage(Message):
    pass


class SamplingRateMessage(Message):
    def __init__(self, rate: int) -> None:
        self.rate = rate


class SourceMessage(Message):
    def __init__(self, index: int, name: str) -> None:
        self.index = index
        self.name = name


class SourcesClearMessage(Message):
    pass


class UnknownMessage(Message):
    def __init__(self, raw_message: str) -> None:
        self.raw_message = raw_message


class VolumeMessage(Message):
    def __init__(self, volume: float) -> None:
        self.volume = volume


class WelcomeMessage(Message):
    def __init__(self, version: str, id: str) -> None:
        self.version = version
        self.id = id
