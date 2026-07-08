"""Unit tests for transcriber context extraction and correction nodes."""

from types import SimpleNamespace
from typing import NamedTuple, cast
from unittest.mock import MagicMock

import pytest

from kyrg.transcribers.schemas import (
    TextSegment,
    TranscriptionResult,
    WordSegment,
)
from kyrg.workflows.core import WorkflowRuntime
from kyrg.workflows.transcriber import nodes
from kyrg.workflows.transcriber.schemas import (
    CorrectedSegment,
    CorrectedTranscriptionOutput,
    DomainContextOutput,
)
from kyrg.workflows.transcriber.state import TranscriberState


class ActionDoubles(NamedTuple):
    """Store a patched action class, instance, and executor class."""

    action_type: MagicMock
    action: MagicMock
    executor_type: MagicMock


def _state(**values: object) -> TranscriberState:
    """Build a partial state for an isolated node test."""
    return cast(TranscriberState, values)


def _runtime(
    *,
    extract_context_llm: object = None,
    correction_llm: object = None,
) -> WorkflowRuntime:
    """Build the minimal runtime context consumed by correction nodes."""
    context = SimpleNamespace(
        extract_context_llm=extract_context_llm,
        correction_llm=correction_llm,
    )
    return cast(WorkflowRuntime, SimpleNamespace(context=context))


def _domain_context() -> DomainContextOutput:
    """Build deterministic domain context for node inputs and outputs."""
    return DomainContextOutput(
        language="en",
        main_subject="Deterministic testing",
        content_type="lesson",
        summary="A lesson about reliable tests.",
        important_terms=["pytest"],
        named_entities=["Kyrg"],
        technical_terms=["deep copy"],
        correction_rules=["Preserve timestamps."],
    )


def _transcription(
    segments: list[TextSegment] | None = None,
) -> TranscriptionResult:
    """Build a transcription with representative nested metadata."""
    if segments is None:
        segments = [
            TextSegment(
                id=10,
                start=0.0,
                end=1.5,
                text="The unedited opening.",
                words=[
                    WordSegment(
                        word="unedited",
                        start=0.2,
                        end=0.8,
                        probability=0.82,
                    )
                ],
            ),
            TextSegment(
                id=20,
                start=1.5,
                end=3.0,
                text="The pytest correction.",
                words=[
                    WordSegment(
                        word="pytest",
                        start=1.8,
                        end=2.3,
                        probability=0.91,
                    )
                ],
            ),
            TextSegment(
                id=30,
                start=3.0,
                end=4.5,
                text="The untouched ending.",
            ),
        ]

    return TranscriptionResult(
        audio_path="working/audio.wav",
        language="en",
        text="Original global transcription.",
        segments=segments,
        model="test-model",
        raw_response={"request_id": "request-123", "nested": {"attempt": 1}},
        provider="fake-provider",
    )


def _tokens() -> dict[str, int]:
    """Return a complete deterministic token usage mapping."""
    return {
        "input_tokens": 11,
        "output_tokens": 7,
        "total_tokens": 18,
    }


def _install_action_doubles(
    monkeypatch: pytest.MonkeyPatch,
    action_name: str,
    *,
    output: object,
    tokens_usage: dict[str, int] | None = None,
) -> ActionDoubles:
    """Patch an action and executor in the namespace used by the nodes."""
    action_type = MagicMock(name=action_name)
    action = action_type.return_value
    action.tokens_usage = _tokens() if tokens_usage is None else tokens_usage
    executor_type = MagicMock(name="AIActionExecutor")
    executor_type.run.return_value = output

    monkeypatch.setattr(nodes, action_name, action_type)
    monkeypatch.setattr(nodes, "AIActionExecutor", executor_type)

    return ActionDoubles(action_type, action, executor_type)


