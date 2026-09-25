# Trinnov Altitude Python Library

[![CI](https://github.com/binarylogic/py-trinnov-altitude/actions/workflows/test.yml/badge.svg)](https://github.com/binarylogic/py-trinnov-altitude/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/trinnov-altitude)](https://pypi.org/project/trinnov-altitude/)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://pypi.org/project/trinnov-altitude/)

Async Trinnov Altitude client for long-running integrations (Home Assistant primary target).

## Version 2.0

Version `2.x` is a clean break from `1.x`.

- No compatibility shims
- New lifecycle (`start` / `wait_synced` / `stop`)
- New state model (`client.state`)
- Optional command ACK handling

Read the migration guide: [docs/MIGRATION_V2.md](docs/MIGRATION_V2.md)

## Installation

```bash
pip install trinnov-altitude
```

## Quick Start

```python
import asyncio

from trinnov_altitude.client import TrinnovAltitudeClient


async def main() -> None:
    client = TrinnovAltitudeClient(host="192.168.1.90")

    try:
        await client.start()
        await client.wait_synced(timeout=10)

        await client.volume_set(-30.0)
        await client.mute_on()

        print(client.state.volume)
        print(client.state.source)
    finally:
        await client.stop()


asyncio.run(main())
```

## Lifecycle

- `await client.start()` connects, bootstraps, and starts the read loop.
- `await client.wait_synced()` waits until welcome + catalogs + current indices are observed.
- `await client.stop()` stops listener and disconnects cleanly.

### Processor power

Client connection lifecycle and processor power are separate. `stop()` closes the
client; it does not power down the processor.

- `await client.power_off()` sends the secured shutdown command and waits for its
  acknowledgement. Concurrent requests share the pending command. Cancelling a
  requesting task does not cancel acknowledgement handling for an already-sent
  shutdown; `stop()` still terminates the client's pending work.
- `await client.wake(shutdown_timeout=60.0)` waits for any pending shutdown
  acknowledgement and, after acknowledged shutdown, for the old connection to
  close before requesting Wake-on-LAN. The acknowledgement uses the command
  timeout; the disconnect wait has its own bounded `shutdown_timeout`.
- A successful wake request does **not** mean boot is complete. Connection,
  synchronization, and `runtime.power` provide subsequent readiness feedback.
  Wake-on-LAN requires a configured MAC address.
- `runtime.power == PowerState.OFF` following `power_off()` means shutdown was
  acknowledged, not that the hardware has already finished powering down. An
  unexplained connection loss is not evidence of acknowledged shutdown.

Starting with 3.3.12, synchronous `power_on()` raises `CommandRejectedError` if a
shutdown acknowledgement is pending or acknowledged shutdown still has an open
connection. Async callers that want to wait through this transition should use
`await client.wake()`. This prevents the previous connection from being mistaken
for a newly ready processor. `power_off()` also now requires acknowledgement;
command failures propagate instead of reporting unconfirmed shutdown as success.

### Liveness & reconnect

The control connection is a long-lived TCP push session, so a silent read is
ambiguous: a healthy link is quiet whenever nothing is changing, but a dead link
(an idle-killed half-open socket, or a processor whose control thread has wedged
while its TCP stack still ACKs) looks identical. To tell them apart, when the link
has been quiet for `heartbeat_interval` seconds the client sends a read-only probe
(`get_current_state`); if no traffic arrives within `heartbeat_timeout`, the link is
treated as dead and `auto_reconnect` kicks in. `TcpTransport` also enables
`SO_KEEPALIVE` as an OS-level backstop.

```python
client = TrinnovAltitudeClient(
    host="192.168.1.90",
    heartbeat_interval=20.0,  # seconds of quiet before a liveness probe (None disables)
    heartbeat_timeout=5.0,    # seconds to wait for the probe response before reconnecting
)
```

### State reconciliation

Push messages remain the fast path for state updates. As a backstop for an
individual dropped notification, the client also requests the processor's
current state every `reconcile_interval` seconds. This schedule is independent
of ordinary push traffic, so unrelated messages cannot leave one cached field
stale indefinitely.

```python
client = TrinnovAltitudeClient(
    host="192.168.1.90",
    reconcile_interval=30.0,  # None disables periodic reconciliation
)
```

## Protocol Semantics

The client parses raw messages first, then normalizes them into canonical state events.
This keeps protocol quirks isolated and keeps the state reducer deterministic.

- Canonical identity:
  - `CURRENT_PRESET <n>`
  - `CURRENT_PROFILE <n>` or index-only `PROFILE <n>`
  - `DECODER ... UPMIXER <mode>`
- Optional catalogs:
  - Presets via `LABELS_CLEAR` + `LABEL <n>: <name>`
  - Sources via `PROFILES_CLEAR` + `PROFILE <n>: <name>`
- Quirk profiles:
  - `altitude_ci` is selected when `IDENTS` includes `altitude_ci`
  - `META_PRESET_LOADED <n>` requests authoritative preset/source readbacks; it does not set either identity directly

Catalog messages may arrive late, be refreshed, or be absent. Consumers should not assume labels are always present.

### Text normalization

The parser matches ASCII protocol keywords without regard to case and preserves
captured labels and unfamiliar values. The transport removes only the line ending.
Known upmixer values are normalized centrally, including case, surrounding
whitespace, and underscore/space spelling. Both `UPMIXER <mode>` and an exact
known bare mode produce the same configured `state.upmixer`. `DECODER` messages
update only `state.active_upmixer`; these are distinct facts.

An unfamiliar prefixed mode remains visible verbatim (apart from surrounding
whitespace); it is not guessed from a partial match. For example, `dolby dolby`
is retained but is not treated as confirmation of `dolby`. A bare unrecognized
line remains unknown. Recognized bare replies do not increment unknown-message
counters. Adapters can use `normalizer.normalize_upmixer_mode()` rather than
maintaining their own spelling rules.

### Command completion and retries

TCP delivery, command acceptance, and observed device state are separate events.
The public operations intentionally make different guarantees:

| Operations | Return means | Automatic repetition |
| --- | --- | --- |
| `preset_set`, `upmixer_set` | Requested selector state observed, or an exception | Setting sent once; only readback queries repeat |
| `source_set`, `source_set_by_name` | Requested source observed, or an exception | Source command and readback can repeat, preserving existing source-selection behavior |
| `volume_set` | Setting and refresh query sent | Neither repeats; subsequent feedback updates state |
| Relative volume, toggles, remapping, other simple setters | Command sent | Never automatically replayed |
| `power_off` | Shutdown acknowledged | Concurrent callers share one shutdown request |
| `power_on`, `wake` | Wake requested (or already connected and synced) | Completion remains explicit in runtime lifecycle state |
| `command(..., wait_for_ack=True)` | An ACK was received, or an exception | No automatic retry; ACK is not selector completion |

Selector confirmation has a finite `selector_convergence_timeout` (default 5s)
and uses `selector_convergence_interval` (default 0.25s) between queries. The
confirmation deadline includes query I/O, and cancellation stops its polling.
A timeout raises `CommandConvergenceTimeoutError`; unrelated status pushes or
an ACK cannot confirm a different selector value. Preset/source setters may
return immediately when the requested value is already recorded.

`upmixer_set` now waits for confirmation instead of returning after sending a
single query. Callers should handle `CommandConvergenceTimeoutError` when the
processor never reports the requested mode. Existing command families retain
their documented semantics; toggles and relative changes must not be retried as
though they were absolute setters.

## Events

```python
def on_event(event, message):
    if event == "connected":
        ...
    elif event == "disconnected":
        ...
    elif event == "received_message":
        ...

client.register_callback(on_event)
```

Callback exceptions are isolated and logged (they do not crash the listener).

## HA Adapter

Use `trinnov_altitude.adapter.AltitudeStateAdapter` to convert mutable runtime state into immutable snapshots plus typed deltas/events:

- `snapshot`: stable full-state view for coordinator data
- `deltas`: field-level changes since previous snapshot
- `events`: integration-friendly event stream (volume, mute, source, preset, etc.)

You can wire this directly through the client:

```python
from trinnov_altitude.adapter import AltitudeStateAdapter

adapter = AltitudeStateAdapter()

def on_update(snapshot, deltas, events):
    ...

handle = client.register_adapter_callback(adapter, on_update)
# later: client.deregister_adapter_callback(handle)
```

For Home Assistant coordinator/event-bus integration, use `trinnov_altitude.ha_bridge`:

- `coordinator_payload(snapshot)`
- `to_ha_events(events)`
- `build_bridge_update(snapshot, deltas, events)`

## Command ACKs

You can use fire-and-forget commands (default) or explicit ACK waiting:

```python
await client.volume_set(-20.0)
await client.command("volume -20", wait_for_ack=True, ack_timeout=2.0)
```

## Development

```bash
uv sync --group dev
uv run ruff check .
uv run ruff format --check .
uv run ty check trinnov_altitude
uv run pytest -v
```

Or use task wrappers:

```bash
task dev
task check
```

## Real Device Integration Tests (Read-Only)

The test suite includes a manual, read-only integration tier for validating behavior against real hardware.

- Marker: `integration_real`
- Opt-in gate: `TRINNOV_ITEST=1`
- Target host: `TRINNOV_HOST=<ip-or-hostname>`
- Optional port override: `TRINNOV_PORT=44100`
- If the device is offline/unreachable, tests are skipped.

These tests intentionally avoid mutating commands (no power/preset/source/volume state changes).

```bash
TRINNOV_ITEST=1 TRINNOV_HOST=192.168.30.3 task test:integration-real
```

## Pyx (optional)

Pyx is optional in this repo. You can keep publishing to PyPI/TestPyPI only.

- Install via Pyx: authenticate `uv` with `PYX_API_KEY` and configure your Pyx
  index URL in `uv` (`uv add --index ...` / `uv sync`).
- Publish to Pyx: run the `Release` workflow manually with `target=pyx` after
  setting repository secrets `PYX_API_KEY` and `PYX_PUBLISH_URL`.
- No dual-publish requirement: use Pyx when you need private/internal package
  distribution or policy control.

## Release

1. Merge conventional-commit changes to `master`.
2. Wait for the `release-please` workflow to open/update a release PR.
3. Review and merge the release PR (this updates `CHANGELOG.md` and `__version__`).
4. Release Please creates the GitHub Release and tag.
5. The `Release` workflow publishes artifacts to PyPI automatically for published releases.
6. For TestPyPI or Pyx-only publishing, run `Release` manually with `workflow_dispatch`.

## Maintenance

- Migration guide: [docs/MIGRATION_V2.md](docs/MIGRATION_V2.md)
- Maintainer runbook: [docs/MAINTAINERS.md](docs/MAINTAINERS.md)
- Protocol reference used for implementation: [docs/Altitude Protocol.pdf](docs/Altitude%20Protocol.pdf) (v1.15, 2019-04-19)

### Wake-on-LAN network settings

The optional keyword-only constructor arguments `wol_host`, `wol_port`,
`wol_interface`, and `wol_family` apply to both `power_on()` and `await wake()`.
Defaults preserve IPv4 broadcast to `255.255.255.255:9` with the OS-selected
outgoing interface. The control connection's `host` and `port` are independent.

```python
import socket

client = TrinnovAltitudeClient(
    host="192.168.20.10",
    mac="00:11:22:33:44:55",
    wol_host="192.168.20.255",
    wol_port=9,
    wol_interface="192.168.10.2",
    wol_family=socket.AF_INET,
)
```

`wol_interface` is a local IP address in the application's network namespace,
not an interface name or the receiver's address. Use `socket.AF_INET6` for an IPv6 destination. The
network still needs to permit or relay the packet across VLANs; successful UDP
sending does not confirm delivery or readiness. Local socket errors propagate
to the caller without marking the device as waking.
