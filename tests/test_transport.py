from __future__ import annotations

import asyncio
import contextlib
import socket

import pytest

from trinnov_altitude.transport import TcpTransport


@contextlib.asynccontextmanager
async def _echoless_server():
    """A loopback server whose handler drains until EOF then closes its side.

    Reading until EOF means the server-side connection closes once the client
    disconnects, so ``server.wait_closed()`` does not block on a live socket.
    """
    conns: list[asyncio.StreamWriter] = []

    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        conns.append(writer)
        try:
            await reader.read()
        finally:
            writer.close()

    server = await asyncio.start_server(handler, host="127.0.0.1", port=0)
    port = server.sockets[0].getsockname()[1]
    try:
        yield port
    finally:
        for writer in conns:
            writer.close()
        server.close()
        await server.wait_closed()


@pytest.mark.asyncio
async def test_connect_enables_tcp_keepalive():
    async with _echoless_server() as port:
        transport = TcpTransport("127.0.0.1", port)
        try:
            await transport.connect(timeout=2.0)
            assert transport.connected

            sock = transport._writer.get_extra_info("socket")
            assert sock is not None
            # Enabled reads back nonzero (the exact value is platform-specific; macOS returns 8).
            assert sock.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE) != 0
        finally:
            await transport.close()


@pytest.mark.asyncio
async def test_connect_can_disable_tcp_keepalive():
    async with _echoless_server() as port:
        transport = TcpTransport("127.0.0.1", port, tcp_keepalive=False)
        try:
            await transport.connect(timeout=2.0)
            sock = transport._writer.get_extra_info("socket")
            assert sock is not None
            assert sock.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE) == 0
        finally:
            await transport.close()
