# Trinnov Altitude Python Library

A Python library for interacting with the [Trinnov Altitude processor](https://www.trinnov.com/en/products/altitude32/) via the
[TCP/IP automation protocol](docs/Alititude%20Protocol.pdf) provided by the Trinnov Altitude.

## Overview

The Trinnov Altitude processor is an audio/video processor that exposes an
automation protocol over TCP/IP for remote control.

The interface is a two-way communication protocol. At any time the processor
can broadcast messages to all connected clients reflecting the current
processor state. For example, the user could turn the volume knob on the
processor itself, which would broadcase volume change messages to all connected
clients.

Therefore, it's important to architect usage of this library to handle state
changes asynchronously. You should not be polling the processor for state
changes. Instead, you should register a callback that fires when changes are
received.

## Installation

```
pip install trinnov-altitude
```

## Setup

### Power on

Powers the processor on via Wake on Lan. The process must be powered on
before you can connect.

```python
from trinnov_altitude.trinnov_altitude import TrinnovAltitude

altitude = TrinnovAltitude(host = "192.168.1.90", mac = "c8:7f:54:2d:ce:f2")
await altitude.power_on()
```

### Connect

Connect to the processor via TCP/IP. Note that you must power on the device
before connecting. The Trinnov Altitude does not have a standby mode that will
accept connections.

```python
from trinnov_altitude.trinnov_altitude import TrinnovAltitude

altitude = TrinnovAltitude(host = "192.168.1.90")

try:
    await altitude.connect()
finally:
    # Always disconnect and cleanup
    await altitude.disconnect()
```

### Listen for updates

The processor will broadcast state changes to all connected clients. You must
explicitly start listening to receive the messages and sync the internal state
of your object.

```python
from trinnov_altitude.trinnov_altitude import TrinnovAltitude

altitude = TrinnovAltitude(host = "192.168.1.90")

# Optionally define a callback to be fired on each individual update
def callback(message):
    # react to the change here
    pass

# Start listening for updates in an async.io Task
altitude.start_listening(callback: callback)
```

## State

State will be available shortly after connecting. When a client connects to the
processor, it will send a list of messages reflecting the current state. The
`start_listening` method will receive these updates in the background and sync
your object with the processor's state.

```python
altitude.audiosync: bool | None # Current state of audiosync
altitude.bypass: bool | None = None # Current state of bypass
altitude.dim: bool | None = None # Current state of dim
altitude.id: str | None = None # Unique ID of the processor
altitude.mute: bool | None = None # Current state of mute
altitude.presets: dict = {} # Dictionary of all presets and their names
altitude.source: str | None = None # Current source
altitude.sources: dict = {} # Dictionary of all sources and their names
altitude.version: str | None = None # Software version of the processor
altitude.volume: float | None = None # Current volume level in dB
```

## Commands

All commands assume you have [setup](#setup) your Trinnov Altitude client.

For a full list of commands, see the [`TrinnovAltitude` class](trinnov_altitude/trinnov_altitude.py),

### Acoustic Correction

```python
await altitude.acoustic_correction_off()
await altitude.acoustic_correction_on()
await altitude.acoustic_correction_set(state: bool)
await altitude.acoustic_correction_toggle()
```

### Bypass

```python
await altitude.bypass_off()
await altitude.bypass_on()
await altitude.bypass_set(state: bool)
await altitude.bypass_toggle()
```

### Dim

```python
await altitude.dim_off()
await altitude.dim_on()
await altitude.dim_set(state: bool)
await altitude.dim_toggle()
```

### Front display

```python
await altitude.dim_off()
await altitude.dim_on()
await altitude.dim_set(state: bool)
await altitude.dim_toggle()
```

### Level alignment

```python
await altitude.level_alignment_off()
await altitude.level_alignment_on()
await altitude.level_alignment_set(state: bool)
await altitude.level_alignment_toggle()
```

### Mute

```python
await altitude.mute_off()
await altitude.mute_on()
await altitude.mute_set(state: bool)
await altitude.mute_toggle()
```

### Page adjust

```python
await altitude.page_adjust(delta: int)
await altitude.page_down()
await altitude.page_up()
```

### Power

```python
altitude.power_on()
await altitude.power_off()
```

### Presets

```python
await altitude.preset_load(id: int)
```

### Quick optimized

```python
await altitude.quick_optimized_off()
await altitude.quick_optimized_on()
await altitude.quick_optimized_set(state: bool)
await altitude.quick_optimized_toggle()
```

### Remapping mode

```python
await altitude.remapping_mode_set(mode: const.RemappingMode)
```

### Sources

```python
await altitude.source_set(id: int)
```

### Time alignment

```python
await altitude.time_alignment_off()
await altitude.time_alignment_on()
await altitude.time_alignment_set(state: bool)
await altitude.time_alignment_toggle()
```

### Upmixer

```python
await altitude.source_set(mode: const.UpmixerMode)
```

### Volume

```python
await altitude.volume_adjust(delta: int | float)
await altitude.volume_down()
await altitude.volume_set(db: int | float)
await altitude.volume_ramp(db: int | float, duration: int)
await altitude.volume_up()
```
