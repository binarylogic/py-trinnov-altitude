# Protocol Architecture

This library uses a strict 4-layer flow:

1. Parser (`protocol.py`)
- Converts text lines into typed raw messages.
- Preserves source message origin when semantics differ (for example `PROFILE` vs `OPTSOURCE`).

2. Normalizer (`normalizer.py`)
- Converts raw messages into canonical events.
- Applies firmware/profile quirks in one place.
- Assigns data quality for competing inputs.

3. Reducer (`state.py`)
- Applies canonical events to runtime state.
- Resolves conflicts with explicit precedence rules.
- Never reads raw wire strings directly.

4. Adapter (`adapter.py`, `ha_bridge.py`)
- Projects reducer state into integration-facing payloads/events.
- Must not implement protocol quirks.

## Guardrails

- Add protocol quirks only in normalizer/profile selection.
- Add label/source precedence only in canonical event metadata + reducer.
- Keep Home Assistant and command bridge projection-only.
- Track parser drift via unknown-message counters exposed by client state.

## Non-Goals

- No plugin framework.
- No per-entity protocol hacks.
- No cross-layer backreferences.
