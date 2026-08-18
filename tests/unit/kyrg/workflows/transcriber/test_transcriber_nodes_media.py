"""Unit tests for media-related transcriber workflow nodes."""

import math
from types import SimpleNamespace
from typing import NamedTuple, cast
from unittest.mock import MagicMock

import pytest

from kyrg.workflows.transcriber import nodes
from kyrg.workflows.transcriber.state import TranscriberState


class MediaDoubles(NamedTuple):
    """Store patched media collaborators and the action instance."""

    context_type: MagicMock
    runner_type: MagicMock
    action_type: MagicMock
    action: MagicMock


def _state(**values: object) -> TranscriberState:
    """Build a partial state for an isolated node test."""
    return cast(TranscriberState, values)


def _install_media_doubles(
    monkeypatch: pytest.MonkeyPatch,
    action_name: str,
) -> MediaDoubles:
    """Patch media collaborators in the namespace used by the nodes."""
    context_type = MagicMock(name="MediaContext")
    runner_type = MagicMock(name="CommandRunner")
    action_type = MagicMock(name=action_name)
    action = action_type.return_value

    monkeypatch.setattr(nodes, "MediaContext", context_type)
    monkeypatch.setattr(nodes, "CommandRunner", runner_type)
    monkeypatch.setattr(nodes, action_name, action_type)

    return MediaDoubles(
        context_type=context_type,
        runner_type=runner_type,
        action_type=action_type,
        action=action,
    )


def test_prepare_audio_executes_conversion_with_exact_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Convert exact input and output paths with a new command runner."""
    doubles = _install_media_doubles(monkeypatch, "ConvertAudio")
    ignored_conversion_result = object()
    doubles.action.execute.return_value = ignored_conversion_result
    state = _state(
        source_path="incoming/source.wav",
        audio_path="working/normalized.mp3",
    )

    result = nodes.prepare_audio(state)

    doubles.context_type.assert_called_once_with(
        input_path="incoming/source.wav",
        output_path="working/normalized.mp3",
    )
    doubles.runner_type.assert_called_once_with()
    doubles.action_type.assert_called_once_with(
        context=doubles.context_type.return_value,
        runner=doubles.runner_type.return_value,
        codec="libmp3lame",
        bitrate="64k",
        sample_rate=16000,
        channels=1,
    )
    doubles.action.execute.assert_called_once_with()
    assert result == {"audio_path": "working/normalized.mp3"}


@pytest.mark.parametrize(
    ("state", "missing_key"),
    [
        pytest.param(_state(audio_path="audio.wav"), "source_path", id="source"),
        pytest.param(_state(source_path="source.wav"), "audio_path", id="audio"),
    ],
)
def test_prepare_audio_propagates_missing_state_key(
    state: TranscriberState,
    missing_key: str,
) -> None:
    """Propagate KeyError when a required path is absent."""
    with pytest.raises(KeyError) as exc_info:
        nodes.prepare_audio(state)

    assert exc_info.value.args == (missing_key,)


def test_prepare_audio_propagates_conversion_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Propagate an external conversion error without translation."""
    doubles = _install_media_doubles(monkeypatch, "ConvertAudio")
    error = OSError("conversion failed")
    doubles.action.execute.side_effect = error
    state = _state(source_path="source.wav", audio_path="audio.mp3")

    with pytest.raises(OSError) as exc_info:
        nodes.prepare_audio(state)

    assert exc_info.value is error
    doubles.action.execute.assert_called_once_with()


