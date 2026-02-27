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
uv run mypy trinnov_altitude
uv run pytest -v
```

Or use task wrappers:

```bash
task dev
task check
```

## Release

1. Update version in `trinnov_altitude/__init__.py`.
2. Update `CHANGELOG.md`.
3. Merge to `master` (CI runs quality/tests/package checks).
4. Create a prerelease tag like `vX.Y.Zrc1` to publish to TestPyPI.
5. Create a full release tag like `vX.Y.Z` to publish to PyPI.
6. Ensure release tag matches `__version__` (workflow enforces this).

## Maintenance

- Migration guide: [docs/MIGRATION_V2.md](docs/MIGRATION_V2.md)
- Maintainer runbook: [docs/MAINTAINERS.md](docs/MAINTAINERS.md)
