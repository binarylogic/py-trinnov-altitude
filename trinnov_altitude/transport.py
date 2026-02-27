"""Transport layer for Trinnov Altitude connections."""

from __future__ import annotations

import asyncio

from trinnov_altitude import exceptions


class TcpTransport:
    """Async TCP transport for line-based protocol communication."""

    ENCODING = "ascii"

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
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
