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
  - In that profile, `META_PRESET_LOADED <n>` is normalized as a source-change signal

Catalog messages may arrive late, be refreshed, or be absent. Consumers should not assume labels are always present.

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
