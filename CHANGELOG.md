# Changelog

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
