from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio

from trinnov_altitude.client import TrinnovAltitudeClient


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _get_required_real_target() -> tuple[str, int]:
    if not _env_flag("TRINNOV_ITEST"):
        pytest.skip("real integration tests are disabled (set TRINNOV_ITEST=1)")

    host = os.getenv("TRINNOV_HOST")
    if not host:
        pytest.skip("TRINNOV_HOST is not set")

    port = int(os.getenv("TRINNOV_PORT", str(TrinnovAltitudeClient.DEFAULT_PORT)))
    return host, port


async def _is_reachable(host: str, port: int, timeout: float) -> bool:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host=host, port=port), timeout=timeout)
    except (TimeoutError, OSError):
        return False

    writer.close()
    await writer.wait_closed()
    return True


@pytest_asyncio.fixture
async def real_client() -> AsyncGenerator[TrinnovAltitudeClient, None]:
    host, port = _get_required_real_target()

    if not await _is_reachable(host, port, timeout=1.0):
        pytest.skip(f"Trinnov target {host}:{port} is unreachable")

    client = TrinnovAltitudeClient(
        host=host,
        port=port,
        auto_reconnect=False,
        connect_timeout=2.0,
        command_timeout=2.0,
        read_timeout=2.0,
    )

    await client.start()
    try:
        await client.wait_synced(timeout=10.0)
        yield client
    finally:
        await client.stop()
