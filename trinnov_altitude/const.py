"""Constants and enums for Trinnov Altitude commands."""

from __future__ import annotations

from enum import Enum


class RemappingMode(str, Enum):
    MODE_NONE = "none"
    MODE_2D = "2D"
    MODE_3D = "3D"
    MODE_AUTOROUTE = "autoroute"
    MODE_MANUAL = "manual"


class UpmixerMode(str, Enum):
    MODE_AUTO = "auto"
    MODE_AURO3D = "auro3d"
    MODE_DTS = "dts"
    MODE_DOLBY = "dolby"
    MODE_NATIVE = "native"
    MODE_LEGACY = "legacy"
    MODE_UPMIX_ON_NATIVE = "upmix on native"
