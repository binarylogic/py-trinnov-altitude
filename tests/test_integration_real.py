from __future__ import annotations

import asyncio

import pytest

from trinnov_altitude.client import TrinnovAltitudeClient


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


@pytest.mark.integration_real
@pytest.mark.asyncio
async def test_real_device_periodic_reconciliation_receives_state(
    real_client: TrinnovAltitudeClient,
) -> None:
    received = asyncio.Event()

    def handle_event(event: str, _message: object | None) -> None:
        if event == "received_message":
            received.set()

    real_client.register_callback(handle_event)
    try:
        await asyncio.wait_for(received.wait(), timeout=2.0)
    finally:
        real_client.deregister_callback(handle_event)

    assert real_client.connected
    assert real_client.state.synced
