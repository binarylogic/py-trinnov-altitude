"""Helpers for Home Assistant-style command parsing and normalization."""

from __future__ import annotations

import shlex
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from trinnov_altitude.const import RemappingMode, UpmixerMode

VALID_COMMANDS: frozenset[str] = frozenset(
    {
        "acoustic_correction_off",
        "acoustic_correction_on",
        "acoustic_correction_toggle",
        "bypass_off",
        "bypass_on",
        "bypass_toggle",
        "dim_off",
        "dim_on",
        "dim_toggle",
        "front_display_off",
        "front_display_on",
        "front_display_toggle",
        "level_alignment_off",
        "level_alignment_on",
        "level_alignment_toggle",
        "mute_off",
        "mute_on",
        "mute_toggle",
        "page_down",
        "page_up",
        "preset_set",
        "optimization_off",
        "optimization_on",
        "optimization_toggle",
        "remapping_mode_set",
        "source_set",
        "source_set_by_name",
        "time_alignment_off",
        "time_alignment_on",
        "time_alignment_toggle",
        "upmixer_set",
        "volume_adjust",
        "volume_down",
        "volume_percentage_set",
        "volume_ramp",
        "volume_set",
        "volume_up",
    }
)

ACK_REQUIRED_COMMANDS: frozenset[str] = frozenset(
    {"power_off", "preset_set", "source_set", "source_set_by_name", "upmixer_set"}
)


@dataclass(frozen=True)
class ParsedCommand:
    """A parsed Home Assistant command."""

    method_name: str
    args: tuple[str, ...]


def parse_command(line: str) -> ParsedCommand:
    """Parse one command line using shell-like tokenization."""
    parts = shlex.split(line)
    if not parts:
        raise ValueError("Command cannot be empty")
    return ParsedCommand(method_name=parts[0], args=tuple(parts[1:]))


def cast_primitive(arg: str) -> bool | int | float | str:
    """Cast a string to bool/int/float when possible."""
    arg_lower = arg.lower()
    if arg_lower == "true":
        return True
    if arg_lower == "false":
        return False
    try:
        return int(arg)
    except ValueError:
        pass
    try:
        return float(arg)
    except ValueError:
        pass
    return arg


def parse_upmixer_mode(value: str) -> UpmixerMode:
    """Convert user input to an UpmixerMode."""
    value_lower = value.lower()
    for mode in UpmixerMode:
        if mode.value == value_lower:
            return mode
    valid_modes = ", ".join(mode.value for mode in UpmixerMode)
    raise ValueError(f"Invalid upmixer mode '{value}'. Valid modes are: {valid_modes}")


def parse_remapping_mode(value: str) -> RemappingMode:
    """Convert user input to a RemappingMode."""
    value_lower = value.lower()
    for mode in RemappingMode:
        if mode.value.lower() == value_lower:
            return mode
    valid_modes = ", ".join(mode.value for mode in RemappingMode)
    raise ValueError(
        f"Invalid remapping mode '{value}'. Valid modes are: {valid_modes}"
    )


def normalize_args(method_name: str, raw_args: Iterable[str]) -> list[Any]:
    """Convert command arguments to types expected by client methods."""
    args = list(raw_args)
    if method_name == "source_set_by_name" and args:
        return [" ".join(args)]
    if method_name == "upmixer_set" and args:
        return [parse_upmixer_mode(args[0])]
    if method_name == "remapping_mode_set" and args:
        return [parse_remapping_mode(args[0])]
    return [cast_primitive(arg) for arg in args]
