"""Transport layer for Trinnov Altitude connections."""

from __future__ import annotations

import asyncio
import logging
import socket

from trinnov_altitude import exceptions

_LOGGER = logging.getLogger(__name__)


class TcpTransport:
    """Async TCP transport for line-based protocol communication."""

    ENCODING = "ascii"

    # OS-level keepalive defaults. These are a defense-in-depth backstop for a
    # truly dead path/peer; the client's application-level liveness probe is the
    # primary detector (it also catches a peer whose TCP stack still ACKs while
    # its control thread has wedged, which keepalive cannot see).
    DEFAULT_KEEPALIVE_IDLE = 15
    DEFAULT_KEEPALIVE_INTERVAL = 5
    DEFAULT_KEEPALIVE_COUNT = 3

    def __init__(
        self,
        host: str,
        port: int,
        *,
        tcp_keepalive: bool = True,
        keepalive_idle: int = DEFAULT_KEEPALIVE_IDLE,
        keepalive_interval: int = DEFAULT_KEEPALIVE_INTERVAL,
        keepalive_count: int = DEFAULT_KEEPALIVE_COUNT,
    ) -> None:
        self.host = host
        self.port = port
        self.tcp_keepalive = tcp_keepalive
        self.keepalive_idle = keepalive_idle
        self.keepalive_interval = keepalive_interval
        self.keepalive_count = keepalive_count
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    @property
    def connected(self) -> bool:
        return self._reader is not None and self._writer is not None

    async def connect(self, timeout: float | None) -> None:
        try:
            if timeout is None:
                self._reader, self._writer = await asyncio.open_connection(self.host, self.port)
            else:
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port), timeout=timeout
                )
        except asyncio.TimeoutError as err:
            raise exceptions.ConnectionTimeoutError() from err
        except (OSError, ValueError) as err:
            raise exceptions.ConnectionFailedError(err) from err

        if self.tcp_keepalive:
            self._enable_keepalive()

    def _enable_keepalive(self) -> None:
        """Enable TCP keepalive on the underlying socket (best-effort)."""
        if self._writer is None:
            return
        sock = self._writer.get_extra_info("socket")
        if sock is None:
            return
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            # Linux-style per-socket tuning.
            if hasattr(socket, "TCP_KEEPIDLE"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, self.keepalive_idle)
            if hasattr(socket, "TCP_KEEPINTVL"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, self.keepalive_interval)
            if hasattr(socket, "TCP_KEEPCNT"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, self.keepalive_count)
            # macOS spells the idle option TCP_KEEPALIVE.
            if not hasattr(socket, "TCP_KEEPIDLE") and hasattr(socket, "TCP_KEEPALIVE"):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPALIVE, self.keepalive_idle)
        except OSError as err:
            # Keepalive tuning is best-effort; the application-level heartbeat is
            # the primary liveness mechanism, so never fail a connection over this.
            _LOGGER.debug("Could not configure TCP keepalive: %s", err)

    async def close(self) -> None:
        writer = self._writer
        self._reader = None
        self._writer = None

        if writer is None:
            return

        writer.close()
        await writer.wait_closed()

    async def read_line(self, timeout: float | None) -> str:
        if self._reader is None:
            raise exceptions.NotConnectedError()

        if timeout is None:
            line = await self._reader.readline()
        else:
            line = await asyncio.wait_for(self._reader.readline(), timeout=timeout)

        if line == b"":
            raise exceptions.NotConnectedError("Connection closed by peer.")

        return line.decode(self.ENCODING).rstrip()

    async def send_line(self, line: str, timeout: float | None) -> None:
        if self._writer is None:
            raise exceptions.NotConnectedError()

        payload = line if line.endswith("\n") else f"{line}\n"
        self._writer.write(payload.encode(self.ENCODING))

        try:
            if timeout is None:
                await self._writer.drain()
            else:
                await asyncio.wait_for(self._writer.drain(), timeout=timeout)
        except OSError as err:
            raise exceptions.NotConnectedError() from err