def test_extract_hybrid_context_returns_context_message_and_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run context extraction once and return its exact output delta."""
    transcription = _transcription()
    domain_context = _domain_context()
    llm = object()
    doubles = _install_action_doubles(
        monkeypatch,
        "ExtractDomainContext",
        output=domain_context,
    )
    state = _state(result=transcription)

    result = nodes.extract_hybrid_context(
        state,
        _runtime(extract_context_llm=llm),
    )

    doubles.action_type.assert_called_once_with(
        llm=llm,
        result=transcription,
    )
    doubles.executor_type.run.assert_called_once_with(doubles.action)
    expected_message = nodes.TranscriptionPrompts.QUALITY_AGENT_INPUT.format(
        domain_context=domain_context.model_dump_json(indent=2),
        result=transcription.model_dump_json(indent=2),
    )
    assert result == {
        "domain_context": domain_context,
        "messages": [{"role": "user", "content": expected_message}],
        "input_tokens": 11,
        "output_tokens": 7,
        "total_tokens": 18,
    }
    assert result["domain_context"] is domain_context


def test_extract_hybrid_context_requires_runtime_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise RuntimeError before creating an action without context."""
    doubles = _install_action_doubles(
        monkeypatch,
        "ExtractDomainContext",
        output=_domain_context(),
    )
    runtime = cast(WorkflowRuntime, SimpleNamespace(context=None))

    with pytest.raises(
        RuntimeError,
        match="Transcriber workflow context is required",
    ):
        nodes.extract_hybrid_context(_state(result=_transcription()), runtime)

    doubles.action_type.assert_not_called()
    doubles.executor_type.run.assert_not_called()


@pytest.mark.parametrize(
    "state",
    [
        pytest.param(_state(), id="missing"),
        pytest.param(_state(result=None), id="none"),
    ],
)
def test_extract_hybrid_context_requires_transcription_result(
    monkeypatch: pytest.MonkeyPatch,
    state: TranscriberState,
) -> None:
    """Raise ValueError before creating an action without a result."""
    doubles = _install_action_doubles(
        monkeypatch,
        "ExtractDomainContext",
        output=_domain_context(),
    )

    with pytest.raises(
        ValueError,
        match="result is required to extract domain context",
    ):
        nodes.extract_hybrid_context(state, _runtime())

    doubles.action_type.assert_not_called()
    doubles.executor_type.run.assert_not_called()


def test_extract_hybrid_context_propagates_executor_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Propagate the exact context executor exception."""
    doubles = _install_action_doubles(
        monkeypatch,
        "ExtractDomainContext",
        output=_domain_context(),
    )
    error = RuntimeError("context extraction failed")
    doubles.executor_type.run.side_effect = error
    state = _state(result=_transcription())

    with pytest.raises(RuntimeError) as exc_info:
        nodes.extract_hybrid_context(state, _runtime())

    assert exc_info.value is error
    doubles.executor_type.run.assert_called_once_with(doubles.action)


@pytest.mark.parametrize(
    "missing_key",
    ["input_tokens", "output_tokens", "total_tokens"],
)
def test_extract_hybrid_context_propagates_incomplete_tokens(
    monkeypatch: pytest.MonkeyPatch,
    missing_key: str,
) -> None:
    """Propagate KeyError for each absent context token metric."""
    tokens = _tokens()
    del tokens[missing_key]
    doubles = _install_action_doubles(
        monkeypatch,
        "ExtractDomainContext",
        output=_domain_context(),
        tokens_usage=tokens,
    )
    state = _state(result=_transcription())

    with pytest.raises(KeyError) as exc_info:
        nodes.extract_hybrid_context(state, _runtime())

    assert exc_info.value.args == (missing_key,)
    doubles.executor_type.run.assert_called_once_with(doubles.action)


def test_correction_transcriber_requires_runtime_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise RuntimeError before correction without runtime context."""
    correction = CorrectedTranscriptionOutput(corrected_text="Corrected.")
    doubles = _install_action_doubles(
        monkeypatch,
        "CorrectTranscription",
        output=correction,
    )
    runtime = cast(WorkflowRuntime, SimpleNamespace(context=None))
    state = _state(
        result=_transcription(),
        domain_context=_domain_context(),
    )

    with pytest.raises(
        RuntimeError,
        match="Transcriber workflow context is required",
    ):
        nodes.correction_transcriber(state, runtime)

    doubles.action_type.assert_not_called()
    doubles.executor_type.run.assert_not_called()


