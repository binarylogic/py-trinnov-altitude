"""
Implements the Trinnov Altitude processor automation protocol over TCP/IP
"""

import asyncio
from collections.abc import Callable
import logging
import re
from typing import TypeAlias
from wakeonlan import send_magic_packet

from trinnov_altitude import const, exceptions, messages

Callback: TypeAlias = Callable[[str, messages.Message | None], None]


class TrinnovAltitude:
    """
    Trinnov Altitude

    A class for interfacing with the Trinnov Altitude processor via the TCP/IP protocol.
    """

    DEFAULT_CLIENT_ID = "py-trinnov-altitude"
    DEFAULT_PORT = 44100
    DEFAULT_TIMEOUT = 2.0
    ENCODING = "ascii"
    VALID_OUIS = [
        "c8:7f:54",  # ASUSTek OUI (components inside Altitudes)
        "64:98:9e",  # Trinnov's OUI
    ]
    VOLUME_MIN = -120.0
    VOLUME_MAX = 20.0

    # Use a sentinel value to signal that the DEFAULT_TIMEOUT should be used.
    # This allows users to pass None and disable the timeout to wait indefinitely.
    USE_DEFAULT_TIMEOUT = -1.0

    @classmethod
    def validate_mac(cls, mac_address):
        """
        Validate, to the best of our abilities, that the Mac address is a
        valid Trinnov Altitude Mac address.
        ."""

        normalized_mac_address = mac_address.lower()

        # Verify the format
        pattern = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
        if pattern.match(normalized_mac_address) is None:
            raise exceptions.MalformedMacAddressError(mac_address)

        # Verify it starts with Trinnov associates OUIs
        mac_oui = normalized_mac_address[:8]
        if not any(mac_oui == oui for oui in cls.VALID_OUIS):
            raise exceptions.InvalidMacAddressOUIError(mac_oui, cls.VALID_OUIS)

        return True

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        mac: str | None = None,
        client_id: str = DEFAULT_CLIENT_ID,
        timeout: float = DEFAULT_TIMEOUT,
        logger: logging.Logger = logging.getLogger(__name__),
    ):
        if mac is not None:
            self.__class__.validate_mac(mac)

        # Settings
        self.host = host
        self.port = port
        self.mac = mac
        self.client_id = client_id
        self.timeout = timeout
        self.logger = logger

        # State
        self.audiosync: str | None = None
        self.bypass: bool | None = None
        self.decoder: str | None = None
        self.dim: bool | None = None
        self.id: str | None = None
        self.mute: bool | None = None
        self.preset: str | None = None
        self.presets: dict[int, str] = {}
        self.source: str | None = None
        self.source_format: str | None = None
        self.sources: dict[int, str] = {}
        self.upmixer: str | None = None
        self.version: str | None = None
        self.volume: float | None = None

        # Utility
        self._callbacks: set[Callback] = set()
        self._initial_sync = asyncio.Event()
        self._reader: asyncio.StreamReader | None = None
        self._response_handler_task: asyncio.Task | None = None
        self._writer: asyncio.StreamWriter | None = None

    # --------------------------
    # Connection
    # --------------------------

    async def connect(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        """Initiates the TCP connection to the processor"""
        if self.connected():
            self.logger.warn(
                "Trinnov Altitude already connected, use `reconnect` to establish a new connection"
            )
            return

        self.logger.info("Connecting to Trinnov Altitude: %s:%s", self.host, self.port)

        if timeout is self.USE_DEFAULT_TIMEOUT:
            timeout = self.timeout

        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout
            )
        except asyncio.TimeoutError as e:
            raise exceptions.ConnectionTimeoutError from e
        except (OSError, ValueError) as e:
            raise exceptions.ConnectionFailedError(e)
        else:
            # Default these values since the Trinnov Altitude will only
            # send them upon connect if they are active.
            self.bypass = False
            self.dim = False
            self.mute = False

            # Fire the callback to signal a connection state change
            for callback in self._callbacks:
                callback("connected", None)

            await self._write(f"id {self.client_id}", timeout)
            await self._write("send volume", timeout)
            await self.preset_get(timeout)
            await self.source_get(timeout)

    def connected(self) -> bool:
        """Returns the connection state."""
        return self._reader is not None and self._writer is not None

    def deregister_callback(self, callback: Callback):
        """
        Deregister a callback.
        """
        self._callbacks.remove(callback)

    async def disconnect(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        """Closes the TCP connection to the processor"""
        if self._writer is None:
            self.logger.warning("Not connected to Trinnov Altitude, can't disconnect")
            return

        if timeout is self.USE_DEFAULT_TIMEOUT:
            timeout = self.timeout

        self._writer.close()
        self._reader = None
        self._writer = None

        # Reset state
        self.audiosync = None
        self.bypass = None
        self.decoder = None
        self.dim = None
        self.mute = None
        self.preset = None
        self.source = None
        self.source_format = None
        self.upmixer = None
        self.volume = None

        # Fire the callback to signal a connection state change
        for callback in self._callbacks:
            callback("disconnected", None)

    async def reconnect(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        """
        Reconnect to the processor.

        This will close any active connections and open a new one. This method
        must be used if you watn to explicitly reconnect, as `connect` will
        return early if a connection is already established.
        """
        if self._writer:
            await self.disconnect(timeout)

        await self.connect(timeout)

    def register_callback(self, callback: Callback):
        """
        Register a callback to be fired when messages are received from
        the processor.
        """
        self._callbacks.add(callback)

    def start_listening(
        self,
        callback: Callback | None = None,
        reconnect: bool = True,
        backoff: int = 2,
    ):
        if callback:
            self.register_callback(callback)

        self._response_handler_task = asyncio.create_task(
            self._listen(reconnect, backoff)
        )

    async def stop_listening(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        if self._response_handler_task:
            if timeout is self.USE_DEFAULT_TIMEOUT:
                timeout = self.timeout

            self._response_handler_task.cancel()
            await asyncio.wait_for(self._response_handler_task, timeout)
            self._response_handler_task = None

    async def wait_for_initial_sync(self, timeout: int | float | None = 10):
        """
        Wait for the initial sync from the processor.

        This is a basic method that returns when id, presets, sources, and version
        are set. There is no guarantee regarding when the processor will respond
        to a new client with current state messages. Additionally, there is no
        message indicating that the initial synchronization is complete. Therefore,
        the best approach is to monitor for changes that suggest the initial
        synchronization has been completed.
        """

        await asyncio.wait_for(self._initial_sync.wait(), timeout)

    # --------------------------
    # Properties
    # --------------------------
    def volume_percentage(self) -> float | None:
        if self.volume is None:
            return None

        return (
            (self.volume - self.VOLUME_MIN) / (self.VOLUME_MAX - self.VOLUME_MIN)
        ) * 100

    # --------------------------
    # Commands
    # --------------------------

    async def acoustic_correction_off(
        self, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Turn the acoustic correction off.
        """
        await self.acoustic_correction_set(False)

    async def acoustic_correction_on(
        self, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Turn the acoustic correction on.
        """
        await self.acoustic_correction_set(True)

    async def acoustic_correction_set(
        self, state: bool, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Set the acoustic correction to On (True) or Off (False)
        """
        await self._write(f"use_acoustic_correct {int(state)}", timeout)

    async def acoustic_correction_toggle(
        self, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Toggle the acoustic correction state.
        """
        await self._write("use_acoustic_correct 2", timeout)

    async def bypass_off(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        """
        Turn the bypass off
        """
        await self.bypass_set(False)

    async def bypass_on(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        """
        Turn the bypass on
        """
        await self.bypass_set(True)

    async def bypass_set(
        self, state: bool, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Set the bypass state to On (True) or Off (False)
        """
        await self._write(f"bypass {int(state)}", timeout)

    async def bypass_toggle(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        """
        Toggle the bypass state.
        """
        await self._write("bypass 2", timeout)

    async def dim_off(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        """
        Turn the dim off.
        """
        await self.dim_set(False)

    async def dim_on(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        """
        Turn the dim on.
        """
        await self.dim_set(True)

    async def dim_set(
        self, state: bool, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Set the dim state to On (True) or Off (False)
        """
        await self._write(f"dim {int(state)}", timeout)

    async def dim_toggle(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        """
        Toggle the dim state.
        """
        await self._write("dim 2", timeout)

    async def front_display_off(
        self, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Turn the front display off.
        """
        await self.front_display_set(False)

    async def front_display_on(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        """
        Turn the front display on.
        """
        await self.front_display_set(True)

    async def front_display_set(
        self, state: bool, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Set the front display of the processor to On (True) or Off (False).
        """
        await self._write(f"fav_light {int(state)}", timeout)

    async def front_display_toggle(
        self, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Toggle the front display of the processor.
        """
        await self._write("dim 2", timeout)

    async def level_alignment_off(
        self, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Turn the level alignment off.
        """
        await self.level_alignment_set(False)

    async def level_alignment_on(
        self, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Turn the level alignment on.
        """
        await self.level_alignment_set(True)

    async def level_alignment_set(
        self, state: bool, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Set the level alignment state to On (True) or Off (False)
        """
        await self._write(f"use_level_alignment {int(state)}", timeout)

    async def level_alignment_toggle(
        self, state, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Toggle the level alignment state.
        """
        await self._write("use_level_alignment 2", timeout)

    async def mute_off(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        """
        Turn the mute off.
        """
        await self.mute_set(False)

    async def mute_on(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        """
        Turn the mute on.
        """
        await self.mute_set(True)

    async def mute_set(
        self, state: bool, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Set the mute state to On (True) or Off (False)
        """
        await self._write(f"mute {int(state)}", timeout)

    async def mute_toggle(
        self, state, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Toggle the mute state.
        """
        await self._write("mute 2", timeout)

    async def page_adjust(
        self, delta: int, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Changes the menu page currently on the GUI. `delta` indicates the number of
        pages to change, and may be positive or negative.
        """
        await self._write(f"page_adjust {delta}", timeout)

    async def page_down(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        """
        Changes the menu page currently on the GUI down by one page.
        """
        await self.page_adjust(-1)

    async def page_up(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        """
        Changes the menu page currently on the GUI up by one page.
        """
        await self.page_adjust(1)

    async def power_off(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        """Power off."""
        await self._write("power_off_SECURED_FHZMCH48FE", timeout)

    def power_on(self):
        """Power on."""
        if self.mac is None:
            raise exceptions.NoMacAddressError()

        send_magic_packet(self.mac)

    def power_on_available(self) -> bool:
        """
        Can the device be powered on.

        A mac address is required to do so.
        """
        return self.mac is not None

    async def preset_get(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        """
        Requests the current present.
        """
        await self._write("get_current_preset", timeout)

    async def preset_set(
        self, id: int, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Set the preset identified by `id`. Preset `0` is the built-in preset and
        presets >= `1` are user defined presets.
        """
        await self._write(f"loadp {id}", timeout)

    async def quick_optimized_off(
        self, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Turn quick optimized off.
        """
        await self.quick_optimized_set(False)

    async def quick_optimized_on(
        self, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Turn quick optimized on.
        """
        await self.quick_optimized_set(True)

    async def quick_optimized_set(
        self, state: bool, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Set the quick optimized state to On (True) or Off (False)
        """
        await self._write(f"quick_optimized {int(state)}", timeout)

    async def quick_optimized_toggle(
        self, state, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Toggle the quick optimized state.
        """
        await self._write("quick_optimized 2", timeout)

    async def remapping_mode_set(
        self,
        mode: const.RemappingMode,
        timeout: int | float | None = USE_DEFAULT_TIMEOUT,
    ):
        """
        Set the remapping mode. See `const.RemappingMode` for available options
        and descriptions.
        """
        await self._write(f"remapping_mode {mode.value}", timeout)

    async def source_get(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        """
        Requests the current source.
        """
        await self._write("get_current_profile", timeout)

    async def source_set(
        self, id: int, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Set the source identified by `id`, where `0` is the first source.
        """
        await self._write(f"profile {id}", timeout)

    async def source_set_by_name(
        self, name: str, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Set the source identified by `name` from `sources`.
        """
        for source_id, source_name in self.sources.items():
            if source_name == name:
                await self.source_set(source_id)
                return

    async def time_alignment_off(
        self, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Turn time alignment off.
        """
        await self.time_alignment_set(False)

    async def time_alignment_on(
        self, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Turn time alignment on.
        """
        await self.time_alignment_set(True)

    async def time_alignment_set(
        self, state: bool, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Set the time alignment state to On (True) or Off (False)
        """
        await self._write(f"use_time_alignment {int(state)}", timeout)

    async def time_alignment_toggle(
        self, state, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Toggle the time alignment state.
        """
        await self._write("use_time_alignment 2", timeout)

    async def upmixer_set(
        self, mode: const.UpmixerMode, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Set the upmixer mode. See `const.UpmixerMode` for available options
        and descriptions.
        """
        await self._write(f"remapping_mode {mode.value}", timeout)

    async def volume_adjust(
        self, delta: int | float, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Adjust the volume by a relative dB value (float).
        """
        await self._write(f"dvolume {delta}", timeout)

    async def volume_down(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        """
        Lower the volume by 0.5 dB
        """
        await self.volume_adjust(-0.5, timeout)

    async def volume_percentage_set(self, percentage: float):
        """
        Set the volume based on a percentage.
        """
        if not (0 <= percentage <= 100):
            raise ValueError("Percentage must be between 0 and 100")

        # Calculate the corresponding volume level from the percentage
        volume = (
            (percentage / 100) * (self.VOLUME_MAX - self.VOLUME_MIN)
        ) + self.VOLUME_MIN
        volume = round(volume, 1)

        await self.volume_set(volume)

    async def volume_set(
        self, db: int | float, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ):
        """
        Set the volume to an absolute dB value.
        """
        await self._write(f"volume {db}", timeout)

    async def volume_ramp(
        self,
        db: int | float,
        duration: int,
        timeout: int | float | None = USE_DEFAULT_TIMEOUT,
    ):
        """
        Ramp the volume to an absolute dB value (float) over a number of milliseconds (int).
        """
        await self._write(f"volume_ramp {db} {duration}", timeout)

    async def volume_up(self, timeout: int | float | None = USE_DEFAULT_TIMEOUT):
        """
        Raise the volume by 0.5 dB
        """
        await self.volume_adjust(0.5, timeout)

    # --------------------------
    # Utility
    # --------------------------
    async def _listen(
        self,
        read_timeout: float = 30.0,
        read_backoff: float = 1.0,
        reconnect: bool = True,
        reconnect_timeout: float = 2.0,
        reconnect_backoff: float = 2.0,
    ):
        """
        Listen for messages and sync internal state

        This method will automatically reconnect when necessary if `reconnect`
        is set to `True`.
        """
        try:
            while True:
                try:
                    await self._read(read_timeout)
                except asyncio.TimeoutError:
                    self.logger.debug(
                        f"Read operation timed out, trying again in {read_backoff} seconds"
                    )
                    await asyncio.sleep(read_backoff)
                except (exceptions.NotConnectedError, EOFError, OSError) as e:
                    if reconnect:
                        self.logger.debug(
                            f"Unable to read message from Trinnov Altitude, reconnecting...: {e}",
                        )

                        try:
                            await self.reconnect(timeout=reconnect_timeout)
                        except (
                            asyncio.TimeoutError,
                            exceptions.ConnectionTimeoutError,
                            exceptions.ConnectionFailedError,
                        ) as e:
                            self.logger.debug(
                                f"Trinnov Altitude reconnect failed, trying again in {reconnect_backoff} seconds...: {e}"
                            )
                            await asyncio.sleep(reconnect_backoff)
                    else:
                        raise e
        except asyncio.CancelledError:
            self.logger.debug(
                "Trinnov Altitude listen task received cancel, shutting down..."
            )

    def _process_message(self, raw_message: str) -> messages.Message:  # noqa: C901
        """Receive a single message off of the socket and process it."""
        print(raw_message)
        message = messages.message_factory(raw_message)

        if isinstance(message, messages.AudiosyncMessage):
            self.audiosync = message.mode
        elif isinstance(message, messages.BypassMessage):
            self.bypass = message.state
        elif isinstance(message, messages.CurrentPresetMessage):
            self.preset = self.presets.get(message.index)
        elif isinstance(message, messages.CurrentSourceFormat):
            self.source_format = message.format
        elif isinstance(message, messages.CurrentSourceMessage):
            self.source = self.sources.get(message.index)
        elif isinstance(message, messages.DecoderMessage):
            self.decoder = message.decoder
            self.upmixer = message.upmixer
        elif isinstance(message, messages.DimMessage):
            self.dim = message.state
        elif isinstance(message, messages.ErrorMessage):
            self.logger.error(
                f"Received error message from Trinnov Altitude: {message.error}"
            )
        elif isinstance(message, messages.PresetMessage):
            self.presets[message.index] = message.name
        elif isinstance(message, messages.PresetsClearMessage):
            self.presets = {}
        elif isinstance(message, messages.MuteMessage):
            self.mute = message.state
        elif isinstance(message, messages.SourceMessage):
            self.sources[message.index] = message.name
        elif isinstance(message, messages.SourcesClearMessage):
            self.sources = {}
        elif isinstance(message, messages.SamplingRateMessage):
            self.sampling_rate = message.rate
        elif isinstance(message, messages.VolumeMessage):
            self.volume = message.volume
        elif isinstance(message, messages.WelcomeMessage):
            self.version = message.version
            self.id = message.id

        if message is not None:
            for callback in self._callbacks:
                callback("received_message", message)

        if (
            not self._initial_sync.is_set()
            and self.id is not None
            and self.presets != {}
            and self.sources != {}
            and self.version is not None
        ):
            self._initial_sync.set()

        return message

    async def _read(
        self, timeout: int | float | None = USE_DEFAULT_TIMEOUT
    ) -> None | messages.Message:
        """Read a single raw message off of the socket"""
        if self._reader is None:
            raise exceptions.NotConnectedError()

        if timeout is self.USE_DEFAULT_TIMEOUT:
            timeout = self.timeout

        raw_message = await asyncio.wait_for(self._reader.readline(), timeout)

        if raw_message == b"":
            self.logger.debug(
                "Received EOF from Trinnov Altitude, closing connection..."
            )
            await self.disconnect()
            raise exceptions.NotConnectedError()
        else:
            raw_message = raw_message.decode().rstrip()
            self.logger.debug(f"Received message from Trinnov Altitude: {raw_message}")
            return self._process_message(raw_message)

    async def _write(self, message: str, timeout: float | None):
        """Write a single message to the socket"""
        if self._writer is None:
            raise exceptions.NotConnectedError()

        if timeout is self.USE_DEFAULT_TIMEOUT:
            timeout = self.timeout

        if not message.endswith("\n"):
            message += "\n"

        message_bytes = message.encode(self.ENCODING)
        self._writer.write(message_bytes)

        try:
            await asyncio.wait_for(self._writer.drain(), timeout=timeout)
            self.logger.debug(f"Sent to Trinnov Altitude: {message.rstrip()}")
        except OSError as e:
            self.logger.debug(
                f"Encountered connection error while writing to Trinnov Altitude, closing connection...: {e}"
            )
            await self.disconnect()
            raise exceptions.NotConnectedError()
