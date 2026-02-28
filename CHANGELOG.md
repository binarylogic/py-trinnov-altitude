# Changelog

## [3.1.1](https://github.com/binarylogic/py-trinnov-altitude/compare/v3.1.0...v3.1.1) (2026-02-28)

### Fixed

- parse Altitude CI index-only source updates (`PROFILE -1`) as current source state
- preserve negative current preset indices from protocol (`CURRENT_PRESET -1`)
- bootstrap with `get_current_state` to populate catalogs deterministically on startup

## [3.1.0](https://github.com/binarylogic/py-trinnov-altitude/compare/v3.0.0...v3.1.0) (2026-02-27)

### Features

- add `command_bridge` helpers for Home Assistant command parsing, normalization, and enum coercion

## [3.0.0](https://github.com/binarylogic/py-trinnov-altitude/compare/v2.0.1...v3.0.0) (2026-02-27)


### ⚠ BREAKING CHANGES

* add strict protocol surface and HA adapter/bridge APIs

### Features

* add strict protocol surface and HA adapter/bridge APIs ([f790a62](https://github.com/binarylogic/py-trinnov-altitude/commit/f790a62855e0153879bff91562d7861d185d1122))

## 2.0.1 - 2026-02-27

### Fixed

- Allow initial sync when devices emit current preset/source indices without full catalog clear messages (Altitude CI compatibility).
- Add regression coverage for Altitude CI-style startup streams.

## 2.0.0 - 2026-02-27

### Breaking

- Removed compatibility modules and legacy imports (`trinnov_altitude.trinnov_altitude`, `trinnov_altitude.messages`).
- Replaced old connection/listening lifecycle with `start()`, `wait_synced()`, and `stop()`.
- Moved runtime values under `client.state`.
- `source_set_by_name()` now raises `ValueError` when source is unknown.

### Added

- New layered architecture: protocol parser, transport, state model, client orchestrator.
- Deterministic reconnect loop with capped exponential backoff and jitter.
- Optional command ACK flow (`client.command(..., wait_for_ack=True)`).
- Callback exception isolation.
- New deterministic test suite for lifecycle, reconnect, ack, and parser behavior.

### Changed

- Removed import-time logging side effects.
- Updated documentation and added migration guide.
- Modernized tooling to `pyproject.toml` + `uv` + `hatchling` (removed `setup.py`, `setup.cfg`, `requirements-dev.txt`, `ruff.toml`).
