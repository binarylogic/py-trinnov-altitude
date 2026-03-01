# Changelog

## [4.0.0](https://github.com/binarylogic/py-trinnov-altitude/compare/v3.2.0...v4.0.0) (2026-03-01)


### ⚠ BREAKING CHANGES

* add strict protocol surface and HA adapter/bridge APIs

### Features

* add strict protocol surface and HA adapter/bridge APIs ([f790a62](https://github.com/binarylogic/py-trinnov-altitude/commit/f790a62855e0153879bff91562d7861d185d1122))
* formalize protocol layering and observability ([d092fda](https://github.com/binarylogic/py-trinnov-altitude/commit/d092fdacd476d054e9d08f108e430c83bc28fe8a))


### Bug Fixes

* allow sync without catalog clear messages ([51bb39d](https://github.com/binarylogic/py-trinnov-altitude/commit/51bb39dfb0f79227a51ca8e35217a02c2dcb6d8d))
* format canonical event definitions ([baef0ca](https://github.com/binarylogic/py-trinnov-altitude/commit/baef0ca694fbf923526281b3cd20501656d41a33))
* handle Altitude CI startup source/preset state ([6c5fb64](https://github.com/binarylogic/py-trinnov-altitude/commit/6c5fb64e9cf2c2d5dca21727998fd309c2e15d21))
* harden source index parsing and label quality precedence ([592c62f](https://github.com/binarylogic/py-trinnov-altitude/commit/592c62f57f254e79e06ea734617e6de6c4d81adb))
* normalize protocol semantics with altitude_ci quirk profile ([14de9cf](https://github.com/binarylogic/py-trinnov-altitude/commit/14de9cfc0058f4372a01cfbd87e03f871680ea7e))
* parse optsource variants with and without trailing OK ([db06676](https://github.com/binarylogic/py-trinnov-altitude/commit/db066769b77d7ed6749e3ee1e4b6068af9402872))
* support Altitude CI profile index startup payloads ([92d067a](https://github.com/binarylogic/py-trinnov-altitude/commit/92d067a543553e3835412eab4942b6d867230084))


### Documentation

* add AGENTS guidance for release and protocol workflow ([59e8e26](https://github.com/binarylogic/py-trinnov-altitude/commit/59e8e26ac2c501c31f192bbb4e898fbf2e8c56de))

## [3.2.0](https://github.com/binarylogic/py-trinnov-altitude/compare/v3.1.3...v3.2.0) (2026-03-01)


### Features

* formalize protocol layering and observability ([d092fda](https://github.com/binarylogic/py-trinnov-altitude/commit/d092fdacd476d054e9d08f108e430c83bc28fe8a))


### Bug Fixes

* harden source index parsing and label quality precedence ([592c62f](https://github.com/binarylogic/py-trinnov-altitude/commit/592c62f57f254e79e06ea734617e6de6c4d81adb))

## [3.1.3](https://github.com/binarylogic/py-trinnov-altitude/compare/v3.1.2...v3.1.3) (2026-02-28)


### Bug Fixes

* format canonical event definitions ([baef0ca](https://github.com/binarylogic/py-trinnov-altitude/commit/baef0ca694fbf923526281b3cd20501656d41a33))
* normalize protocol semantics with altitude_ci quirk profile ([14de9cf](https://github.com/binarylogic/py-trinnov-altitude/commit/14de9cfc0058f4372a01cfbd87e03f871680ea7e))


### Documentation

* add AGENTS guidance for release and protocol workflow ([59e8e26](https://github.com/binarylogic/py-trinnov-altitude/commit/59e8e26ac2c501c31f192bbb4e898fbf2e8c56de))

## [3.1.2](https://github.com/binarylogic/py-trinnov-altitude/compare/v3.1.1...v3.1.2) (2026-02-28)


### Bug Fixes

* parse optsource variants with and without trailing OK ([db06676](https://github.com/binarylogic/py-trinnov-altitude/commit/db066769b77d7ed6749e3ee1e4b6068af9402872))

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