@pytest.mark.parametrize(
    "state",
    [
        pytest.param(_state(domain_context=_domain_context()), id="missing"),
        pytest.param(
            _state(result=None, domain_context=_domain_context()),
            id="none",
        ),
    ],
)
def test_correction_transcriber_requires_transcription_result(
    monkeypatch: pytest.MonkeyPatch,
    state: TranscriberState,
) -> None:
    """Raise ValueError before correction without a transcription result."""
    correction = CorrectedTranscriptionOutput(corrected_text="Corrected.")
    doubles = _install_action_doubles(
        monkeypatch,
        "CorrectTranscription",
        output=correction,
    )

    with pytest.raises(
        ValueError,
        match="result is required to correct transcription",
    ):
        nodes.correction_transcriber(state, _runtime())

    doubles.action_type.assert_not_called()
    doubles.executor_type.run.assert_not_called()


@pytest.mark.parametrize(
    "state",
    [
        pytest.param(_state(result=_transcription()), id="missing"),
        pytest.param(
            _state(result=_transcription(), domain_context=None),
            id="none",
        ),
    ],
)
def test_correction_transcriber_requires_domain_context(
    monkeypatch: pytest.MonkeyPatch,
    state: TranscriberState,
) -> None:
    """Raise ValueError before correction without domain context."""
    correction = CorrectedTranscriptionOutput(corrected_text="Corrected.")
    doubles = _install_action_doubles(
        monkeypatch,
        "CorrectTranscription",
        output=correction,
    )

    with pytest.raises(
        ValueError,
        match="domain_context is required to correct transcription",
    ):
        nodes.correction_transcriber(state, _runtime())

    doubles.action_type.assert_not_called()
    doubles.executor_type.run.assert_not_called()


def test_correction_transcriber_deep_copies_and_selectively_updates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Correct selected text while deeply preserving all other metadata."""
    transcription = _transcription()
    original_snapshot = transcription.model_dump()
    domain_context = _domain_context()
    llm = object()
    correction = CorrectedTranscriptionOutput(
        corrected_text="Corrected global transcription.",
        corrected_segments=[
            CorrectedSegment(id=20, text="The corrected pytest segment."),
            CorrectedSegment(id=999, text="Unknown IDs are ignored."),
        ],
    )
    doubles = _install_action_doubles(
        monkeypatch,
        "CorrectTranscription",
        output=correction,
    )
    state = _state(
        result=transcription,
        domain_context=domain_context,
    )

    result = nodes.correction_transcriber(
        state,
        _runtime(correction_llm=llm),
    )

    doubles.action_type.assert_called_once_with(
        llm=llm,
        result=transcription,
        domain_context=domain_context,
    )
    doubles.executor_type.run.assert_called_once_with(doubles.action)
    corrected = result["result"]
    assert corrected is not transcription
    assert corrected.text == "Corrected global transcription."
    assert [segment.text for segment in corrected.segments] == [
        "The unedited opening.",
        "The corrected pytest segment.",
        "The untouched ending.",
    ]
    assert corrected.audio_path == transcription.audio_path
    assert corrected.language == transcription.language
    assert corrected.model == transcription.model
    assert corrected.provider == transcription.provider
    assert corrected.raw_response == transcription.raw_response
    assert corrected.raw_response is not transcription.raw_response
    assert corrected.segments[0] is not transcription.segments[0]
    assert corrected.segments[0].words[0] is not transcription.segments[0].words[0]
    assert corrected.segments[0].model_dump(exclude={"text"}) == (
        transcription.segments[0].model_dump(exclude={"text"})
    )
    assert transcription.model_dump() == original_snapshot
    assert result["status"] == "corrected"
    assert result["human_review_reason"] is None
    assert result["input_tokens"] == 11
    assert result["output_tokens"] == 7
    assert result["total_tokens"] == 18


def test_correction_transcriber_updates_last_duplicate_original_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Update only the last indexed segment when original IDs repeat."""
    transcription = _transcription(
        segments=[
            TextSegment(id=7, start=0.0, end=1.0, text="First duplicate."),
            TextSegment(id=7, start=1.0, end=2.0, text="Second duplicate."),
        ]
    )
    correction = CorrectedTranscriptionOutput(
        corrected_text="Corrected duplicate transcription.",
        corrected_segments=[CorrectedSegment(id=7, text="Updated duplicate.")],
    )
    _install_action_doubles(
        monkeypatch,
        "CorrectTranscription",
        output=correction,
    )
    state = _state(result=transcription, domain_context=_domain_context())

    result = nodes.correction_transcriber(state, _runtime())

    corrected = result["result"]
    assert [segment.text for segment in corrected.segments] == [
        "First duplicate.",
        "Updated duplicate.",
    ]
    assert [segment.text for segment in transcription.segments] == [
        "First duplicate.",
        "Second duplicate.",
    ]


