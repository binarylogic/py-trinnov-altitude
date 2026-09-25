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

## Normalization and diagnostics contract

- Match ASCII message keywords case-insensitively; do not lowercase entire lines.
- Preserve labels, unknown payloads, and raw unknown messages. Strip only transport line endings.
- Normalize known enum spellings in the normalizer; adapters reuse that function.
- A recognized firmware variant produces canonical events even if its raw message is unclassified.
- `AltitudeState.apply()` returns the canonical events it applied. The client records an unknown
  raw message only when normalization produced no events; it does not duplicate quirk rules.
- A configured selector and the currently active decoder remain distinct state fields.

## Command policy

Use the command completion table in README.md when adding an operation. State-confirming
commands share one deadline-bounded polling implementation. Repeating the setting itself
is a separate, explicit device behavior; never infer retry safety from a method's name.
Keep response fixtures for known firmware shapes, and exercise delayed state, unrelated
pushes, unknown values, cancellation, and stalled query I/O. Do not reinterpret an
unfamiliar payload merely to make a confirmation test pass.
