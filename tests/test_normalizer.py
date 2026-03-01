from trinnov_altitude.canonical import (
    SOURCE_LABEL_QUALITY_OPTSOURCE,
    SOURCE_LABEL_QUALITY_PROFILE,
    SetCurrentPresetEvent,
    SetCurrentSourceEvent,
    SetFeaturesEvent,
    UpsertSourceEvent,
)
from trinnov_altitude.normalizer import PROFILE_ALTITUDE_CI, PROFILE_DEFAULT, normalize_message, select_profile
from trinnov_altitude.protocol import IdentsMessage, MetaPresetLoadedMessage, SourceMessage


def test_select_profile_uses_altitude_ci_feature():
    assert select_profile(["with_tsf", "altitude_ci"]) == PROFILE_ALTITUDE_CI
    assert select_profile(["with_tsf"]) == PROFILE_DEFAULT


def test_meta_preset_loaded_normalizes_to_preset_for_default_profile():
    events = normalize_message(MetaPresetLoadedMessage(index=2), PROFILE_DEFAULT)
    assert events == [SetCurrentPresetEvent(index=2)]


def test_meta_preset_loaded_normalizes_to_source_for_altitude_ci_profile():
    events = normalize_message(MetaPresetLoadedMessage(index=2), PROFILE_ALTITUDE_CI)
    assert events == [SetCurrentSourceEvent(index=2)]


def test_idents_normalization_emits_feature_event():
    events = normalize_message(IdentsMessage(features=("with_tsf", "altitude_ci")), PROFILE_DEFAULT)
    assert events == [SetFeaturesEvent(features=("with_tsf", "altitude_ci"))]


def test_source_from_profile_uses_high_quality():
    events = normalize_message(SourceMessage(index=0, name="AppleTV", origin="profile"), PROFILE_DEFAULT)
    assert events == [UpsertSourceEvent(index=0, name="AppleTV", quality=SOURCE_LABEL_QUALITY_PROFILE)]


def test_source_from_optsource_uses_lower_quality():
    events = normalize_message(SourceMessage(index=0, name="Source 1", origin="optsource"), PROFILE_DEFAULT)
    assert events == [UpsertSourceEvent(index=0, name="Source 1", quality=SOURCE_LABEL_QUALITY_OPTSOURCE)]
