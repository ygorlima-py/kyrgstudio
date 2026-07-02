"""Unit tests for transcriber workflow actions."""

import asyncio
from dataclasses import dataclass
from typing import Any, TypeVar, cast

import pytest
from pydantic import BaseModel

from kyrg.llms.base import LLMBase
from kyrg.transcribers.schemas import TextSegment, TranscriptionResult
from kyrg.workflows.transcriber.actions import (
    CorrectTranscription,
    ExtractDomainContext,
)
from kyrg.workflows.transcriber.schemas import (
    CorrectedSegment,
    CorrectedTranscriptionOutput,
    DomainContextOutput,
)


OutputT = TypeVar("OutputT", bound=BaseModel)


@dataclass(frozen=True)
class StructuredCall:
    """Record one structured-output request."""

    prompt: str
    output_schema: type[BaseModel]


class RecordingLLM(LLMBase):
    """Return a configured model while recording structured calls."""

    def __init__(
        self,
        response: BaseModel,
        error: Exception | None = None,
    ) -> None:
        """Initialize the fake response, failure, and call logs."""
        super().__init__()
        self.response = response
        self.error = error
        self.structured_calls: list[StructuredCall] = []
        self.astructured_calls: list[StructuredCall] = []

    def invoke(self, prompt: str) -> str:
        """Reject unstructured synchronous calls from these actions."""
        raise AssertionError(f"Unexpected invoke call: {prompt}")

    async def ainvoke(self, prompt: str) -> str:
        """Reject unstructured asynchronous calls from these actions."""
        raise AssertionError(f"Unexpected ainvoke call: {prompt}")

    def structured(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        """Record and answer a synchronous structured request."""
        self.structured_calls.append(StructuredCall(prompt, output_schema))
        if self.error is not None:
            raise self.error
        return cast(OutputT, self.response)

    async def astructured(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        """Record and answer an asynchronous structured request."""
        self.astructured_calls.append(StructuredCall(prompt, output_schema))
        if self.error is not None:
            raise self.error
        return cast(OutputT, self.response)

    def _structured_once(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        """Reject the unused base implementation hook."""
        raise AssertionError(
            f"Unexpected _structured_once call for {output_schema}: {prompt}"
        )

    async def _astructured_once(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        """Reject the unused asynchronous base implementation hook."""
        raise AssertionError(
            f"Unexpected _astructured_once call for {output_schema}: {prompt}"
        )


class SerializationFailure(RuntimeError):
    """Represent an expected model serialization failure."""


class FailingSerializable:
    """Raise a configured exception when JSON serialization is requested."""

    def __init__(self, error: Exception) -> None:
        """Store the exception and initialize the call log."""
        self.error = error
        self.indents: list[int | None] = []

    def model_dump_json(self, *, indent: int | None = None) -> str:
        """Record the indentation and raise the configured exception."""
        self.indents.append(indent)
        raise self.error


def transcription_result() -> TranscriptionResult:
    """Build a representative normalized transcription result."""
    return TranscriptionResult(
        audio_path="/virtual/interview.wav",
        language="en",
        text="The speaker discusses Pydantic validation.",
        segments=[
            TextSegment(
                id=4,
                start=1.25,
                end=3.5,
                text="The speaker discusses Pydantic validation.",
            )
        ],
        model="offline-test-model",
        raw_response={"request_id": "local-only"},
        provider="fake-provider",
    )


def domain_context() -> DomainContextOutput:
    """Build a representative extracted domain context."""
    return DomainContextOutput(
        language="English",
        main_subject="Pydantic validation",
        content_type="interview",
        summary="An interview about schema validation.",
        important_terms=["Pydantic"],
        correction_rules=["Preserve library names."],
    )


def corrected_output() -> CorrectedTranscriptionOutput:
    """Build a representative corrected transcription output."""
    return CorrectedTranscriptionOutput(
        corrected_text="The speaker discusses Pydantic validation.",
        corrected_segments=[
            CorrectedSegment(
                id=4,
                text="The speaker discusses Pydantic validation.",
            )
        ],
    )


def run_async(coroutine: Any) -> Any:
    """Run one action coroutine without requiring an async pytest plugin."""
    return asyncio.run(coroutine)


def test_extract_domain_context_execute_uses_structured_contract() -> None:
    """Serialize input and call only the synchronous structured method."""
    result = transcription_result()
    expected = domain_context()
    llm = RecordingLLM(expected)

    actual = ExtractDomainContext(llm, result).execute()

    assert actual is expected
    assert len(llm.structured_calls) == 1
    assert llm.astructured_calls == []
    call = llm.structured_calls[0]
    assert call.output_schema is DomainContextOutput
    assert result.model_dump_json(indent=2) in call.prompt
    assert "Raw transcription:" in call.prompt
    assert "{raw_transcription}" not in call.prompt


def test_extract_domain_context_aexecute_uses_astructured_contract() -> None:
    """Serialize input and await only the async structured method."""
    result = transcription_result()
    expected = domain_context()
    llm = RecordingLLM(expected)

    actual = run_async(ExtractDomainContext(llm, result).aexecute())

    assert actual is expected
    assert llm.structured_calls == []
    assert len(llm.astructured_calls) == 1
    call = llm.astructured_calls[0]
    assert call.output_schema is DomainContextOutput
    assert result.model_dump_json(indent=2) in call.prompt
    assert "Raw transcription:" in call.prompt
    assert "{raw_transcription}" not in call.prompt


@pytest.mark.parametrize("mode", ("sync", "async"))
def test_extract_domain_context_propagates_llm_error(mode: str) -> None:
    """Propagate the original LLM exception without an action-level retry."""
    expected_error = RuntimeError("structured extraction failed")
    llm = RecordingLLM(domain_context(), error=expected_error)
    action = ExtractDomainContext(llm, transcription_result())

    with pytest.raises(RuntimeError) as exc_info:
        if mode == "sync":
            action.execute()
        else:
            run_async(action.aexecute())

    assert exc_info.value is expected_error
    assert len(llm.structured_calls) + len(llm.astructured_calls) == 1


@pytest.mark.parametrize("mode", ("sync", "async"))
def test_extract_domain_context_propagates_serialization_error(mode: str) -> None:
    """Propagate input serialization failure before calling the LLM."""
    expected_error = SerializationFailure("result serialization failed")
    failing_result = FailingSerializable(expected_error)
    llm = RecordingLLM(domain_context())
    action = ExtractDomainContext(
        llm,
        cast(TranscriptionResult, failing_result),
    )

    with pytest.raises(SerializationFailure) as exc_info:
        if mode == "sync":
            action.execute()
        else:
            run_async(action.aexecute())

    assert exc_info.value is expected_error
    assert failing_result.indents == [2]
    assert llm.structured_calls == []
    assert llm.astructured_calls == []


def test_correct_transcription_execute_uses_structured_contract() -> None:
    """Interpolate both models and call only synchronous structured output."""
    result = transcription_result()
    context = domain_context()
    expected = corrected_output()
    llm = RecordingLLM(expected)

    actual = CorrectTranscription(llm, result, context).execute()

    assert actual is expected
    assert len(llm.structured_calls) == 1
    assert llm.astructured_calls == []
    call = llm.structured_calls[0]
    assert call.output_schema is CorrectedTranscriptionOutput
    assert context.model_dump_json(indent=2) in call.prompt
    assert result.model_dump_json(indent=2) in call.prompt
    assert "Domain context:" in call.prompt
    assert "Transcription:" in call.prompt
    assert "{domain_context}" not in call.prompt
    assert "{result}" not in call.prompt


def test_correct_transcription_aexecute_uses_astructured_contract() -> None:
    """Interpolate both models and await only async structured output."""
    result = transcription_result()
    context = domain_context()
    expected = corrected_output()
    llm = RecordingLLM(expected)

    actual = run_async(CorrectTranscription(llm, result, context).aexecute())

    assert actual is expected
    assert llm.structured_calls == []
    assert len(llm.astructured_calls) == 1
    call = llm.astructured_calls[0]
    assert call.output_schema is CorrectedTranscriptionOutput
    assert context.model_dump_json(indent=2) in call.prompt
    assert result.model_dump_json(indent=2) in call.prompt
    assert "Domain context:" in call.prompt
    assert "Transcription:" in call.prompt
    assert "{domain_context}" not in call.prompt
    assert "{result}" not in call.prompt


def test_correct_transcription_sync_and_async_contracts_are_equivalent() -> None:
    """Use identical prompts and schemas in synchronous and async modes."""
    llm = RecordingLLM(corrected_output())
    action = CorrectTranscription(
        llm,
        transcription_result(),
        domain_context(),
    )

    action.execute()
    run_async(action.aexecute())

    assert len(llm.structured_calls) == 1
    assert len(llm.astructured_calls) == 1
    assert llm.structured_calls[0] == llm.astructured_calls[0]


@pytest.mark.parametrize("mode", ("sync", "async"))
def test_correct_transcription_propagates_llm_error(mode: str) -> None:
    """Propagate correction LLM failure without an action-level retry."""
    expected_error = RuntimeError("structured correction failed")
    llm = RecordingLLM(corrected_output(), error=expected_error)
    action = CorrectTranscription(
        llm,
        transcription_result(),
        domain_context(),
    )

    with pytest.raises(RuntimeError) as exc_info:
        if mode == "sync":
            action.execute()
        else:
            run_async(action.aexecute())

    assert exc_info.value is expected_error
    assert len(llm.structured_calls) + len(llm.astructured_calls) == 1


@pytest.mark.parametrize("mode", ("sync", "async"))
@pytest.mark.parametrize("failing_model", ("result", "domain_context"))
def test_correct_transcription_propagates_serialization_error(
    mode: str,
    failing_model: str,
) -> None:
    """Propagate either model serialization failure without calling the LLM."""
    expected_error = SerializationFailure(f"{failing_model} serialization failed")
    failing_value = FailingSerializable(expected_error)
    result = transcription_result()
    context = domain_context()
    if failing_model == "result":
        result = cast(TranscriptionResult, failing_value)
    else:
        context = cast(DomainContextOutput, failing_value)
    llm = RecordingLLM(corrected_output())
    action = CorrectTranscription(llm, result, context)

    with pytest.raises(SerializationFailure) as exc_info:
        if mode == "sync":
            action.execute()
        else:
            run_async(action.aexecute())

    assert exc_info.value is expected_error
    assert failing_value.indents == [2]
    assert llm.structured_calls == []
    assert llm.astructured_calls == []
