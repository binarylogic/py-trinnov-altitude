from trinnov_altitude.protocol import (
    AudiosyncStatusMessage,
    ByeMessage,
    CurrentPresetMessage,
    CurrentSourceMessage,
    DecoderMessage,
    ErrorMessage,
    PresetMessage,
    SpeakerInfoMessage,
    StartRunningMessage,
    UnknownMessage,
    VolumeMessage,
    WelcomeMessage,
    parse_message,
)


def test_parse_welcome_message():
    message = parse_message("Welcome on Trinnov Optimizer (Version 4.3.2rc1, ID 10485761)")
    assert isinstance(message, WelcomeMessage)
    assert message.version == "4.3.2rc1"
    assert message.id == "10485761"


def test_parse_current_profile_message():
    message = parse_message("CURRENT_PROFILE 4")
    assert isinstance(message, CurrentSourceMessage)
    assert message.index == 4


def test_parse_meta_preset_loaded_message_maps_to_current_preset():
    message = parse_message("META_PRESET_LOADED 2")
    assert isinstance(message, CurrentPresetMessage)
    assert message.index == 2


def test_parse_preset_label_message():
    message = parse_message("LABEL 1: Cinema")
    assert isinstance(message, PresetMessage)
    assert message.index == 1
    assert message.name == "Cinema"


def test_parse_decoder_message_applies_audio_mapping():
    message = parse_message("DECODER NONAUDIO 0 PLAYABLE 1 DECODER ATMOS TrueHD UPMIXER dolby")
    assert isinstance(message, DecoderMessage)
    assert message.decoder == "Dolby Atmos/Dolby TrueHD"
    assert message.upmixer == "dolby"


def test_parse_volume_message():
    message = parse_message("VOLUME -18.5")
    assert isinstance(message, VolumeMessage)
    assert message.volume == -18.5


def test_parse_error_message():
    message = parse_message("ERROR: invalid command")
    assert isinstance(message, ErrorMessage)
    assert message.error == "invalid command"


def test_parse_audiosync_status_message():
    message = parse_message("AUDIOSYNC STATUS 1")
    assert isinstance(message, AudiosyncStatusMessage)
    assert message.synchronized is True


def test_parse_speaker_info_message():
    message = parse_message("SPEAKER_INFO 0 1.36485 102.091 -43.3817")
    assert isinstance(message, SpeakerInfoMessage)
    assert message.speaker_number == 0
    assert message.radius == 1.36485
    assert message.theta == 102.091
    assert message.phi == -43.3817


def test_parse_start_running_message():
    message = parse_message("START_RUNNING")
    assert isinstance(message, StartRunningMessage)


def test_parse_bye_message():
    message = parse_message("BYE")
    assert isinstance(message, ByeMessage)


def test_parse_unknown_message():
    message = parse_message("UNRECOGNIZED_EVENT foo bar")
    assert isinstance(message, UnknownMessage)
    assert message.raw_message == "UNRECOGNIZED_EVENT foo bar"


def test_parser_handles_diverse_unknowns_without_crashing():
    lines = ["", " ", "%%%", "\t", "CURRENT_PROFILE nope", "LABEL:"]
    for line in lines:
        message = parse_message(line)
        assert isinstance(message, UnknownMessage)
        assert message.raw_message == line
