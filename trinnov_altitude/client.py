"""High-level Trinnov Altitude client optimized for long-running integrations."""

from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from collections import deque
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Protocol

from wakeonlan import send_magic_packet

from trinnov_altitude import const, exceptions
from trinnov_altitude.adapter import AdapterEvent, AltitudeSnapshot, AltitudeStateAdapter, StateDelta, snapshot_from_state
from trinnov_altitude.lifecycle import (
    AltitudeRuntimeState,
    ConnectionErrorInfo,
    ConnectionErrorKind,
    ControlHealth,
    PowerState,
    SyncState,
    TransportState,
    utc_now,
)
from trinnov_altitude.protocol import (
    ErrorMessage,
    Message,
    MetaPresetLoadedMessage,
    OKMessage,
    UnknownMessage,
    parse_message,
)
from trinnov_altitude.state import AltitudeState
from trinnov_altitude.transport import TcpTransport

Callback = Callable[[str, Message | None], None]
AdapterCallback = Callable[[AltitudeSnapshot, list[StateDelta], list[AdapterEvent]], None]
RandomFunc = Callable[[], float]


class Transport(Protocol):
    @property
    def connected(self) -> bool: ...

    async def connect(self, timeout: float | None) -> None: ...

    async def close(self) -> None: ...

    async def read_line(self, timeout: float | None) -> str: ...

    async def send_line(self, line: str, timeout: float | None) -> None: ...


