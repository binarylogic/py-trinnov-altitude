"""
Utilities for mocking a Trinnov Altitude
"""

import asyncio
import logging
import re
from trinnov_altitude.trinnov_altitude import TrinnovAltitude


class MockTrinnovAltitudeServer:
    """
    Mocks a real Trinnov Altitude

    This class starts a TCP server on the proviced `host` (default `localhost`)
    and mimics a real Trinnov Altitude server. This is useful for integration
    testing a Trinnov Altitude integration.
    """

    DEFAULT_HOST = "localhost"
    ENCODING = "ascii"

    INITIAL_MESSAGES = [
        "OK",
        "SOURCES_CHANGED",
        "OPTSOURCE 0 Source 1",
        "OK",
        "SOURCE 0",
        "CURRENT_SOURCE_FORMAT_NAME Atmos narrow",
        "CURRENT_SOURCE_CHANNELS_ORDER_IS_DCI 0",
        "CURRENT_SOURCE_CHANNELS_ORDER L-R-C-Ls-Rs-Lrs-Rrs-Ltm-Rtm-LFE",
        "START_RUNNING",
        "CALIBRATION_DONE",
        "STOP_COMPUTING",
        "REMAPPING_MODE none",
        "MON_VOL -40.0",
        "VOLUME -40.0",
        "DISPLAY_VOLUME -40.0",
        "MON_REMOTE_SPKER_MAIN -1",
        "MON_REMOTE_SPKER_ALT1 -1",
        "MON_REMOTE_SPKER_ALT2 -1",
        "MON_REMOTE_MAINSRC1 -1",
        "MON_REMOTE_MAINSRC2 -1",
        "MON_REMOTE_MAINSRC3 -1",
        "MON_REMOTE_MAINSRC4 -1",
        "MON_REMOTE_MAINSRC5 -1",
        "MON_REMOTE_MAINSRC6 -1",
        "MON_REMOTE_CUEIN0 -1",
        "MON_REMOTE_CUEIN1 -1",
        "MON_REMOTE_CUEIN2 -1",
        "MON_REMOTE_CUEIN3 -1",
        "MON_REMOTE_CUEOUT1 -1",
        "MON_REMOTE_CUEOUT2 -1",
        "MON_REMOTE_CUEOUT3 -1",
        "MON_REMOTE_CUEOUT4 -1",
        "MON_REMOTE_CUEOUT5 -1",
        "BYPASS 0",
        "DIM 0",
        "MUTE 0",
        "FAV_LIGHT 0",
        "RIAA_PHONO 0",
        'NETSTATUS ETH LINK "Connected" DHCP "1" IP "192.168.60.90" '
        'NETMASK "255.255.255.0" GATEWAY "192.168.60.1" DNS "192.168.60.1"',
        'NETSTATUS WLAN WLANMODE "ap" LINK "Disconnected" SSID "" AP_SSID '
        '"Altitude-2541" AP_PASSWORD "abc" AP_IP "192.168.12.101" AP_NETMASK '
        '"255.255.255.0" IP "0.0.0.0" NETMASK "0.0.0.0" WPA_STATE ""',
        'NETSTATUS SERVICE_STATUS "No connection to internet"',
        "OK",
        "LABELS_CLEAR",
        "LABEL 0: Builtin",
        "LABEL 1: MLP",
        "PROFILES_CLEAR",
        "PROFILE 0: Kaleidescape",
        "PROFILE 1: Apple TV",
        "PROFILE 2: PS 5",
        "PROFILE 3: HDMI 4",
        "PROFILE 4: HDMI 5",
        "PROFILE 5: HDMI 6",
        "PROFILE 6: HDMI 7",
        "PROFILE 7: HDMI 8",
        "PROFILE 8: NETWORK",
        "PROFILE 9: S/PDIF IN 1",
        "PROFILE 10: S/PDIF IN 2",
        "PROFILE 11: S/PDIF IN 3",
        "PROFILE 12: S/PDIF IN 4",
        "PROFILE 13: S/PDIF IN 7.1 PCM",
        "PROFILE 14: Optical IN 5",
        "PROFILE 15: Optical IN 6",
        "PROFILE 16: Optical IN 7",
        "PROFILE 17: Optical IN 8",
        "PROFILE 18: Optical IN 7.1 PCM",
        "PROFILE 19: DCI MCH AES IN",
        "PROFILE 20: AES IN 1",
        "PROFILE 21: AES IN 2",
        "PROFILE 22: ANALOG BAL IN 1",
        "PROFILE 23: ANALOG BAL IN 2",
        "PROFILE 24: ANALOG BAL IN 1+2 (MIC 4 XLR)",
        "PROFILE 25: MIC IN",
        "PROFILE 26: ANALOG SE1 IN 7.1",
        "PROFILE 27: ANALOG SE2 IN",
        "PROFILE 28: ANALOG SE3 IN",
        "PROFILE 29: ANALOG SE4 IN",
        "PROFILE 30: ROON",
        "OK",
        "SRATE 48000",
        "AUDIOSYNC_STATUS 0",
        "DECODER NONAUDIO 1 PLAYABLE 0 DECODER none UPMIXER none",
        "AUDIOSYNC Slave",
        "CURRENT_PROFILE 1",
        "CURRENT_PRESET -1",
    ]

    def __init__(self, host=DEFAULT_HOST, port=TrinnovAltitude.DEFAULT_PORT):
        # Configuration
        self.host = host
        self.port = port
        self.server = None
        self.logger = logging.getLogger(__name__)

        # State
        self.active_handlers = set()
        self.volume = -40

    async def start_server(self):
        self.logger.info(
            "Starting mock Trinnov Altitude server on %s:%d", self.host, self.port
        )
        self.server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        self.logger.info("Mock Trinnov Altitude server started")
        await self.server.start_serving()

    async def stop_server(self):
        self.logger.info("Stopping mock Trinnov Altitude server")

        if not self.server:
            return

        # Stop accepting new connections immediately
        self.server.close()

        # Cancel active handlers
        for task in self.active_handlers:
            task.cancel()

        # Wait for all active client handlers to acknowledge cancellation and cleanup
        await asyncio.gather(*self.active_handlers, return_exceptions=True)

        # Wait for the server to close
        await self.server.wait_closed()

        self.logger.info("Mock server stopped")

    async def handle_client(self, reader, writer):
        self.logger.debug("Client connected")

        task = asyncio.current_task()
        self.active_handlers.add(task)
        power_off = False

        try:
            # When you connect to an Altitude it will send a welcome message with
            # the firmware vesion and ID of the unit.
            writer.write(
                b"Welcome on Trinnov Optimizer (Version 4.3.2rc1, ID 10485761)\n"
            )
            await writer.drain()

            # An actual Altitude will wait to send the initial state messages
            await asyncio.sleep(0.1)

            # Upon connecting the Altitude will send a variety of messages reflecting
            # current state.
            for message in self.INITIAL_MESSAGES:
                writer.write(f"{message}\n".encode(self.ENCODING))
                await writer.drain()

            # Listen for messages
            while True:
                message_bytes = await reader.readline()
                if not message_bytes:
                    break

                message = message_bytes.decode(self.ENCODING).strip()
                if message == "power_off_SECURED_FHZMCH48FE":
                    self.logger.info("Received shut down signal")
                    power_off = True
                    break
                elif message == "bye":
                    break
                else:
                    responses = self._handle_message(message)

                    for response in responses:
                        writer.write(f"{response}\n".encode(self.ENCODING))
                        await writer.drain()
        except (asyncio.CancelledError, OSError):
            pass
        finally:
            self.active_handlers.discard(task)
            writer.close()

            try:
                await writer.wait_closed()
            except OSError:
                pass

            self.logger.info("Client disconnected")

            if power_off:
                await self.stop_server()

    def _handle_message(self, message):
        self.logger.debug("Received message from client: %s", message)

        if match := re.match(r"^dvolume\s(-?\d+(\.\d+)?)", message):
            delta = float(match.group(1))
            self.volume += delta
            return ["OK", f"VOLUME {self.volume}"]
        if match := re.match(r"^id (.*)", message):
            return ["OK"]
        elif match := re.match(r"^volume\s(-?\d+(\.\d+)?)", message):
            self.volume = float(match.group(1))
            return ["OK", f"VOLUME {self.volume}"]
        else:
            return [f"ERROR: invalid command: {message}"]
