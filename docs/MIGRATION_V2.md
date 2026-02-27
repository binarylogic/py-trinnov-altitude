# Migration Guide: v1 -> v2

Version `2.x` is a deliberate breaking change.

## Import paths

### Old

```python
from trinnov_altitude.trinnov_altitude import TrinnovAltitude
```

### New

```python
from trinnov_altitude.client import TrinnovAltitudeClient
```

## Lifecycle changes

### Old

```python
await client.connect()
client.start_listening()
await client.wait_for_initial_sync()
...
await client.stop_listening()
await client.disconnect()
```

### New

```python
await client.start()
await client.wait_synced()
...
await client.stop()
```

## State access

### Old

```python
client.volume
client.source
client.preset
```

### New

```python
client.state.volume
client.state.source
client.state.preset
```

## Source-by-name behavior

`source_set_by_name()` now raises `ValueError` when the name does not exist (no silent no-op).

## Optional command acknowledgements

Use `client.command(..., wait_for_ack=True)` when you need explicit confirmation.

- Returns `OKMessage` on success
- Raises `CommandRejectedError` on protocol error
- Raises `asyncio.TimeoutError` on ack timeout

## Callback behavior

Callback exceptions are now isolated and logged. A failing callback no longer kills the listen loop.

## Reconnect behavior

Reconnect now uses capped exponential backoff with optional jitter.

## Suggested HA migration checklist

1. Replace import path and class name.
2. Move lifecycle calls to `start()/wait_synced()/stop()`.
3. Update state reads to `client.state.*`.
4. Handle `ValueError` from `source_set_by_name()`.
5. Optionally use ACK waiting for critical commands.
