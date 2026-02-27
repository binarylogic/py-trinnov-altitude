import asyncio
import contextlib
from collections import deque

import pytest

from trinnov_altitude.client import TrinnovAltitudeClient
from trinnov_altitude.exceptions import (
    CommandRejectedError,
    ConnectionFailedError,
    MalformedMacAddressError,
    NotConnectedError,
)


class FakeTransport:
    def __init__(self, incoming_lines=None, connect_exception=None):
        self.connected = False
        self.sent: list[str] = []
        self.connect_calls = 0
        self.close_calls = 0
        self._incoming = asyncio.Queue()
        self._connect_exception = connect_exception

        for line in incoming_lines or []:
            self._incoming.put_nowait(line)

    async def connect(self, timeout):
        self.connect_calls += 1
        if self._connect_exception is not None:
            raise self._connect_exception
        self.connected = True

    async def close(self):
        self.close_calls += 1
        self.connected = False

    async def read_line(self, timeout):
        if not self.connected:
            raise NotConnectedError()

        if timeout is None:
            item = await self._incoming.get()
        else:
            item = await asyncio.wait_for(self._incoming.get(), timeout=timeout)

        if item is None:
            self.connected = False
            raise NotConnectedError("Connection closed by peer.")

        return item

    async def send_line(self, line, timeout):
        if not self.connected:
            raise NotConnectedError()
        self.sent.append(line)

    def push(self, line):
        self._incoming.put_nowait(line)


class FakeTransportFactory:
    def __init__(self, transports):
        self._transports = deque(transports)

    def __call__(self):
        return self._transports.popleft()


def synced_lines(version="4.3.2", device_id="1", preset="Builtin", source="Apple TV"):
    return [
        f"Welcome on Trinnov Optimizer (Version {version}, ID {device_id})",
        "LABELS_CLEAR",
        f"LABEL 0: {preset}",
        "PROFILES_CLEAR",
        f"PROFILE 0: {source}",
        "CURRENT_PRESET 0",
        "CURRENT_PROFILE 0",
    ]


@pytest.mark.asyncio
async def test_validate_mac():
    with pytest.raises(MalformedMacAddressError):
        TrinnovAltitudeClient.validate_mac("malformed")

    assert TrinnovAltitudeClient.validate_mac("c8:7f:54:7a:eb:c2")


@pytest.mark.asyncio
async def test_start_and_stop_are_idempotent():
    transport = FakeTransport(incoming_lines=synced_lines())
    client = TrinnovAltitudeClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
    )

    await client.start()
    await client.start()
    await client.wait_synced(timeout=1)

    assert transport.connect_calls == 1

    await client.stop()
    await client.stop()

    assert transport.close_calls == 1


@pytest.mark.asyncio
async def test_sync_requires_catalog_clear_even_when_empty():
    transport = FakeTransport(
        incoming_lines=[
            "Welcome on Trinnov Optimizer (Version 4.3.2, ID 42)",
            "LABELS_CLEAR",
            "PROFILES_CLEAR",
            "CURRENT_PRESET 0",
            "CURRENT_PROFILE 0",
        ]
    )
    client = TrinnovAltitudeClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
    )

    await client.start()
    await client.wait_synced(timeout=1)

    assert client.state.synced is True
    assert client.state.preset is None
    assert client.state.source is None

    await client.stop()


@pytest.mark.asyncio
async def test_current_indices_backfill_names_when_catalog_arrives_later():
    transport = FakeTransport(
        incoming_lines=[
            "Welcome on Trinnov Optimizer (Version 4.3.2, ID 2)",
            "CURRENT_PRESET 3",
            "CURRENT_PROFILE 4",
            "LABELS_CLEAR",
            "PROFILES_CLEAR",
            "LABEL 3: Cinema",
            "PROFILE 4: Shield",
        ]
    )
    client = TrinnovAltitudeClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
    )

    await client.start()
    await client.wait_synced(timeout=1)

    assert client.state.preset == "Cinema"
    assert client.state.source == "Shield"

    await client.stop()


@pytest.mark.asyncio
async def test_callback_exception_is_isolated():
    transport = FakeTransport(incoming_lines=synced_lines())
    client = TrinnovAltitudeClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
    )

    def broken_callback(event, message):
        raise RuntimeError("boom")

    client.register_callback(broken_callback)

    await client.start()
    await client.wait_synced(timeout=1)

    assert client.connected
    assert client.state.synced

    await client.stop()


