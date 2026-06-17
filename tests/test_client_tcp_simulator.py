from __future__ import annotations

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