def test_extract_audio_executes_extraction_with_exact_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Extract between exact paths with a new command runner."""
    doubles = _install_media_doubles(monkeypatch, "ConvertAudio")
    ignored_extraction_result = object()
    doubles.action.execute.return_value = ignored_extraction_result
    state = _state(
        source_path="incoming/source.mp4",
        audio_path="working/extracted.mp3",
    )

    result = nodes.extract_audio(state)

    doubles.context_type.assert_called_once_with(
        input_path="incoming/source.mp4",
        output_path="working/extracted.mp3",
    )
    doubles.runner_type.assert_called_once_with()
    doubles.action_type.assert_called_once_with(
        context=doubles.context_type.return_value,
        runner=doubles.runner_type.return_value,
        codec="libmp3lame",
        bitrate="64k",
        sample_rate=16000,
        channels=1,
    )
    doubles.action.execute.assert_called_once_with()
    assert result == {"audio_path": "working/extracted.mp3"}


@pytest.mark.parametrize(
    ("state", "missing_key"),
    [
        pytest.param(_state(audio_path="audio.wav"), "source_path", id="source"),
        pytest.param(_state(source_path="source.mp4"), "audio_path", id="audio"),
    ],
)
def test_extract_audio_propagates_missing_state_key(
    state: TranscriberState,
    missing_key: str,
) -> None:
    """Propagate KeyError when an extraction path is absent."""
    with pytest.raises(KeyError) as exc_info:
        nodes.extract_audio(state)

    assert exc_info.value.args == (missing_key,)


def test_extract_audio_propagates_failure_without_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Propagate an extraction error without translation or cleanup."""
    doubles = _install_media_doubles(monkeypatch, "ConvertAudio")
    error = RuntimeError("extraction failed")
    doubles.action.execute.side_effect = error
    doubles.action.cleanup = MagicMock(name="cleanup")
    state = _state(source_path="source.mp4", audio_path="audio.mp3")

    with pytest.raises(RuntimeError) as exc_info:
        nodes.extract_audio(state)

    assert exc_info.value is error
    doubles.action.execute.assert_called_once_with()
    doubles.action.cleanup.assert_not_called()


def test_measure_audio_builds_action_and_parses_whitespace_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Measure exact paths and parse whitespace-padded duration bytes."""
    doubles = _install_media_doubles(monkeypatch, "AudioSize")
    doubles.action.execute.return_value = SimpleNamespace(stdout=b" 180.0\n")
    state = _state(source_path="source.mp4", audio_path="audio.wav")
    original_state = dict(state)

    result = nodes.measure_audio(state)

    doubles.context_type.assert_called_once_with(
        input_path="source.mp4",
        output_path="audio.wav",
    )
    doubles.runner_type.assert_called_once_with()
    doubles.action_type.assert_called_once_with(
        context=doubles.context_type.return_value,
        runner=doubles.runner_type.return_value,
    )
    doubles.action.execute.assert_called_once_with()
    assert result == {"audio_duration_in_seconds": 180.0}
    assert state == original_state


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        pytest.param(b"0", 0.0, id="zero"),
        pytest.param(b"-12.5", -12.5, id="negative"),
        pytest.param(b"nan", float("nan"), id="nan"),
        pytest.param(b"inf", float("inf"), id="positive-infinity"),
        pytest.param(b"-inf", float("-inf"), id="negative-infinity"),
    ],
)
def test_measure_audio_uses_direct_float_conversion(
    monkeypatch: pytest.MonkeyPatch,
    stdout: bytes,
    expected: float,
) -> None:
    """Accept every special numeric value supported by float conversion."""
    doubles = _install_media_doubles(monkeypatch, "AudioSize")
    doubles.action.execute.return_value = SimpleNamespace(stdout=stdout)
    state = _state(source_path="source.mp4", audio_path="audio.wav")

    result = nodes.measure_audio(state)
    duration = result["audio_duration_in_seconds"]

    if math.isnan(expected):
        assert math.isnan(duration)
    else:
        assert duration == expected


@pytest.mark.parametrize(
    "stdout",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"not-a-number", id="non-numeric"),
    ],
)
def test_measure_audio_propagates_invalid_float_value(
    monkeypatch: pytest.MonkeyPatch,
    stdout: bytes,
) -> None:
    """Propagate ValueError for bytes that do not contain a float."""
    doubles = _install_media_doubles(monkeypatch, "AudioSize")
    doubles.action.execute.return_value = SimpleNamespace(stdout=stdout)
    state = _state(source_path="source.mp4", audio_path="audio.wav")

    with pytest.raises(ValueError):
        nodes.measure_audio(state)


def test_measure_audio_propagates_incompatible_stdout_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Propagate an error when stdout has no compatible decode method."""
    doubles = _install_media_doubles(monkeypatch, "AudioSize")
    doubles.action.execute.return_value = SimpleNamespace(stdout=object())
    state = _state(source_path="source.mp4", audio_path="audio.wav")

    with pytest.raises(AttributeError):
        nodes.measure_audio(state)
