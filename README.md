# Trinnov Altitude Python Library

[![CI](https://github.com/binarylogic/py-trinnov-altitude/actions/workflows/test.yml/badge.svg)](https://github.com/binarylogic/py-trinnov-altitude/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/trinnov-altitude)](https://pypi.org/project/trinnov-altitude/)
[![Python Version](https://img.shields.io/pypi/pyversions/trinnov-altitude)](https://pypi.org/project/trinnov-altitude/)
[![License](https://img.shields.io/github/license/binarylogic/py-trinnov-altitude)](https://github.com/binarylogic/py-trinnov-altitude/blob/master/LICENSE)

A modern Python library for interacting with the [Trinnov Altitude processor](https://www.trinnov.com/en/products/altitude32/) via the [TCP/IP automation protocol](docs/Alititude%20Protocol.pdf). Initially built for the [Trinnov Altitude Home Assistant integration](https://github.com/binarylogic/trinnov-altitude-homeassistant).

## Features

- **Async/await support** - Built on asyncio for non-blocking I/O
- **Real-time state synchronization** - Bidirectional communication with automatic state updates
- **Type hints** - Full type annotation support for better IDE integration
- **Comprehensive API** - Control volume, sources, presets, and audio processing settings
- **Automatic reconnection** - Handles connection drops gracefully
- **Wake-on-LAN** - Power on your processor remotely

## Installation

```bash
pip install trinnov-altitude
```

## Quick Start

```python
import asyncio
from trinnov_altitude.trinnov_altitude import TrinnovAltitude

async def main():
    # Create client instance
    altitude = TrinnovAltitude(host="192.168.1.90")
    
    try:
        # Connect to processor
        await altitude.connect()
        
        # Start listening for updates
        altitude.start_listening()
        
        # Wait for initial state sync
        await altitude.wait_for_initial_sync()
        
        # Control the processor
        await altitude.volume_set(-30.0)
        await altitude.mute_on()
        
        print(f"Current volume: {altitude.volume} dB")
        print(f"Current source: {altitude.source}")
        
    finally:
        await altitude.disconnect()

asyncio.run(main())
```

## Usage

### Connecting to the Processor

The Trinnov Altitude must be powered on before you can connect. If you have Wake-on-LAN enabled, you can power it on programmatically:

```python
from trinnov_altitude.trinnov_altitude import TrinnovAltitude

altitude = TrinnovAltitude(
    host="192.168.1.90",
    mac="c8:7f:54:2d:ce:f2"  # Required for Wake-on-LAN
)

# Power on via Wake-on-LAN
altitude.power_on()

# Wait a moment for the processor to boot
await asyncio.sleep(30)

# Connect
await altitude.connect()
```

### Handling State Updates

The processor broadcasts state changes to all connected clients. Register a callback to react to updates:

```python
def on_update(event: str, message):
    if event == "received_message":
        print(f"Update received: {message}")
    elif event == "connected":
        print("Connected to processor")
    elif event == "disconnected":
        print("Disconnected from processor")

altitude.register_callback(on_update)
altitude.start_listening()
```

### Available State

After connecting and calling `start_listening()`, the following state attributes are automatically synchronized:

| Attribute | Type | Description |
|-----------|------|-------------|
| `altitude.audiosync` | `str \| None` | Current audio sync mode |
| `altitude.bypass` | `bool \| None` | Bypass state |
| `altitude.decoder` | `str \| None` | Active decoder |
| `altitude.dim` | `bool \| None` | Dim state |
| `altitude.id` | `str \| None` | Processor unique ID |
| `altitude.mute` | `bool \| None` | Mute state |
| `altitude.preset` | `str \| None` | Current preset name |
| `altitude.presets` | `dict[int, str]` | Available presets |
| `altitude.sampling_rate` | `int \| None` | Current sampling rate |
| `altitude.source` | `str \| None` | Current source name |
| `altitude.source_format` | `str \| None` | Source format |
| `altitude.sources` | `dict[int, str]` | Available sources |
| `altitude.upmixer` | `str \| None` | Active upmixer |
| `altitude.version` | `str \| None` | Firmware version |
| `altitude.volume` | `float \| None` | Volume level in dB |

## API Reference

### Volume Control

```python
await altitude.volume_set(-30.0)              # Set absolute volume in dB
await altitude.volume_adjust(2.5)             # Adjust by relative amount
await altitude.volume_up()                    # Increase by 0.5 dB
await altitude.volume_down()                  # Decrease by 0.5 dB
await altitude.volume_ramp(-25.0, 2000)       # Ramp to volume over 2000ms
await altitude.volume_percentage_set(75.0)    # Set volume by percentage
```

### Mute Control

```python
await altitude.mute_on()
await altitude.mute_off()
await altitude.mute_set(True)
await altitude.mute_toggle()
```

### Source Selection

```python
await altitude.source_set(0)                  # Set source by index
await altitude.source_set_by_name("Apple TV") # Set source by name
await altitude.source_get()                   # Request current source
```

### Presets

```python
await altitude.preset_set(1)                  # Set preset by index
await altitude.preset_get()                   # Request current preset
```

### Audio Processing

```python
# Bypass
await altitude.bypass_on()
await altitude.bypass_off()
await altitude.bypass_toggle()

# Acoustic correction
await altitude.acoustic_correction_on()
await altitude.acoustic_correction_off()

# Time alignment
await altitude.time_alignment_on()
await altitude.time_alignment_off()

# Level alignment
await altitude.level_alignment_on()
await altitude.level_alignment_off()

# Upmixer
from trinnov_altitude.const import UpmixerMode
await altitude.upmixer_set(UpmixerMode.MODE_AURO3D)

# Remapping mode
from trinnov_altitude.const import RemappingMode
await altitude.remapping_mode_set(RemappingMode.MODE_3D)
```

### Display & UI

```python
# Dim
await altitude.dim_on()
await altitude.dim_off()

# Front display
await altitude.front_display_on()
await altitude.front_display_off()

# Page navigation
await altitude.page_up()
await altitude.page_down()
await altitude.page_adjust(2)  # Move 2 pages
```

### Power Control

```python
altitude.power_on()                # Wake-on-LAN (requires MAC address)
await altitude.power_off()         # Power off processor
```

For a complete list of methods, see the [`TrinnovAltitude` class](trinnov_altitude/trinnov_altitude.py).

## Development

This project uses modern Python tooling:

- **[uv](https://github.com/astral-sh/uv)** - Fast Python package installer
- **[ruff](https://github.com/astral-sh/ruff)** - Fast Python linter and formatter
- **[task](https://taskfile.dev)** - Task runner for development workflows

### Setup

```bash
# Clone the repository
git clone https://github.com/binarylogic/py-trinnov-altitude.git
cd py-trinnov-altitude

# Install task (macOS)
brew install go-task/tap/go-task

# Setup development environment
task dev
```

### Available Tasks

```bash
task install      # Install dependencies
task test         # Run tests
task lint         # Run linting
task lint:fix     # Run linting with auto-fix
task format       # Format code
task format:check # Check code formatting
task check        # Run all checks (lint + format + test)
task build        # Build package
task clean        # Clean build artifacts
```

### Running Tests

```bash
# Run all tests
task test

# Or use pytest directly
pytest -v
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Related Projects

- [Trinnov Altitude Home Assistant Integration](https://github.com/binarylogic/trinnov-altitude-homeassistant) - Home Assistant integration using this library

## Acknowledgments

- [Trinnov Audio](https://www.trinnov.com/) for the Altitude processor and protocol documentation
