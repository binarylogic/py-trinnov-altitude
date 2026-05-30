"""Typed runtime lifecycle model for Trinnov Altitude clients."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum


class TransportState(str, Enum):
    """TCP transport lifecycle."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"


class SyncState(str, Enum):
    """Protocol bootstrap/sync lifecycle."""

    UNSYNCED = "unsynced"
    SYNCING = "syncing"
    SYNCED = "synced"


class ControlHealth(str, Enum):
    """Whether the processor control plane is usable."""

    UNAVAILABLE = "unavailable"
    CONNECTING = "connecting"
    AVAILABLE = "available"


class PowerState(str, Enum):
    """Best-known power lifecycle without conflating it with transport state."""

    UNKNOWN = "unknown"
    OFF = "off"
    WAKING = "waking"
    READY = "ready"


class ConnectionErrorKind(str, Enum):
    """Stable reason categories for connection and command failures."""

    CONNECTION_FAILED = "connection_failed"
    CONNECTION_TIMEOUT = "connection_timeout"
    NOT_CONNECTED = "not_connected"
    OS_ERROR = "os_error"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ConnectionErrorInfo:
    """Last connection/control failure observed by the client."""

    kind: ConnectionErrorKind
    message: str
    at: datetime


@dataclass(frozen=True)
class AltitudeRuntimeState:
    """Runtime metadata that is not part of the Trinnov protocol state."""

    transport: TransportState = TransportState.DISCONNECTED
    sync: SyncState = SyncState.UNSYNCED
    control: ControlHealth = ControlHealth.UNAVAILABLE
    power: PowerState = PowerState.UNKNOWN
    last_error: ConnectionErrorInfo | None = None
    last_connected_at: datetime | None = None
    last_disconnected_at: datetime | None = None
    last_message_at: datetime | None = None

    def with_changes(self, **changes: object) -> AltitudeRuntimeState:
        """Return a copy with selected fields replaced."""
        return replace(self, **changes)


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""
    return datetime.now(timezone.utc)
