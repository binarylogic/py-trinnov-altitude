from __future__ import annotations

from dataclasses import dataclass

from trinnov_altitude.adapter import snapshot_from_state
from trinnov_altitude.protocol import parse_message
from trinnov_altitude.state import AltitudeState


@dataclass(frozen=True)
class CatalogView:
    preset: str | None
    presets: tuple[tuple[int, str], ...]
    source: str | None
    sources: tuple[tuple[int, str], ...]


def _view(state: AltitudeState) -> CatalogView:
    snapshot = snapshot_from_state(state)
    return CatalogView(
        preset=snapshot.preset,
        presets=snapshot.presets,
        source=snapshot.source,
        sources=snapshot.sources,
    )


def _apply(state: AltitudeState, *lines: str) -> list[CatalogView]:
    views: list[CatalogView] = []
    for line in lines:
        state.apply(parse_message(line))
        views.append(_view(state))
    return views


def _ready_state() -> AltitudeState:
    state = AltitudeState()
    _apply(
        state,
        "Welcome on Trinnov Optimizer (Version 4.4.3, ID 10487582)",
        "LABELS_CLEAR",
        "LABEL 0: Builtin",
        "LABEL 1: 9.1.6 Reference",
        "LABEL 2: 9.1.6 Action",
        "CURRENT_PRESET 2",
        "PROFILES_CLEAR",
        "PROFILE 0: Apple TV",
        "PROFILE 1: Kaleidescape",
        "CURRENT_PROFILE 0",
    )
    return state


def test_catalogs_are_not_published_partially_during_startup() -> None:
    state = AltitudeState()
    empty = _view(state)

    views = _apply(
        state,
        "LABELS_CLEAR",
        "LABEL 0: Builtin",
        "LABEL 1: Reference",
        "LABEL 2: Action",
    )

    assert views == [empty, empty, empty, empty]

    _apply(state, "CURRENT_PRESET 2")
    assert state.presets == {0: "Builtin", 1: "Reference", 2: "Action"}
    assert state.preset == "Action"


def test_unchanged_refresh_never_exposes_empty_or_partial_catalogs() -> None:
    state = _ready_state()
    stable = _view(state)

    views = _apply(
        state,
        "LABELS_CLEAR",
        "LABEL 0: Builtin",
        "LABEL 1: 9.1.6 Reference",
        "LABEL 2: 9.1.6 Action",
        "CURRENT_PRESET 2",
        "PROFILES_CLEAR",
        "PROFILE 0: Apple TV",
        "PROFILE 1: Kaleidescape",
        "BASS_MANAGEMENT 1",
    )

    assert views == [stable] * len(views)


def test_changed_catalog_is_replaced_once_at_its_boundary() -> None:
    state = _ready_state()
    stable = _view(state)

    views = _apply(
        state,
        "LABELS_CLEAR",
        "LABEL 0: Builtin",
        "LABEL 2: Action Updated",
        "LABEL 3: Speakers Only",
        "CURRENT_PRESET 2",
    )

    assert views[:-1] == [stable] * 4
    assert views[-1] == CatalogView(
        preset="Action Updated",
        presets=((0, "Builtin"), (2, "Action Updated"), (3, "Speakers Only")),
        source="Apple TV",
        sources=((0, "Apple TV"), (1, "Kaleidescape")),
    )


def test_empty_catalog_replaces_previous_catalog_at_boundary() -> None:
    state = _ready_state()
    stable = _view(state)

    views = _apply(state, "LABELS_CLEAR", "OK")

    assert views[0] == stable
    assert views[1].preset is None
    assert views[1].presets == ()


def test_source_refresh_keeps_best_label_and_commits_atomically() -> None:
    state = _ready_state()
    stable = _view(state)

    views = _apply(
        state,
        "PROFILES_CLEAR",
        "OPTSOURCE 0 Source 1",
        "PROFILE 0: Apple TV",
        "PROFILE 1: Kaleidescape",
        "PROFILE 2: Xbox",
        "SOURCES_CHANGED",
    )

    assert views[:-1] == [stable] * 5
    assert views[-1].source == "Apple TV"
    assert views[-1].sources == ((0, "Apple TV"), (1, "Kaleidescape"), (2, "Xbox"))


def test_disconnect_discards_an_incomplete_catalog() -> None:
    state = _ready_state()
    _apply(state, "LABELS_CLEAR", "LABEL 0: Incomplete")

    state.reset_runtime_values()
    _apply(state, "LABEL 0: Fresh", "CURRENT_PRESET 0")

    assert state.presets == {0: "Fresh"}
    assert state.preset == "Fresh"