def test_correction_transcriber_applies_last_repeated_correction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Apply the final correction when one ID appears repeatedly."""
    transcription = _transcription()
    correction = CorrectedTranscriptionOutput(
        corrected_text="Corrected repeated transcription.",
        corrected_segments=[
            CorrectedSegment(id=20, text="First correction."),
            CorrectedSegment(id=20, text="Final correction."),
        ],
    )
    _install_action_doubles(
        monkeypatch,
        "CorrectTranscription",
        output=correction,
    )
    state = _state(result=transcription, domain_context=_domain_context())

    result = nodes.correction_transcriber(state, _runtime())

    assert result["result"].segments[1].text == "Final correction."
    assert transcription.segments[1].text == "The pytest correction."


def test_correction_transcriber_accepts_empty_segment_corrections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replace only global text when no segment corrections are returned."""
    transcription = _transcription()
    original_segment_values = [
        segment.model_dump() for segment in transcription.segments
    ]
    correction = CorrectedTranscriptionOutput(
        corrected_text="Only the global text changed.",
        corrected_segments=[],
    )
    _install_action_doubles(
        monkeypatch,
        "CorrectTranscription",
        output=correction,
    )
    state = _state(result=transcription, domain_context=_domain_context())

    result = nodes.correction_transcriber(state, _runtime())

    corrected = result["result"]
    assert corrected.text == "Only the global text changed."
    assert [segment.model_dump() for segment in corrected.segments] == (
        original_segment_values
    )
    assert corrected.segments[0] is not transcription.segments[0]
    assert transcription.text == "Original global transcription."


def test_correction_transcriber_propagates_constructor_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Propagate an action construction failure without changing the result."""
    transcription = _transcription()
    original_snapshot = transcription.model_dump()
    correction = CorrectedTranscriptionOutput(corrected_text="Unused.")
    doubles = _install_action_doubles(
        monkeypatch,
        "CorrectTranscription",
        output=correction,
    )
    error = LookupError("action construction failed")
    doubles.action_type.side_effect = error
    state = _state(result=transcription, domain_context=_domain_context())

    with pytest.raises(LookupError) as exc_info:
        nodes.correction_transcriber(state, _runtime())

    assert exc_info.value is error
    assert transcription.model_dump() == original_snapshot
    doubles.executor_type.run.assert_not_called()


def test_correction_transcriber_propagates_executor_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Propagate an executor failure without publishing partial correction."""
    transcription = _transcription()
    original_snapshot = transcription.model_dump()
    correction = CorrectedTranscriptionOutput(corrected_text="Unused.")
    doubles = _install_action_doubles(
        monkeypatch,
        "CorrectTranscription",
        output=correction,
    )
    error = RuntimeError("correction execution failed")
    doubles.executor_type.run.side_effect = error
    state = _state(result=transcription, domain_context=_domain_context())

    with pytest.raises(RuntimeError) as exc_info:
        nodes.correction_transcriber(state, _runtime())

    assert exc_info.value is error
    assert transcription.model_dump() == original_snapshot
    doubles.executor_type.run.assert_called_once_with(doubles.action)


@pytest.mark.parametrize(
    "missing_key",
    ["input_tokens", "output_tokens", "total_tokens"],
)
def test_correction_transcriber_propagates_incomplete_tokens(
    monkeypatch: pytest.MonkeyPatch,
    missing_key: str,
) -> None:
    """Propagate KeyError for each absent correction token metric."""
    transcription = _transcription()
    original_snapshot = transcription.model_dump()
    tokens = _tokens()
    del tokens[missing_key]
    correction = CorrectedTranscriptionOutput(
        corrected_text="Corrected but unpublished.",
        corrected_segments=[CorrectedSegment(id=20, text="Unpublished.")],
    )
    _install_action_doubles(
        monkeypatch,
        "CorrectTranscription",
        output=correction,
        tokens_usage=tokens,
    )
    state = _state(result=transcription, domain_context=_domain_context())

    with pytest.raises(KeyError) as exc_info:
        nodes.correction_transcriber(state, _runtime())

    assert exc_info.value.args == (missing_key,)
    assert transcription.model_dump() == original_snapshot
