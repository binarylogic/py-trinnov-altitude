"""Utilities for mocking a Trinnov Altitude server for development/testing."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re


class MockTrinnovAltitudeServer:
    """Simple TCP mock for local protocol development."""

    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 44100
    ENCODING = "ascii"

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        *,
        presets: dict[int, str] | None = None,
        sources: dict[int, str] | None = None,
        current_preset_index: int = 0,
        current_source_index: int = 0,
        preset_readback_lag: int = 0,
    ):
        self.host = host
        self.port = port
        self.server: asyncio.AbstractServer | None = None
        self.logger = logging.getLogger(__name__)

        self.active_handlers: set[asyncio.Task] = set()
        self.received_messages: list[str] = []
        self.presets = presets or {0: "Builtin", 1: "Movies", 2: "Music"}
        self.sources = sources or {0: "Apple TV", 1: "Blu-ray"}
        self.current_preset_index = current_preset_index
        self.current_source_index = current_source_index
        self.preset_readback_lag = preset_readback_lag
        self._pending_preset_index: int | None = None
        self._preset_readbacks_remaining = 0
        self.volume = -40.0

    async def start_server(self) -> None:
        self.logger.info("Starting mock Trinnov Altitude server on %s:%d", self.host, self.port)
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
        sockets = self.server.sockets or []
        if sockets:
            self.port = int(sockets[0].getsockname()[1])
        self.logger.info("Mock Trinnov Altitude server started")
        await self.server.start_serving()

    async def stop_server(self) -> None:
        self.logger.info("Stopping mock Trinnov Altitude server")

        if not self.server:
            return

        self.server.close()

        for task in tuple(self.active_handlers):
            task.cancel()

        await asyncio.gather(*self.active_handlers, return_exceptions=True)
        await self.server.wait_closed()

        self.logger.info("Mock server stopped")

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:  # noqa: C901
        self.logger.debug("Client connected")

        task = asyncio.current_task()
        if task is not None:
            self.active_handlers.add(task)

        power_off = False

        try:
            writer.write(b"Welcome on Trinnov Optimizer (Version 4.3.2rc1, ID 10485761)\n")
            await writer.drain()

            await asyncio.sleep(0.1)

            for message in self._initial_messages():
                writer.write(f"{message}\n".encode(self.ENCODING))
                await writer.drain()

            while True:
                message_bytes = await reader.readline()
                if not message_bytes:
                    break

                message = message_bytes.decode(self.ENCODING).strip()
                self.received_messages.append(message)
                if message == "power_off_SECURED_FHZMCH48FE":
                    self.logger.info("Received shut down signal")
                    power_off = True
                    break
                if message == "bye":
                    break

                responses = self._handle_message(message)
                for response in responses:
                    writer.write(f"{response}\n".encode(self.ENCODING))
                    await writer.drain()
        except (asyncio.CancelledError, OSError):
            pass
        finally:
            if task is not None:
                self.active_handlers.discard(task)
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()

            self.logger.info("Client disconnected")

            if power_off:
                await self.stop_server()

    def _initial_messages(self) -> list[str]:
        messages = [
            "OK",
            "SOURCES_CHANGED",
            "CURRENT_SOURCE_FORMAT_NAME Atmos narrow",
            f"VOLUME {self.volume}",
            "BYPASS 0",
            "DIM 0",
            "MUTE 0",
            "LABELS_CLEAR",
        ]
        messages.extend(f"LABEL {index}: {name}" for index, name in sorted(self.presets.items()))
        messages.append("PROFILES_CLEAR")
        messages.extend(f"PROFILE {index}: {name}" for index, name in sorted(self.sources.items()))
        messages.extend(
            [
                "SRATE 48000",
                "AUDIOSYNC Slave",
                f"CURRENT_PROFILE {self.current_source_index}",
                f"CURRENT_PRESET {self.current_preset_index}",
                "UPMIXER auto",
            ]
        )
        return messages

    def _handle_message(self, message: str) -> list[str]:
        self.logger.debug("Received message from client: %s", message)

        responses = self._handle_selector_message(message)
        if responses is not None:
            return responses

        responses = self._handle_state_message(message)
        if responses is not None:
            return responses

        responses = self._handle_volume_message(message)
        if responses is not None:
            return responses

        return [f"ERROR: invalid command: {message}"]

    def _handle_state_message(self, message: str) -> list[str] | None:
        if re.match(r"^id\s.*", message):
            return ["OK"]
        if message == "get_current_state":
            return [
                f"VOLUME {self.volume}",
                "BYPASS 0",
                "DIM 0",
                "MUTE 0",
            ]
        if message == "upmixer":
            return ["UPMIXER auto"]
        return None

    def _handle_volume_message(self, message: str) -> list[str] | None:
        if match := re.match(r"^dvolume\s(-?\d+(\.\d+)?)$", message):
            delta = float(match.group(1))
            self.volume += delta
            return ["OK", f"VOLUME {self.volume}"]
        if match := re.match(r"^volume\s(-?\d+(\.\d+)?)$", message):
            self.volume = float(match.group(1))
            return ["OK", f"VOLUME {self.volume}"]
        return None

    def _handle_selector_message(self, message: str) -> list[str] | None:
        if message == "get_current_preset":
            return [f"CURRENT_PRESET {self._read_current_preset()}"]
        if message == "get_all_label":
            return [f"LABEL {index}: {name}" for index, name in sorted(self.presets.items())]
        if match := re.match(r"^get_label\s(-?\d+)$", message):
            preset_id = int(match.group(1))
            if preset_id not in self.presets:
                return ["ERROR: unknown preset"]
            return [f"LABEL {preset_id}: {self.presets[preset_id]}"]
        if match := re.match(r"^loadp\s(-?\d+)$", message):
            self._set_pending_preset(int(match.group(1)))
            return ["OK"]
        if message == "get_current_profile":
            return [f"CURRENT_PROFILE {self.current_source_index}"]
        if match := re.match(r"^get_profile_name\s(-?\d+)$", message):
            source_id = int(match.group(1))
            if source_id not in self.sources:
                return ["ERROR: unknown source"]
            return [f"PROFILE {source_id}: {self.sources[source_id]}"]
        if match := re.match(r"^profile\s(-?\d+)$", message):
            self.current_source_index = int(match.group(1))
            return ["OK", f"CURRENT_PROFILE {self.current_source_index}"]
        return None

    def _set_pending_preset(self, preset_id: int) -> None:
        self._pending_preset_index = preset_id
        self._preset_readbacks_remaining = self.preset_readback_lag

    def _read_current_preset(self) -> int:
        if self._pending_preset_index is None:
            return self.current_preset_index
        if self._preset_readbacks_remaining > 0:
            self._preset_readbacks_remaining -= 1
            return self.current_preset_index
        self.current_preset_index = self._pending_preset_index
        self._pending_preset_index = None
        return self.current_preset_index