@pytest.mark.asyncio
async def test_reconnect_uses_backoff_until_success():
    sleep_calls = []

    async def fake_sleep(delay):
        sleep_calls.append(delay)

    first = FakeTransport(incoming_lines=synced_lines(device_id="1") + [None])
    failing = FakeTransport(connect_exception=ConnectionFailedError(OSError("network down")))
    second = FakeTransport(incoming_lines=synced_lines(version="4.3.3", device_id="2", preset="Movie", source="Blu-ray"))

    client = TrinnovAltitudeClient(
        host="unused",
        transport_factory=FakeTransportFactory([first, failing, second]),
        read_timeout=0.01,
        reconnect_initial_backoff=0.1,
        reconnect_max_backoff=0.4,
        reconnect_jitter=0.0,
        sleep_func=fake_sleep,
    )

    await client.start()
    await client.wait_synced(timeout=1)

    await asyncio.wait_for(_wait_for(lambda: client.state.id == "2"), timeout=1)

    assert sleep_calls == [0.1]
    assert client.state.version == "4.3.3"
    assert client.state.preset == "Movie"
    assert client.state.source == "Blu-ray"

    await client.stop()


@pytest.mark.asyncio
async def test_reconnect_stops_when_auto_reconnect_disabled():
    transport = FakeTransport(incoming_lines=synced_lines() + [None])
    client = TrinnovAltitudeClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
        auto_reconnect=False,
    )

    await client.start()
    await client.wait_synced(timeout=1)

    await asyncio.wait_for(_wait_for(lambda: not client.connected), timeout=1)

    assert client.connected is False

    await client.stop()


@pytest.mark.asyncio
async def test_command_wait_for_ack_returns_ok_message():
    transport = FakeTransport(incoming_lines=synced_lines())
    client = TrinnovAltitudeClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
    )

    await client.start()
    await client.wait_synced(timeout=1)

    async def push_ack():
        await asyncio.sleep(0)
        transport.push("OK")

    asyncio.create_task(push_ack())
    ack = await client.command("volume -20", wait_for_ack=True, ack_timeout=0.5)

    assert ack is not None
    assert transport.sent[-1] == "volume -20"

    await client.stop()


@pytest.mark.asyncio
async def test_command_wait_for_ack_raises_on_error_message():
    transport = FakeTransport(incoming_lines=synced_lines())
    client = TrinnovAltitudeClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
    )

    await client.start()
    await client.wait_synced(timeout=1)

    async def push_error():
        await asyncio.sleep(0)
        transport.push("ERROR: invalid command")

    asyncio.create_task(push_error())

    with pytest.raises(CommandRejectedError):
        await client.command("bad", wait_for_ack=True, ack_timeout=0.5)

    await client.stop()


@pytest.mark.asyncio
async def test_command_wait_for_ack_timeout_does_not_leak_waiters():
    transport = FakeTransport(incoming_lines=synced_lines())
    client = TrinnovAltitudeClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
    )

    await client.start()
    await client.wait_synced(timeout=1)

    with pytest.raises(asyncio.TimeoutError):
        await client.command("volume -10", wait_for_ack=True, ack_timeout=0.01)

    assert len(client._ack_waiters) == 0

    await client.stop()


@pytest.mark.asyncio
async def test_source_set_by_name_raises_for_unknown_source():
    transport = FakeTransport(incoming_lines=synced_lines())
    client = TrinnovAltitudeClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
    )

    await client.start()
    await client.wait_synced(timeout=1)

    with pytest.raises(ValueError, match="Unknown source name"):
        await client.source_set_by_name("Not A Source")

    await client.stop()


@pytest.mark.asyncio
async def test_volume_percentage_set_validates_bounds():
    transport = FakeTransport(incoming_lines=synced_lines())
    client = TrinnovAltitudeClient(
        host="unused",
        transport_factory=FakeTransportFactory([transport]),
        read_timeout=0.01,
    )

    await client.start()
    await client.wait_synced(timeout=1)

    with pytest.raises(ValueError, match="between 0 and 100"):
        await client.volume_percentage_set(101)

    await client.volume_percentage_set(50)
    assert any(line.startswith("volume ") for line in transport.sent)

    await client.stop()


async def _wait_for(predicate):
    if predicate():
        return

    event = asyncio.Event()
    while not predicate():
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(event.wait(), timeout=0.01)