class TrinnovAltitudeClient:
    DEFAULT_CLIENT_ID = "py-trinnov-altitude"
    DEFAULT_PORT = 44100
    DEFAULT_CONNECT_TIMEOUT = 2.0
    DEFAULT_COMMAND_TIMEOUT = 2.0
    DEFAULT_READ_TIMEOUT = 30.0
    DEFAULT_RECONNECT_INITIAL_BACKOFF = 1.0
    DEFAULT_RECONNECT_MAX_BACKOFF = 30.0
    DEFAULT_RECONNECT_JITTER = 0.2
    DEFAULT_SELECTOR_CONVERGENCE_TIMEOUT = 5.0
    DEFAULT_SELECTOR_CONVERGENCE_INTERVAL = 0.25

    VOLUME_MIN = -120.0
    VOLUME_MAX = 20.0

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        mac: str | None = None,
        client_id: str = DEFAULT_CLIENT_ID,
        connect_timeout: float | None = DEFAULT_CONNECT_TIMEOUT,
        command_timeout: float | None = DEFAULT_COMMAND_TIMEOUT,
        read_timeout: float | None = DEFAULT_READ_TIMEOUT,
        reconnect_initial_backoff: float = DEFAULT_RECONNECT_INITIAL_BACKOFF,
        reconnect_max_backoff: float = DEFAULT_RECONNECT_MAX_BACKOFF,
        reconnect_jitter: float = DEFAULT_RECONNECT_JITTER,
        auto_reconnect: bool = True,
        logger: logging.Logger | None = None,
        transport_factory: Callable[[], Transport] | None = None,
        sleep_func: Callable[[float], Awaitable[None]] | None = None,
        random_func: RandomFunc | None = None,
        selector_convergence_timeout: float = DEFAULT_SELECTOR_CONVERGENCE_TIMEOUT,
        selector_convergence_interval: float = DEFAULT_SELECTOR_CONVERGENCE_INTERVAL,
    ) -> None:
        if mac is not None:
            self.validate_mac(mac)

        self.host = host
        self.port = port
        self.mac = mac
        self.client_id = client_id
        self.connect_timeout = connect_timeout
        self.command_timeout = command_timeout
        self.read_timeout = read_timeout

        self.reconnect_initial_backoff = reconnect_initial_backoff
        self.reconnect_max_backoff = reconnect_max_backoff
        self.reconnect_jitter = reconnect_jitter
        self.auto_reconnect = auto_reconnect
        self.selector_convergence_timeout = selector_convergence_timeout
        self.selector_convergence_interval = selector_convergence_interval

        self.logger = logger if logger is not None else logging.getLogger(__name__)
        self.state = AltitudeState()
        self.runtime = AltitudeRuntimeState()

        self._callbacks: set[Callback] = set()
        self._listen_task: asyncio.Task[None] | None = None
        self._sync_event = asyncio.Event()
        self._stopping = False

        self._transport_factory = transport_factory or (lambda: TcpTransport(self.host, self.port))
        self._transport: Transport | None = None

        self._sleep = sleep_func or asyncio.sleep
        self._random = random_func or random.random

        self._command_lock = asyncio.Lock()
        self._ack_waiters: deque[asyncio.Future[Message]] = deque()
        self._unknown_message_count = 0
        self._unknown_message_samples: deque[str] = deque(maxlen=20)

    @property
    def connected(self) -> bool:
        return self._transport is not None and self._transport.connected

    @property
    def snapshot(self) -> AltitudeSnapshot:
        """Return the current protocol and runtime state as one immutable snapshot."""
        return snapshot_from_state(self.state, self.runtime)

    @classmethod
    def validate_mac(cls, mac_address: str) -> bool:
        pattern = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
        if pattern.match(mac_address.lower()) is None:
            raise exceptions.MalformedMacAddressError(mac_address)
        return True

    def register_callback(self, callback: Callback) -> None:
        self._callbacks.add(callback)

    def deregister_callback(self, callback: Callback) -> None:
        self._callbacks.discard(callback)

    def register_adapter_callback(self, adapter: AltitudeStateAdapter, callback: AdapterCallback) -> Callback:
        """Register a callback that receives adapter snapshots, deltas and events."""

        def wrapped(event: str, message: Message | None) -> None:
            if event == "received_message" and message is None:
                return
            if event not in {"received_message", "runtime_changed", "connected", "disconnected"}:
                return

            initial = adapter.last_snapshot is None
            snapshot, deltas, events = adapter.update(self.state, self.runtime)

            if initial:
                callback(snapshot, deltas, [AdapterEvent(kind="initial", payload={}), *events])
                return

            if not deltas and not events:
                return

            callback(snapshot, deltas, events)

        self.register_callback(wrapped)
        return wrapped

    def deregister_adapter_callback(self, callback: Callback) -> None:
        """Deregister a callback previously returned by ``register_adapter_callback``."""
        self.deregister_callback(callback)

    async def start(self) -> None:
        if self._listen_task is not None and not self._listen_task.done():
            return

        self._stopping = False
        await self._connect_and_bootstrap()
        self._listen_task = asyncio.create_task(self._listen_loop())

    async def stop(self) -> None:
        self._stopping = True

        if self._listen_task is not None:
            self._listen_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._listen_task
            self._listen_task = None

        await self._disconnect_statefully()

    async def wait_synced(self, timeout: float | None = 10.0) -> None:
        if timeout is None:
            await self._sync_event.wait()
            return
        await asyncio.wait_for(self._sync_event.wait(), timeout=timeout)

    async def command(
        self,
        line: str,
        wait_for_ack: bool = False,
        ack_timeout: float | None = None,
        send_timeout: float | None = None,
    ) -> Message | None:
        return await self._command(
            line,
            wait_for_ack=wait_for_ack,
            ack_timeout=ack_timeout,
            send_timeout=send_timeout,
        )

    async def _connect_and_bootstrap(self) -> None:
        if self.connected:
            return

        self._set_runtime(
            transport=TransportState.CONNECTING,
            sync=SyncState.SYNCING,
            control=ControlHealth.CONNECTING,
        )
        self._sync_event.clear()
        self.state.reset_runtime_values()

        self._transport = self._transport_factory()
        try:
            await self._transport.connect(timeout=self.connect_timeout)
        except Exception as err:
            self._transport = None
            self._set_runtime(
                transport=TransportState.DISCONNECTED,
                sync=SyncState.UNSYNCED,
                control=ControlHealth.UNAVAILABLE,
                last_error=_connection_error_info(err),
            )
            raise

        self.state.bypass = False
        self.state.dim = False
        self.state.mute = False

        self._set_runtime(
            transport=TransportState.CONNECTED,
            sync=SyncState.SYNCING,
            control=ControlHealth.CONNECTING,
            last_connected_at=utc_now(),
        )

        self._emit("connected", None)

        await self._command(f"id {self.client_id}")
        await self._command("get_current_state")
        await self._command("upmixer")

    async def _disconnect_statefully(self, error: Exception | None = None) -> None:
        transport = self._transport
        self._transport = None

        self._sync_event.clear()
        self.state.reset_runtime_values()
        changes: dict[str, object] = {
            "transport": TransportState.DISCONNECTED,
            "sync": SyncState.UNSYNCED,
            "control": ControlHealth.UNAVAILABLE,
            "last_disconnected_at": utc_now(),
        }
        if error is not None:
            changes["last_error"] = _connection_error_info(error)
        if self.runtime.power == PowerState.READY:
            changes["power"] = PowerState.UNKNOWN
        self._set_runtime(**changes)

        while self._ack_waiters:
            waiter = self._ack_waiters.popleft()
            if not waiter.done():
                waiter.set_exception(exceptions.NotConnectedError())

        if transport is None:
            return

        with suppress(OSError, exceptions.NotConnectedError):
            await transport.close()

        self._emit("disconnected", None)

    async def _listen_loop(self) -> None:
        try:
            while not self._stopping:
                try:
                    line = await self._read_line()
                    message = parse_message(line)
                    if isinstance(message, UnknownMessage):
                        self._record_unknown_message(message.raw_message)

                    self.state.apply(message)
                    if isinstance(message, MetaPresetLoadedMessage):
                        await self._refresh_authoritative_selectors()

                    if isinstance(message, ErrorMessage):
                        self.logger.error("Received error from Trinnov Altitude: %s", message.error)

                    self._resolve_ack_waiter(message)
                    self._set_runtime(last_message_at=utc_now())
                    self._emit("received_message", message)

                    self._mark_ready_when_synced()
                except asyncio.TimeoutError:
                    continue
                except (exceptions.NotConnectedError, OSError) as err:
                    await self._disconnect_statefully(err)
                    reconnected = await self._attempt_reconnect_until_success()
                    if not reconnected:
                        break
        except asyncio.CancelledError:
            pass

    def _record_unknown_message(self, line: str) -> None:
        self._unknown_message_count += 1
        self._unknown_message_samples.append(line)
        if self._unknown_message_count <= 5:
            self.logger.warning("Unknown protocol message: %s", line)
            return
        if self._unknown_message_count % 100 == 0:
            self.logger.warning(
                "Unknown protocol messages seen=%s latest=%s",
                self._unknown_message_count,
                line,
            )

    @property
    def unknown_message_count(self) -> int:
        return self._unknown_message_count

    @property
    def recent_unknown_messages(self) -> tuple[str, ...]:
        return tuple(self._unknown_message_samples)

    def _resolve_ack_waiter(self, message: Message) -> None:
        if not isinstance(message, (OKMessage, ErrorMessage)):
            return
        if not self._ack_waiters:
            return

        waiter = self._ack_waiters.popleft()
        if not waiter.done():
            waiter.set_result(message)

    async def _attempt_reconnect_until_success(self) -> bool:
        if self._stopping or not self.auto_reconnect:
            return False

        delay = max(0.0, self.reconnect_initial_backoff)

        while not self._stopping and self.auto_reconnect:
            try:
                await self._connect_and_bootstrap()
                return True
            except (exceptions.ConnectionFailedError, exceptions.ConnectionTimeoutError):
                capped_delay = min(delay, self.reconnect_max_backoff)
                jitter_amount = capped_delay * self.reconnect_jitter * self._random()
                self._emit("reconnect_scheduled", None)
                await self._sleep(capped_delay + jitter_amount)
                delay = min(max(capped_delay * 2, self.reconnect_initial_backoff), self.reconnect_max_backoff)

        return False

    async def _read_line(self) -> str:
        if self._transport is None:
            raise exceptions.NotConnectedError()
        return await self._transport.read_line(timeout=self.read_timeout)

    async def _command(
        self,
        line: str,
        wait_for_ack: bool = False,
        ack_timeout: float | None = None,
        send_timeout: float | None = None,
    ) -> Message | None:
        if self._transport is None:
            raise exceptions.NotConnectedError()

        waiter: asyncio.Future[Message] | None = None

        async with self._command_lock:
            if wait_for_ack:
                loop = asyncio.get_running_loop()
                waiter = loop.create_future()
                self._ack_waiters.append(waiter)

            try:
                actual_timeout = self.command_timeout if send_timeout is None else send_timeout
                await self._transport.send_line(line, timeout=actual_timeout)
            except Exception:
                if waiter is not None and waiter in self._ack_waiters:
                    self._ack_waiters.remove(waiter)
                raise

        if waiter is None:
            return None

        timeout = self.command_timeout if ack_timeout is None else ack_timeout
        try:
            ack_message = await asyncio.wait_for(waiter, timeout=timeout)
        except asyncio.TimeoutError:
            if waiter in self._ack_waiters:
                self._ack_waiters.remove(waiter)
            raise

        if isinstance(ack_message, ErrorMessage):
            raise exceptions.CommandRejectedError(line, ack_message.error)

        return ack_message

    def _emit(self, event: str, message: Message | None) -> None:
        for callback in tuple(self._callbacks):
            try:
                callback(event, message)
            except Exception:
                self.logger.exception("Callback raised an exception during '%s'", event)

    def _set_runtime(self, **changes: object) -> None:
        previous = self.runtime
        current = previous.with_changes(**changes)
        if current == previous:
            return
        self.runtime = current
        self._emit("runtime_changed", None)

    def _mark_ready_when_synced(self) -> None:
        if not self.state.synced:
            return
        changes: dict[str, object] = {
            "sync": SyncState.SYNCED,
            "control": ControlHealth.AVAILABLE,
        }
        if self.runtime.power is not PowerState.READY:
            changes["power"] = PowerState.READY
        self._set_runtime(**changes)
        self._sync_event.set()

    async def _refresh_authoritative_selectors(self) -> None:
        await self.preset_get()
        await self.source_get()

    @property
    def volume(self) -> float | None:
        return self.state.volume

    @property
    def volume_percentage(self) -> float | None:
        if self.state.volume is None:
            return None
        return ((self.state.volume - self.VOLUME_MIN) / (self.VOLUME_MAX - self.VOLUME_MIN)) * 100

    def power_on_available(self) -> bool:
        return self.mac is not None

    def power_on(self) -> None:
        if self.mac is None:
            raise exceptions.NoMacAddressError()
        if self.connected and self.state.synced:
            self._set_runtime(power=PowerState.READY)
            return
        self._set_runtime(power=PowerState.WAKING)
        send_magic_packet(self.mac)

    async def power_off(self) -> None:
        await self._command("power_off_SECURED_FHZMCH48FE")
        self._set_runtime(power=PowerState.OFF)

    async def preset_get(self) -> None:
        await self._command("get_current_preset")

    async def preset_label_get(self, preset_id: int) -> None:
        await self._command(f"get_label {preset_id}")

    async def presets_get_all(self) -> None:
        await self._command("get_all_label")

    async def preset_set(self, preset_id: int) -> None:
        await self._command_until(
            command=lambda: self._command(f"loadp {preset_id}"),
            refresh=self.preset_get,
            predicate=lambda: self.state.current_preset_index == preset_id,
            description=f"preset {preset_id} to become active",
        )

    async def source_get(self) -> None:
        await self._command("get_current_profile")

    async def source_name_get(self, source_id: int) -> None:
        await self._command(f"get_profile_name {source_id}")

    async def source_set(self, source_id: int) -> None:
        await self._command_until(
            command=lambda: self._command(f"profile {source_id}"),
            refresh=self.source_get,
            predicate=lambda: self.state.current_source_index == source_id,
            description=f"source {source_id} to become active",
        )

    async def source_set_by_name(self, name: str) -> None:
        for source_id, source_name in self.state.sources.items():
            if source_name == name:
                await self.source_set(source_id)
                return
        raise ValueError(f"Unknown source name: {name}")

    async def _command_until(
        self,
        command: Callable[[], Awaitable[Message | None]],
        refresh: Callable[[], Awaitable[None]],
        predicate: Callable[[], bool],
        description: str,
    ) -> None:
        if predicate():
            return
        deadline = time.monotonic() + self.selector_convergence_timeout
        while True:
            await command()
            await refresh()
            await self._sleep(0)
            if predicate():
                return
            if time.monotonic() >= deadline:
                raise exceptions.CommandConvergenceTimeoutError(description, self.selector_convergence_timeout)
            await self._sleep(self.selector_convergence_interval)

    async def remapping_mode_set(self, mode: const.RemappingMode) -> None:
        await self._command(f"remapping_mode {mode.value}")

    async def upmixer_get(self) -> None:
        await self._command("upmixer")

    async def upmixer_set(self, mode: const.UpmixerMode) -> None:
        await self._command(f"upmixer {mode.value}")
        await self.upmixer_get()

    async def state_get_current(self) -> None:
        await self._command("get_current_state")

    async def volume_set(self, db: float) -> None:
        target = round(db, 1)
        await self._command_until(
            command=lambda: self._command(f"volume {target}"),
            refresh=self.state_get_current,
            predicate=lambda: self.state.volume is not None and abs(self.state.volume - target) <= 0.05,
            description=f"volume {target:.1f} dB to be active",
        )

    async def volume_adjust(self, delta: float) -> None:
        await self._command(f"dvolume {delta}")

    async def volume_up(self) -> None:
        await self.volume_adjust(0.5)

    async def volume_down(self) -> None:
        await self.volume_adjust(-0.5)

    async def volume_ramp(self, db: float, duration: int) -> None:
        await self._command(f"volume_ramp {db} {duration}")

    async def volume_percentage_set(self, percentage: float) -> None:
        if not (0 <= percentage <= 100):
            raise ValueError("Percentage must be between 0 and 100")
        volume = ((percentage / 100) * (self.VOLUME_MAX - self.VOLUME_MIN)) + self.VOLUME_MIN
        await self.volume_set(round(volume, 1))

    async def change_page(self, delta: int) -> None:
        await self._command(f"change_page {delta}")

    async def page_down(self) -> None:
        await self.change_page(-1)

    async def page_up(self) -> None:
        await self.change_page(1)

    async def bypass_set(self, state: bool) -> None:
        await self._command(f"bypass {int(state)}")

    async def bypass_on(self) -> None:
        await self.bypass_set(True)

    async def bypass_off(self) -> None:
        await self.bypass_set(False)

    async def bypass_toggle(self) -> None:
        await self._command("bypass 2")

    async def mute_set(self, state: bool) -> None:
        await self._command(f"mute {int(state)}")

    async def mute_on(self) -> None:
        await self.mute_set(True)

    async def mute_off(self) -> None:
        await self.mute_set(False)

    async def mute_toggle(self) -> None:
        await self._command("mute 2")

    async def dim_set(self, state: bool) -> None:
        await self._command(f"dim {int(state)}")

    async def dim_on(self) -> None:
        await self.dim_set(True)

    async def dim_off(self) -> None:
        await self.dim_set(False)

    async def dim_toggle(self) -> None:
        await self._command("dim 2")

    async def front_display_set(self, state: bool) -> None:
        await self._command(f"fav_light {int(state)}")

    async def front_display_on(self) -> None:
        await self.front_display_set(True)

    async def front_display_off(self) -> None:
        await self.front_display_set(False)

    async def front_display_toggle(self) -> None:
        await self._command("fav_light 2")

    async def optimization_set(self, state: bool) -> None:
        await self._command(f"quick_optimized {int(state)}")

    async def optimization_on(self) -> None:
        await self.optimization_set(True)

    async def optimization_off(self) -> None:
        await self.optimization_set(False)

    async def optimization_toggle(self) -> None:
        await self._command("quick_optimized 2")

    async def acoustic_correction_set(self, state: bool) -> None:
        await self._command(f"use_acoustic_correct {int(state)}")

    async def acoustic_correction_on(self) -> None:
        await self.acoustic_correction_set(True)

    async def acoustic_correction_off(self) -> None:
        await self.acoustic_correction_set(False)

    async def acoustic_correction_toggle(self) -> None:
        await self._command("use_acoustic_correct 2")

    async def level_alignment_set(self, state: bool) -> None:
        await self._command(f"use_level_alignment {int(state)}")

    async def level_alignment_on(self) -> None:
        await self.level_alignment_set(True)

    async def level_alignment_off(self) -> None:
        await self.level_alignment_set(False)

    async def level_alignment_toggle(self) -> None:
        await self._command("use_level_alignment 2")

    async def time_alignment_set(self, state: bool) -> None:
        await self._command(f"use_time_alignment {int(state)}")

    async def time_alignment_on(self) -> None:
        await self.time_alignment_set(True)

    async def time_alignment_off(self) -> None:
        await self.time_alignment_set(False)

    async def time_alignment_toggle(self) -> None:
        await self._command("use_time_alignment 2")

    async def bye(self) -> None:
        await self._command("bye")


def _connection_error_info(error: Exception) -> ConnectionErrorInfo:
    if isinstance(error, exceptions.ConnectionFailedError):
        kind = ConnectionErrorKind.CONNECTION_FAILED
    elif isinstance(error, exceptions.ConnectionTimeoutError):
        kind = ConnectionErrorKind.CONNECTION_TIMEOUT
    elif isinstance(error, exceptions.NotConnectedError):
        kind = ConnectionErrorKind.NOT_CONNECTED
    elif isinstance(error, OSError):
        kind = ConnectionErrorKind.OS_ERROR
    else:
        kind = ConnectionErrorKind.UNKNOWN
    return ConnectionErrorInfo(kind=kind, message=str(error), at=utc_now())
