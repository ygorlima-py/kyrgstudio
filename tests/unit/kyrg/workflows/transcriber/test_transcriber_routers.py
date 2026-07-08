"""Unit tests for the transcriber workflow routers."""

from typing import Any, cast

import pytest

from kyrg.workflows.transcriber.nodes import primary_router, secondary_router
from kyrg.workflows.transcriber.state import TranscriberState


def _state(**values: object) -> TranscriberState:
    """Build a partial state for isolated router tests."""
    return cast(TranscriberState, values)


def test_primary_router_routes_audio_to_normalization() -> None:
    """Route audio sources to audio normalization."""
    assert primary_router(_state(source_type="audio")) == "normalize_audio"


def test_primary_router_routes_video_to_extraction() -> None:
    """Route video sources to audio extraction."""
    assert primary_router(_state(source_type="video")) == "extract_audio"


@pytest.mark.parametrize(
    "state",
    [
        pytest.param(_state(), id="missing"),
        pytest.param(_state(source_type=None), id="none"),
        pytest.param(_state(source_type=""), id="empty"),
        pytest.param(_state(source_type="document"), id="invalid"),
    ],
)
def test_primary_router_defaults_to_extraction(
    state: TranscriberState,
) -> None:
    """Route absent or unsupported source types to audio extraction."""
    assert primary_router(state) == "extract_audio"


def test_primary_router_literal_is_not_validated_at_runtime() -> None:
    """Show that a TypedDict Literal does not enforce runtime validation."""
    state_factory = cast(Any, TranscriberState)
    state = cast(TranscriberState, state_factory(source_type="document"))

    assert state["source_type"] == "document"
    assert primary_router(state) == "extract_audio"


@pytest.mark.parametrize(
    "duration",
    [
        pytest.param(179.99, id="below-limit"),
        pytest.param(180, id="inclusive-limit"),
    ],
)
def test_secondary_router_routes_eligible_audio_to_correction(
    duration: float,
) -> None:
    """Route truthy correction requests at or below the limit."""
    state = _state(
        audio_duration_in_seconds=duration,
        need_correction=True,
    )

    assert secondary_router(state) == "to_correction"


@pytest.mark.parametrize(
    "need_correction",
    [
        pytest.param(True, id="true"),
        pytest.param(False, id="false"),
        pytest.param("requested", id="truthy-non-boolean"),
    ],
)
def test_secondary_router_rejects_duration_above_limit(
    need_correction: object,
) -> None:
    """Skip correction above the duration limit regardless of the flag."""
    state = _state(
        audio_duration_in_seconds=180.01,
        need_correction=need_correction,
    )

    assert secondary_router(state) == "not_correction"


@pytest.mark.parametrize(
    "state",
    [
        pytest.param(
            _state(audio_duration_in_seconds=120),
            id="missing",
        ),
        pytest.param(
            _state(audio_duration_in_seconds=120, need_correction=None),
            id="none",
        ),
        pytest.param(
            _state(audio_duration_in_seconds=120, need_correction=False),
            id="false",
        ),
        pytest.param(
            _state(audio_duration_in_seconds=120, need_correction=0),
            id="zero",
        ),
        pytest.param(
            _state(audio_duration_in_seconds=120, need_correction=""),
            id="empty-string",
        ),
    ],
)
def test_secondary_router_skips_correction_for_falsy_flags(
    state: TranscriberState,
) -> None:
    """Skip correction when the request flag is absent or falsy."""
    assert secondary_router(state) == "not_correction"


@pytest.mark.parametrize(
    "need_correction",
    [
        pytest.param(1, id="nonzero-integer"),
        pytest.param("requested", id="nonempty-string"),
        pytest.param(["requested"], id="nonempty-list"),
    ],
)
def test_secondary_router_accepts_truthy_non_boolean_flags(
    need_correction: object,
) -> None:
    """Treat non-boolean truthy values as correction requests."""
    state = _state(
        audio_duration_in_seconds=120,
        need_correction=need_correction,
    )

    assert secondary_router(state) == "to_correction"


def test_secondary_router_accepts_negative_duration() -> None:
    """Route negative durations to correction when requested."""
    state = _state(
        audio_duration_in_seconds=-1,
        need_correction=True,
    )

    assert secondary_router(state) == "to_correction"


def test_secondary_router_skips_correction_for_nan_duration() -> None:
    """Skip correction because NaN fails the duration comparison."""
    state = _state(
        audio_duration_in_seconds=float("nan"),
        need_correction=True,
    )

    assert secondary_router(state) == "not_correction"


@pytest.mark.parametrize(
    ("duration", "expected_route"),
    [
        pytest.param(float("inf"), "not_correction", id="positive"),
        pytest.param(float("-inf"), "to_correction", id="negative"),
    ],
)
def test_secondary_router_uses_native_infinity_comparison(
    duration: float,
    expected_route: str,
) -> None:
    """Route positive and negative infinity using float comparison rules."""
    state = _state(
        audio_duration_in_seconds=duration,
        need_correction=True,
    )

    assert secondary_router(state) == expected_route


@pytest.mark.parametrize(
    "state",
    [
        pytest.param(_state(need_correction=True), id="missing"),
        pytest.param(
            _state(audio_duration_in_seconds=None, need_correction=True),
            id="none",
        ),
    ],
)
def test_secondary_router_raises_for_unavailable_duration(
    state: TranscriberState,
) -> None:
    """Raise RuntimeError when the audio duration is unavailable."""
    with pytest.raises(RuntimeError, match="Failed measure audio in seconds"):
        secondary_router(state)


def test_secondary_router_propagates_incompatible_duration_type() -> None:
    """Propagate TypeError for a duration that cannot be compared to int."""
    state = _state(
        audio_duration_in_seconds="120",
        need_correction=True,
    )

    with pytest.raises(TypeError):
        secondary_router(state)
