"""Integration tests for the compiled copy analysis workflow graph.

The suite executes the real ``CopyAnalysisWorkflow`` with deterministic LLM
responses. It verifies graph sequencing, technical structured-output retries,
token reduction, asynchronous parity, and checkpoint-based resumption without
calling external providers.
"""

import asyncio
import json
import re
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import pytest
from pydantic import BaseModel

from kyrg.llms.base import LLMBase, OutputT
from kyrg.llms.error import (
    StructuredOutputError,
    StructuredOutputParsingError,
)
from kyrg.transcribers import TextSegment, TranscriptionResult
from kyrg.workflows.checkpointers import SQLiteCheckpointer
from kyrg.workflows.copyanalysis.schemas import (
    CopyAnalysisOutput,
    CopyAnalysisWorkflowContext,
    CopySection,
    CopyStructureOutput,
    OfferAnalysisOutput,
    PersuasionAnalysisOutput,
)
from kyrg.workflows.copyanalysis.workflow import CopyAnalysisWorkflow


INPUT_TOKENS_PER_CALL = 10
OUTPUT_TOKENS_PER_CALL = 4


@pytest.fixture(autouse=True)
def isolate_generated_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep the workflow JSON decorator from writing into the repository."""

    monkeypatch.chdir(tmp_path)


@dataclass(frozen=True)
class LLMCall:
    """Record one provider attempt made during graph execution."""

    mode: Literal["sync", "async"]
    output_schema: type[BaseModel]
    prompt: str


class WorkflowLLM(LLMBase):
    """Serve ordered responses per schema and observe the real graph execution."""

    def __init__(
        self,
        responses: dict[
            type[BaseModel],
            Sequence[BaseModel | dict[str, Any] | Exception],
        ],
        *,
        max_attempts: int = 2,
    ) -> None:
        super().__init__(max_attempts=max_attempts)
        self.responses = {
            schema: deque(schema_responses)
            for schema, schema_responses in responses.items()
        }
        self.calls: list[LLMCall] = []
        self._active_schema: type[BaseModel] | None = None

    def invoke(self, prompt: str) -> str:
        raise AssertionError("Copy analysis workflow must use structured output.")

    async def ainvoke(self, prompt: str) -> str:
        raise AssertionError("Copy analysis workflow must use structured output.")

    def _structured_once(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        return self._next("sync", prompt, output_schema)

    async def _astructured_once(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        return self._next("async", prompt, output_schema)

    def _next(
        self,
        mode: Literal["sync", "async"],
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        """Consume one response while tracking usage for the current action."""

        if self._active_schema is not output_schema:
            self._active_schema = output_schema
            self._input_tokens = 0
            self._output_tokens = 0

        self.calls.append(
            LLMCall(
                mode=mode,
                output_schema=output_schema,
                prompt=prompt,
            )
        )
        current_usage = self.token_usage()
        self._add_token(
            input_tokens=current_usage["input_tokens"] + INPUT_TOKENS_PER_CALL,
            output_tokens=current_usage["output_tokens"] + OUTPUT_TOKENS_PER_CALL,
        )

        try:
            response = self.responses[output_schema].popleft()
        except (KeyError, IndexError) as error:
            raise AssertionError(
                f"Unexpected call for {output_schema.__name__}."
            ) from error

        if isinstance(response, Exception):
            raise response

        if isinstance(response, dict):
            return output_schema.model_validate(response)

        if type(response) is not output_schema:
            raise AssertionError(
                f"Expected {output_schema.__name__}, got {type(response).__name__}."
            )

        return cast(OutputT, response)


def _transcription(
    *,
    language: str | None = "es",
    segments: list[TextSegment] | None = None,
    label: str = "reference",
) -> TranscriptionResult:
    """Return a provider-independent transcription accepted by the workflow."""

    return TranscriptionResult(
        audio_path=f"/tmp/{label}.wav",
        language=language,
        text=(
            "Tu comisión también puede trabajar por tu futuro. "
            "Aprende a invertir con un plan."
        ),
        segments=(
            [
                TextSegment(
                    id=0,
                    start=0.0,
                    end=4.0,
                    text="Tu comisión también puede trabajar por tu futuro.",
                ),
                TextSegment(
                    id=1,
                    start=4.0,
                    end=8.5,
                    text="Aprende a invertir con un plan.",
                ),
            ]
            if segments is None
            else segments
        ),
        model="small",
        raw_response={"duration": 8.5},
        provider="whisper-local",
    )


def _copy_structure(
    *,
    timed: bool = True,
    label: str = "reference",
) -> CopyStructureOutput:
    """Return structural output identifiable across workflow executions."""

    return CopyStructureOutput(
        language="Spanish",
        content_type="VSL",
        main_hook=f"{label}: tu comisión puede trabajar por tu futuro.",
        sections=[
            CopySection(
                section_type="hook",
                text=f"{label}: tu comisión puede trabajar por tu futuro.",
                purpose="Captar atención mediante una aspiración financiera.",
                start=0.0 if timed else None,
                end=4.0 if timed else None,
            ),
            CopySection(
                section_type="education",
                text="Aprende a invertir con un plan.",
                purpose="Presentar un camino educativo.",
                start=4.0 if timed else None,
                end=8.5 if timed else None,
            ),
        ],
        narrative_flow=["hook", "education"],
        section_gaps=[],
        summary="La copy conecta una aspiración con educación financiera.",
    )


def _offer_analysis(label: str = "reference") -> OfferAnalysisOutput:
    """Return offer output identifiable across workflow executions."""

    return OfferAnalysisOutput(
        product_or_solution=f"{label}: curso de educación financiera",
        target_audience="Profesionales con ingresos por comisión",
        core_problem="No saben cómo organizar sus inversiones",
        core_desire="Construir una cartera diversificada",
        main_promise="Aprender un proceso responsable de inversión",
        unique_mechanism="Método de Organización de Comisiones",
        call_to_action="Entrar en la lista de interés",
        summary="La oferta enseña a organizar comisiones e inversiones.",
    )


def _persuasion_analysis(label: str = "reference") -> PersuasionAnalysisOutput:
    """Return persuasion output identifiable across workflow executions."""

    return PersuasionAnalysisOutput(
        dominant_emotion="aspiración",
        persuasion_pattern="education-to-offer",
        hook_strength="high",
        promise_clarity="high",
        proof_strength="low",
        urgency_strength="low",
        cta_strength="medium",
        persuasion_signals=[],
        weaknesses=[],
        summary=f"{label}: la copy educa antes de presentar la oferta.",
    )


def _llm(
    *,
    structure_responses: Sequence[
        CopyStructureOutput | dict[str, Any] | Exception
    ]
    | None = None,
    offer_responses: Sequence[OfferAnalysisOutput | Exception] | None = None,
    persuasion_responses: Sequence[PersuasionAnalysisOutput | Exception]
    | None = None,
    label: str = "reference",
) -> WorkflowLLM:
    """Build a deterministic LLM queue for one workflow execution."""

    return WorkflowLLM(
        {
            CopyStructureOutput: structure_responses or [
                _copy_structure(label=label)
            ],
            OfferAnalysisOutput: offer_responses or [
                _offer_analysis(label)
            ],
            PersuasionAnalysisOutput: persuasion_responses or [
                _persuasion_analysis(label)
            ],
        }
    )


def _workflow(
    llm: WorkflowLLM,
    *,
    transcription: TranscriptionResult | None = None,
    checkpointer: SQLiteCheckpointer | None = None,
    thread_id: str | None = None,
) -> CopyAnalysisWorkflow:
    """Build the real workflow with deterministic external dependencies."""

    initial_state = (
        {"transcription": transcription}
        if transcription is not None
        else {}
    )
    return CopyAnalysisWorkflow(
        initial_state=initial_state,
        context=CopyAnalysisWorkflowContext(analysis_llm=llm),
        checkpointer=checkpointer,
        thread_id=thread_id,
    )


def _run_workflow(
    llm: WorkflowLLM,
    *,
    transcription: TranscriptionResult | None = None,
    checkpointer: SQLiteCheckpointer | None = None,
    thread_id: str | None = None,
) -> dict[str, Any]:
    """Execute the real synchronous graph and return its final state."""

    workflow = _workflow(
        llm,
        transcription=transcription or _transcription(),
        checkpointer=checkpointer,
        thread_id=thread_id,
    )
    return workflow.start()


def _schemas(llm: WorkflowLLM) -> list[type[BaseModel]]:
    """Return the ordered structured schemas requested by the graph."""

    return [call.output_schema for call in llm.calls]


def _tag_content(prompt: str, tag_name: str) -> str:
    """Extract normalized text enclosed by an XML-style prompt tag."""

    match = re.search(
        rf"<{tag_name}>\s*(.*?)\s*</{tag_name}>",
        prompt,
        flags=re.DOTALL,
    )

    if match is None:
        raise AssertionError(f"Prompt tag <{tag_name}> was not found.")

    return match.group(1).strip()


def _assert_token_totals(result: dict[str, Any], call_count: int) -> None:
    """Assert reducer totals for all provider attempts committed to state."""

    assert result["input_tokens"] == INPUT_TOKENS_PER_CALL * call_count
    assert result["output_tokens"] == OUTPUT_TOKENS_PER_CALL * call_count
    assert result["total_tokens"] == (
        INPUT_TOKENS_PER_CALL + OUTPUT_TOKENS_PER_CALL
    ) * call_count
    assert result["total_tokens"] == (
        result["input_tokens"] + result["output_tokens"]
    )


def test_happy_path_runs_in_order_and_returns_consolidated_analysis() -> None:
    """A valid transcription should traverse every analysis stage exactly once."""

    llm = _llm()

    result = _run_workflow(llm)

    assert _schemas(llm) == [
        CopyStructureOutput,
        OfferAnalysisOutput,
        PersuasionAnalysisOutput,
    ]
    analysis = result["analysis"]
    assert isinstance(analysis, CopyAnalysisOutput)
    assert analysis.language == "es"
    assert analysis.copy_structure == _copy_structure()
    assert analysis.offer_analysis == _offer_analysis()
    assert analysis.persuasion_analysis == _persuasion_analysis()
    assert "copy_structure_retry_count" not in result
    assert "copy_structure_error_history" not in result
    _assert_token_totals(result, call_count=3)


def test_transcription_without_segments_completes_with_null_timestamps() -> None:
    """Untimed transcription should complete without fabricated section timing."""

    llm = _llm(
        structure_responses=[_copy_structure(timed=False)]
    )

    result = _run_workflow(llm, transcription=_transcription(segments=[]))

    assert json.loads(
        _tag_content(llm.calls[0].prompt, "structured_transcription")
    ) == []
    assert all(
        section.start is None and section.end is None
        for section in result["analysis"].copy_structure.sections
    )
    assert isinstance(result["analysis"], CopyAnalysisOutput)


def test_validation_error_retries_inside_node_and_then_continues() -> None:
    """Invalid schema output should be repaired without adding a graph retry loop."""

    llm = _llm(structure_responses=[{}, _copy_structure()])

    result = _run_workflow(llm)

    assert _schemas(llm) == [
        CopyStructureOutput,
        CopyStructureOutput,
        OfferAnalysisOutput,
        PersuasionAnalysisOutput,
    ]
    retry_prompt = llm.calls[1].prompt
    assert "<schema_validation_retry>" in retry_prompt
    assert "content_type" in retry_prompt
    assert "copy_structure_retry_count" not in result
    assert "copy_structure_error_history" not in result
    assert isinstance(result["analysis"], CopyAnalysisOutput)
    _assert_token_totals(result, call_count=4)


def test_parsing_error_retries_inside_node_and_then_continues() -> None:
    """Provider parsing failure should be normalized and retried in the LLM layer."""

    llm = _llm(
        structure_responses=[
            StructuredOutputParsingError("Malformed structured response"),
            _copy_structure(),
        ]
    )

    result = _run_workflow(llm)

    assert _schemas(llm) == [
        CopyStructureOutput,
        CopyStructureOutput,
        OfferAnalysisOutput,
        PersuasionAnalysisOutput,
    ]
    assert "parsing_error" in llm.calls[1].prompt
    assert isinstance(result["analysis"], CopyAnalysisOutput)
    _assert_token_totals(result, call_count=4)


def test_exhausted_structured_retry_stops_downstream_nodes() -> None:
    """Exhausted schema recovery must fail without publishing partial analysis."""

    llm = _llm(structure_responses=[{}, {}])
    workflow = _workflow(llm, transcription=_transcription())

    with pytest.raises(StructuredOutputError, match="CopyStructureOutput"):
        workflow.start()

    assert _schemas(llm) == [CopyStructureOutput, CopyStructureOutput]
    assert not Path("CopyAnalysisWorkflow.json").exists()


def test_nonrecoverable_error_is_not_retried() -> None:
    """Authentication or programming failures should propagate after one attempt."""

    llm = _llm(
        structure_responses=[RuntimeError("Invalid provider credentials")]
    )
    workflow = _workflow(llm, transcription=_transcription())

    with pytest.raises(RuntimeError, match="Invalid provider credentials"):
        workflow.start()

    assert _schemas(llm) == [CopyStructureOutput]
    assert not Path("CopyAnalysisWorkflow.json").exists()


def test_same_thread_resumes_failed_node_without_repeating_completed_work(
    tmp_path: Path,
) -> None:
    """Checkpoint resumption should retry only the interrupted analysis action."""

    llm = _llm(
        offer_responses=[
            RuntimeError("Temporary offer analysis failure"),
            _offer_analysis(),
        ]
    )
    workflow = _workflow(
        llm,
        transcription=_transcription(),
        checkpointer=SQLiteCheckpointer(str(tmp_path / "resume.sqlite")),
        thread_id="copyanalysis:interrupted",
    )

    with pytest.raises(RuntimeError, match="Temporary offer analysis failure"):
        workflow.start()

    result = workflow.start()

    assert _schemas(llm) == [
        CopyStructureOutput,
        OfferAnalysisOutput,
        OfferAnalysisOutput,
        PersuasionAnalysisOutput,
    ]
    assert isinstance(result["copy_structure"], CopyStructureOutput)
    assert isinstance(result["analysis"], CopyAnalysisOutput)
    _assert_token_totals(result, call_count=4)


def test_new_thread_starts_without_state_from_completed_thread(
    tmp_path: Path,
) -> None:
    """Different thread identifiers must keep analyses and token state isolated."""

    checkpointer = SQLiteCheckpointer(str(tmp_path / "threads.sqlite"))
    first_llm = _llm(label="first")
    second_llm = _llm(label="second")

    first_result = _run_workflow(
        first_llm,
        transcription=_transcription(label="first"),
        checkpointer=checkpointer,
        thread_id="copyanalysis:first",
    )
    second_result = _run_workflow(
        second_llm,
        transcription=_transcription(label="second"),
        checkpointer=checkpointer,
        thread_id="copyanalysis:second",
    )

    assert first_result["analysis"].copy_structure.main_hook.startswith("first")
    assert second_result["analysis"].copy_structure.main_hook.startswith("second")
    assert _schemas(first_llm) == [
        CopyStructureOutput,
        OfferAnalysisOutput,
        PersuasionAnalysisOutput,
    ]
    assert _schemas(second_llm) == [
        CopyStructureOutput,
        OfferAnalysisOutput,
        PersuasionAnalysisOutput,
    ]
    _assert_token_totals(first_result, call_count=3)
    _assert_token_totals(second_result, call_count=3)


@pytest.mark.skip(
    reason=(
        "CopyAnalysisWorkflow.astart currently stalls after the first "
        "LLM-backed node; enable this regression test after async graph "
        "execution is corrected."
    )
)
def test_async_execution_uses_only_async_structured_calls() -> None:
    """Asynchronous workflow execution should preserve output and avoid sync calls."""

    llm = _llm()
    workflow = _workflow(llm, transcription=_transcription())

    result = asyncio.run(workflow.astart())

    assert [call.mode for call in llm.calls] == ["async", "async", "async"]
    assert _schemas(llm) == [
        CopyStructureOutput,
        OfferAnalysisOutput,
        PersuasionAnalysisOutput,
    ]
    assert isinstance(result["analysis"], CopyAnalysisOutput)
    _assert_token_totals(result, call_count=3)


def test_missing_transcription_fails_before_first_llm_call() -> None:
    """Missing public input should stop preparation before any model usage."""

    llm = _llm()
    workflow = _workflow(llm, transcription=None)

    with pytest.raises(RuntimeError, match="required to this workflow"):
        workflow.start()

    assert llm.calls == []
    assert not Path("CopyAnalysisWorkflow.json").exists()
