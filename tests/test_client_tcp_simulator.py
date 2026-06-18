from __future__ import annotations

import asyncio
import contextlib

import pytest

from trinnov_altitude.client import TrinnovAltitudeClient
from trinnov_altitude.mocks import MockTrinnovAltitudeServer


@pytest.mark.asyncio
async def test_preset_set_over_tcp_retries_readback_without_repeating_load_command() -> None:
    server = MockTrinnovAltitudeServer(
        host="127.0.0.1",
        port=0,
        presets={0: "Builtin", 1: "MLP"},
        current_preset_index=0,
        preset_readback_lag=2,
    )
    await server.start_server()

    client = TrinnovAltitudeClient(
        host=server.host,
        port=server.port,
        auto_reconnect=False,
        connect_timeout=1.0,
        command_timeout=1.0,
        read_timeout=0.1,
        selector_convergence_timeout=1.0,
        selector_convergence_interval=0.0,
    )

    try:
        await client.start()
        await client.wait_synced(timeout=1.0)

        await client.preset_set(1)

        assert server.received_messages.count("loadp 1") == 1
        assert server.received_messages.count("get_current_preset") >= 3
        assert client.state.preset == "MLP"
    finally:
        await client.stop()
        await server.stop_server()


@pytest.mark.asyncio
async def test_volume_set_over_tcp_sends_absolute_db_once_and_requests_readback() -> None:
    server = MockTrinnovAltitudeServer(host="127.0.0.1", port=0)
    server.volume = -22.0
    await server.start_server()

    client = TrinnovAltitudeClient(
        host=server.host,
        port=server.port,
        auto_reconnect=False,
        connect_timeout=1.0,
        command_timeout=1.0,
        read_timeout=0.1,
    )

    try:
        await client.start()
        await client.wait_synced(timeout=1.0)

        await client.volume_set(-17.5)
        await asyncio.wait_for(_wait_for(lambda: client.state.volume == -17.5), timeout=1.0)

        assert server.received_messages.count("volume -17.5") == 1
        assert server.received_messages.count("send volume") == 1
        assert client.state.volume == -17.5
    finally:
        await client.stop()
        await server.stop_server()


async def _wait_for(predicate):
    if predicate():
        return

    event = asyncio.Event()
    while not predicate():
        with contextlib.suppress(asyncio.TimeoutError, TimeoutError):
            await asyncio.wait_for(event.wait(), timeout=0.01)
