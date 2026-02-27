"""Public package exports for Trinnov Altitude."""

from trinnov_altitude import adapter, ha_bridge
from trinnov_altitude.client import TrinnovAltitudeClient

__all__ = ["TrinnovAltitudeClient", "adapter", "ha_bridge"]
__version__ = "3.0.0"
