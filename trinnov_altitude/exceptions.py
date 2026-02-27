"""Exceptions for the Trinnov Altitude client."""

from __future__ import annotations


class TrinnovAltitudeError(Exception):
    """Base exception for this library."""


class ConnectionFailedError(TrinnovAltitudeError):
    """Raised when connecting fails immediately."""

    def __init__(self, exception: Exception):
        super().__init__(f"Connection failed: {exception}")


class ConnectionTimeoutError(TrinnovAltitudeError):
    """Raised when connecting times out."""

    def __init__(self, message: str | None = None):
        super().__init__(
            message
            or "Connection to the Trinnov Altitude timed out. Is it powered on? Try calling `power_on` first."
        )


class CommandRejectedError(TrinnovAltitudeError):
    """Raised when the processor rejects a command."""

    def __init__(self, command: str, reason: str):
        super().__init__(f"Command rejected: {command} ({reason})")


class MalformedMacAddressError(TrinnovAltitudeError):
    """Raised when a MAC address has an invalid format."""

    def __init__(self, mac_address: str):
        super().__init__(f"Malformed MAC address provided: {mac_address}")


class NoMacAddressError(TrinnovAltitudeError):
    """Raised when Wake-on-LAN is requested without a MAC address."""

    def __init__(self):
        super().__init__("You must supply a MAC address to power on the Trinnov Altitude.")


class NotConnectedError(TrinnovAltitudeError):
    """Raised when a connected operation is attempted while disconnected."""

    def __init__(self, message: str = "Not connected to Trinnov Altitude."):
        super().__init__(message)
