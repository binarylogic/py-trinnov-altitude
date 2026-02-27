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

    INITIAL_MESSAGES = [
        "OK",
        "SOURCES_CHANGED",
        "CURRENT_SOURCE_FORMAT_NAME Atmos narrow",
        "VOLUME -40.0",
        "BYPASS 0",
        "DIM 0",
        "MUTE 0",
        "LABELS_CLEAR",
        "LABEL 0: Builtin",
        "PROFILES_CLEAR",
        "PROFILE 0: Apple TV",
        "SRATE 48000",
        "AUDIOSYNC Slave",
        "CURRENT_PROFILE 0",
        "CURRENT_PRESET 0",
    ]

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.server: asyncio.AbstractServer | None = None
        self.logger = logging.getLogger(__name__)

        self.active_handlers: set[asyncio.Task] = set()
        self.volume = -40.0

    async def start_server(self) -> None:
        self.logger.info("Starting mock Trinnov Altitude server on %s:%d", self.host, self.port)
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
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

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.logger.debug("Client connected")

        task = asyncio.current_task()
        if task is not None:
            self.active_handlers.add(task)

        power_off = False

        try:
            writer.write(b"Welcome on Trinnov Optimizer (Version 4.3.2rc1, ID 10485761)\n")
            await writer.drain()

            await asyncio.sleep(0.1)

            for message in self.INITIAL_MESSAGES:
                writer.write(f"{message}\n".encode(self.ENCODING))
                await writer.drain()

            while True:
                message_bytes = await reader.readline()
                if not message_bytes:
                    break

                message = message_bytes.decode(self.ENCODING).strip()
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

    def _handle_message(self, message: str) -> list[str]:
        self.logger.debug("Received message from client: %s", message)

        if match := re.match(r"^dvolume\s(-?\d+(\.\d+)?)$", message):
            delta = float(match.group(1))
            self.volume += delta
            return ["OK", f"VOLUME {self.volume}"]
        if re.match(r"^id\s.*", message):
            return ["OK"]
        if match := re.match(r"^volume\s(-?\d+(\.\d+)?)$", message):
            self.volume = float(match.group(1))
            return ["OK", f"VOLUME {self.volume}"]
        return [f"ERROR: invalid command: {message}"]
