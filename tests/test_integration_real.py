from __future__ import annotations

import asyncio

import pytest

from trinnov_altitude.adapter import AltitudeStateAdapter
from trinnov_altitude.client import TrinnovAltitudeClient
from trinnov_altitude.protocol import PresetsClearMessage, SourcesClearMessage


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


@pytest.mark.integration_real
@pytest.mark.asyncio
async def test_real_device_catalog_refreshes_are_atomic(real_client: TrinnovAltitudeClient) -> None:
    baseline = (
        real_client.snapshot.preset,
        real_client.snapshot.presets,
        real_client.snapshot.source,
        real_client.snapshot.sources,
    )
    observed = []
    clear_counts = {PresetsClearMessage: 0, SourcesClearMessage: 0}
    adapter = AltitudeStateAdapter()

    def handle_update(snapshot, _deltas, _events) -> None:
        observed.append((snapshot.preset, snapshot.presets, snapshot.source, snapshot.sources))

    def handle_message(event: str, message: object | None) -> None:
        if event == "received_message" and type(message) in clear_counts:
            clear_counts[type(message)] += 1

    callback = real_client.register_adapter_callback(adapter, handle_update)
    real_client.register_callback(handle_message)
    try:
        for _ in range(3):
            await real_client.state_get_current()
            await asyncio.sleep(0.35)
    finally:
        real_client.deregister_adapter_callback(callback)
        real_client.deregister_callback(handle_message)

    assert observed
    assert clear_counts[PresetsClearMessage] >= 3
    assert clear_counts[SourcesClearMessage] >= 3
    assert set(observed) == {baseline}
