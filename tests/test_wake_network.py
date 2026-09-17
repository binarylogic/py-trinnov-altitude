"""Wake-on-LAN routing is independent of the control transport."""

import socket
from unittest.mock import patch

import pytest

from trinnov_altitude.client import TrinnovAltitudeClient
from trinnov_altitude.lifecycle import PowerState


@pytest.mark.asyncio
@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize(
    "options,expected",
    [
        ({}, {"ip_address": "255.255.255.255", "port": 9, "interface": None, "address_family": socket.AF_INET}),
        (
            {"wol_host": "192.168.20.255", "wol_port": 7, "wol_interface": "192.168.10.2", "wol_family": socket.AF_INET},
            {"ip_address": "192.168.20.255", "port": 7, "interface": "192.168.10.2", "address_family": socket.AF_INET},
        ),
        (
            {"wol_host": "ff02::1", "wol_family": socket.AF_INET6},
            {"ip_address": "ff02::1", "port": 9, "interface": None, "address_family": socket.AF_INET6},
        ),
    ],
)
async def test_wake_routes_packet(asynchronous, options, expected):
    client = TrinnovAltitudeClient(host="control.example", mac="00:11:22:33:44:55", **options)
    with patch("trinnov_altitude.client.send_magic_packet") as send:
        if asynchronous:
            await client.wake()
        else:
            client.power_on()
    send.assert_called_once_with(client.mac, **expected)
    assert client.runtime.power is PowerState.WAKING
    assert client.host == "control.example"
    assert client.port == 44100


def test_local_send_failure_does_not_claim_waking():
    client = TrinnovAltitudeClient(host="unused", mac="00:11:22:33:44:55")
    before = client.runtime.power
    with (
        patch("trinnov_altitude.client.send_magic_packet", side_effect=OSError("No route")),
        pytest.raises(OSError, match="No route"),
    ):
        client.power_on()
    assert client.runtime.power is before


@pytest.mark.parametrize("options", [{"wol_host": " "}, {"wol_port": 0}, {"wol_port": 65536}, {"wol_family": socket.AF_UNIX}])
def test_invalid_wake_configuration(options):
    with pytest.raises(ValueError):
        TrinnovAltitudeClient(host="unused", **options)


def test_real_udp_magic_packet():
    """Exercise the dependency with a loopback socket, without waking hardware."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        receiver.bind(("127.0.0.1", 0))
        receiver.settimeout(1)
        client = TrinnovAltitudeClient(
            host="unused",
            mac="00:11:22:33:44:55",
            wol_host="127.0.0.1",
            wol_port=receiver.getsockname()[1],
            wol_interface="127.0.0.1",
        )
        client.power_on()
        packet, sender = receiver.recvfrom(1024)
    assert packet == b"\xff" * 6 + bytes.fromhex("001122334455") * 16
    assert sender[0] == "127.0.0.1"
