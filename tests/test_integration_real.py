from __future__ import annotations

import pytest

from trinnov_altitude.client import TrinnovAltitudeClient
from trinnov_altitude.protocol import OKMessage


@pytest.mark.integration_real
@pytest.mark.asyncio
async def test_real_device_startup_sync_is_readable(real_client: TrinnovAltitudeClient) -> None:
    assert real_client.connected is True
    assert real_client.state.synced is True
    assert real_client.state.version is not None
    assert real_client.state.id is not None


@pytest.mark.integration_real
@pytest.mark.asyncio
async def test_real_device_read_only_queries(real_client: TrinnovAltitudeClient) -> None:
    # Read-only commands only. No preset/source/volume/power mutating commands are allowed here.
    await real_client.preset_get()
    await real_client.source_get()
    ack = await real_client.command("send volume", wait_for_ack=True, ack_timeout=2.0)

    assert isinstance(ack, OKMessage)
