"""Public package exports for Trinnov Altitude."""

from trinnov_altitude import adapter, command_bridge, ha_bridge, lifecycle
from trinnov_altitude.client import TrinnovAltitudeClient

__all__ = ["TrinnovAltitudeClient", "adapter", "command_bridge", "ha_bridge", "lifecycle"]
__version__ = "3.2.5"
