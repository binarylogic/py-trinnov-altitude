from trinnov_altitude.command_bridge import (
    ACK_REQUIRED_COMMANDS,
    VALID_COMMANDS,
    cast_primitive,
    normalize_args,
    parse_command,
    parse_remapping_mode,
    parse_upmixer_mode,
)
from trinnov_altitude.const import RemappingMode, UpmixerMode


def test_parse_command_handles_quoted_args():
    parsed = parse_command('source_set_by_name "Apple TV 4K"')
    assert parsed.method_name == "source_set_by_name"
    assert parsed.args == ("Apple TV 4K",)


def test_parse_command_rejects_empty():
    try:
        parse_command("   ")
    except ValueError as exc:
        assert "empty" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError")


def test_cast_primitive():
    assert cast_primitive("true") is True
    assert cast_primitive("false") is False
    assert cast_primitive("2") == 2
    assert cast_primitive("-35.5") == -35.5
    assert cast_primitive("dolby") == "dolby"


def test_parse_upmixer_mode_case_insensitive():
    assert parse_upmixer_mode("DOLBY") is UpmixerMode.MODE_DOLBY


def test_parse_remapping_mode_case_insensitive():
    assert parse_remapping_mode("3d") is RemappingMode.MODE_3D


def test_normalize_args_for_special_commands():
    assert normalize_args("source_set_by_name", ["Apple", "TV"]) == ["Apple TV"]
    assert normalize_args("upmixer_set", ["native"]) == [UpmixerMode.MODE_NATIVE]
    assert normalize_args("remapping_mode_set", ["manual"]) == [RemappingMode.MODE_MANUAL]


def test_command_sets_include_expected_items():
    assert "source_set_by_name" in VALID_COMMANDS
    assert "upmixer_set" in VALID_COMMANDS
    assert "source_set_by_name" in ACK_REQUIRED_COMMANDS
