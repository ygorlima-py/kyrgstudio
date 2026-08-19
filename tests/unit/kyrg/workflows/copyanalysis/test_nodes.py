"""Unit tests for copy analysis workflow nodes.

The suite verifies node-level state transformations and dependency boundaries
with deterministic LLM responses. Graph compilation, routing, checkpointing,
and live model quality are intentionally outside this module.
"""

import json
import re
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, TypedDict, cast

import pytest
from langgraph.runtime import Runtime as WorkflowRuntime
from pydantic import BaseModel

from kyrg.llms.base import LLMBase, OutputT
from kyrg.llms.error import StructuredOutputError
from kyrg.transcribers import TextSegment, TranscriptionResult
from kyrg.workflows.copyanalysis.nodes import (
    analyse_persuasion,
    build_copy_analysis,
    extract_copy_structure,
    extract_offer_elements,
    prepare_copy_input,
)
from kyrg.workflows.copyanalysis.schemas import (
    CopyAnalysisOutput,
    CopyAnalysisWorkflowContext,
    CopySection,
    CopyStructureOutput,
    OfferAnalysisOutput,
    PersuasionAnalysisOutput,
    StructuredTranscript,
)
from kyrg.workflows.copyanalysis.state import CopyAnalysisState

INPUT_TOKENS = 11
OUTPUT_TOKENS = 5
TOKEN_OUTPUT = {
    "input_tokens": INPUT_TOKENS,
    "output_tokens": OUTPUT_TOKENS,
    "total_tokens": INPUT_TOKENS + OUTPUT_TOKENS,
}


class PreparedCopyInput(TypedDict):
    """Typed result returned by the deterministic input-preparation node."""

    clean_transcript: str
    structured_transcription: list[StructuredTranscript]
    language: str | None


class CopyAnalysisLLMNode(Protocol):
    """Common callable contract shared by copy-analysis LLM nodes."""

    def __call__(
        self,
        state: CopyAnalysisState,
        runtime: WorkflowRuntime[CopyAnalysisWorkflowContext],
        /,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class StructuredRequest:
    """Record the prompt and schema received by the deterministic LLM."""

    prompt: str
    output_schema: type[BaseModel]


class SequenceLLM(LLMBase):
    """Return configured schema responses and expose every node-level request."""

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
        self.requests: list[StructuredRequest] = []

    def invoke(self, prompt: str) -> str:
        raise AssertionError("Copy analysis nodes must use structured output.")

    async def ainvoke(self, prompt: str) -> str:
        raise AssertionError("Copy analysis nodes must use structured output.")

    def _structured_once(
        self,
        prompt: str,
        system_prompt: str,
        prompt_cache_key: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        return self._respond(prompt, output_schema)

    async def _astructured_once(
        self,
        prompt: str,
        system_prompt: str,
        prompt_cache_key: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        return self._respond(prompt, output_schema)

    def _respond(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        """Consume one response and validate raw dictionaries through the schema."""

        self.requests.append(
            StructuredRequest(prompt=prompt, output_schema=output_schema)
        )
        self._add_token(INPUT_TOKENS, OUTPUT_TOKENS)

        try:
            response = self.responses[output_schema].popleft()
        except (KeyError, IndexError) as error:
            raise AssertionError(
                f"No response configured for {output_schema.__name__}."
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
    text: str = (
        "  Tu comisión\n\ttambién puede trabajar por tu futuro.   "
        "Aprende a invertir con un plan.  "
    ),
    language: str | None = "es",
    segments: list[TextSegment] | None = None,
) -> TranscriptionResult:
    """Return a normalized transcription with configurable segment metadata."""

    return TranscriptionResult(
        audio_path="/tmp/reference.wav",
        language=language,
        text=text,
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


def _copy_structure() -> CopyStructureOutput:
    """Return a deterministic copy structure for downstream node tests."""

    return CopyStructureOutput(
        language="Spanish",
        content_type="VSL",
        main_hook="Tu comisión también puede trabajar por tu futuro.",
        sections=[
            CopySection(
                section_type="hook",
                text="Tu comisión también puede trabajar por tu futuro.",
                purpose="Captar atención mediante una aspiración financiera.",
                start=0.0,
                end=4.0,
            ),
            CopySection(
                section_type="education",
                text="Aprende a invertir con un plan.",
                purpose="Presentar un camino educativo.",
                start=4.0,
                end=8.5,
            ),
        ],
        narrative_flow=["hook", "education"],
        section_gaps=[],
        summary="La copy conecta una aspiración con educación financiera.",
    )


def _offer_analysis() -> OfferAnalysisOutput:
    """Return a deterministic offer analysis."""

    return OfferAnalysisOutput(
        product_or_solution="Curso de educación financiera",
        target_audience="Profesionales con ingresos por comisión",
        core_problem="No saben cómo organizar sus inversiones",
        core_desire="Construir una cartera diversificada",
        main_promise="Aprender un proceso responsable de inversión",
        unique_mechanism="Método de Organización de Comisiones",
        call_to_action="Entrar en la lista de interés",
        summary="La oferta enseña a organizar comisiones e inversiones.",
    )


def _persuasion_analysis() -> PersuasionAnalysisOutput:
    """Return a deterministic persuasion diagnosis."""

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
        summary="La copy educa y construye aspiración antes de la oferta.",
    )


def _llm(
    *,
    structure_responses: Sequence[
        CopyStructureOutput | dict[str, Any] | Exception
    ]
    | None = None,
) -> SequenceLLM:
    """Build an LLM configured for every copy analysis action schema."""

    return SequenceLLM(
        {
            CopyStructureOutput: structure_responses or [_copy_structure()],
            OfferAnalysisOutput: [_offer_analysis()],
            PersuasionAnalysisOutput: [_persuasion_analysis()],
        }
    )


def _runtime(
    llm: SequenceLLM | None = None,
) -> tuple[WorkflowRuntime[CopyAnalysisWorkflowContext], SequenceLLM]:
    """Return a typed runtime and its observable LLM dependency."""

    analysis_llm = llm or _llm()
    runtime = WorkflowRuntime(
        context=CopyAnalysisWorkflowContext(analysis_llm=analysis_llm)
    )
    return runtime, analysis_llm


def _base_state() -> CopyAnalysisState:
    """Return state containing every dependency required by downstream nodes."""

    return {
        "transcription": _transcription(),
        "clean_transcript": (
            "Tu comisión también puede trabajar por tu futuro. "
            "Aprende a invertir con un plan."
        ),
        "structured_transcription": [
            StructuredTranscript(
                start=0.0,
                end=4.0,
                text="Tu comisión también puede trabajar por tu futuro.",
            ),
            StructuredTranscript(
                start=4.0,
                end=8.5,
                text="Aprende a invertir con un plan.",
            ),
        ],
        "language": "es",
        "copy_structure": _copy_structure(),
        "offer_analysis": _offer_analysis(),
        "persuasion_analysis": _persuasion_analysis(),
    }


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


def _json_tag(prompt: str, tag_name: str) -> object:
    """Decode JSON stored inside a named XML-style prompt tag."""

    return json.loads(_tag_content(prompt, tag_name))


def _assert_token_output(output: dict[str, Any]) -> None:
    """Assert that a node exposes exactly one action's token usage."""

    assert {
        key: output[key]
        for key in TOKEN_OUTPUT
    } == TOKEN_OUTPUT


def test_prepare_copy_input_normalizes_text_and_preserves_source() -> None:
    """Preparation should normalize whitespace without mutating transcription data."""

    transcription = _transcription()
    original = transcription.model_dump()
    state: CopyAnalysisState = {"transcription": transcription}

    output = cast(PreparedCopyInput, prepare_copy_input(state))

    assert output["clean_transcript"] == (
        "Tu comisión también puede trabajar por tu futuro. "
        "Aprende a invertir con un plan."
    )
    assert output["language"] == "es"
    assert transcription.model_dump() == original


def test_prepare_copy_input_converts_every_segment_with_timestamps() -> None:
    """Preparation should convert provider segments into workflow-owned schemas."""

    state: CopyAnalysisState = {"transcription": _transcription()}
    output = cast(PreparedCopyInput, prepare_copy_input(state))
    segments = output["structured_transcription"]

    assert len(segments) == 2
    assert all(isinstance(segment, StructuredTranscript) for segment in segments)
    assert segments[0].start == 0.0
    assert segments[0].end == 4.0
    assert segments[1].text == "Aprende a invertir con un plan."


def test_prepare_copy_input_preserves_null_timestamps() -> None:
    """Unavailable provider timestamps must remain null rather than fabricated."""

    transcription = _transcription(
        segments=[
            TextSegment(
                id=0,
                start=None,
                end=None,
                text="Segmento sin tiempo.",
            )
        ]
    )

    state: CopyAnalysisState = {"transcription": transcription}
    output = cast(PreparedCopyInput, prepare_copy_input(state))
    segment = output["structured_transcription"][0]

    assert segment.start is None
    assert segment.end is None


def test_prepare_copy_input_returns_empty_segments_when_provider_has_none() -> None:
    """A transcript without segments should still produce a valid empty collection."""

    state: CopyAnalysisState = {
        "transcription": _transcription(segments=[]),
    }
    output = cast(
        PreparedCopyInput,
        prepare_copy_input(state),
    )

    assert output["structured_transcription"] == []


def test_prepare_copy_input_rejects_missing_transcription() -> None:
    """Preparation must fail before text access when transcription is absent."""

    with pytest.raises(
        ValueError,
        match="transcription is required to prepare copy input",
    ):
        prepare_copy_input(cast(CopyAnalysisState, {}))


@pytest.mark.parametrize("text", ("", "   ", "\n\t  "))
def test_prepare_copy_input_rejects_blank_transcription_text(text: str) -> None:
    """Blank transcription content must never reach an LLM action."""

    with pytest.raises(
        ValueError,
        match="transcription text is required to prepare copy input",
    ):
        state: CopyAnalysisState = {
            "transcription": _transcription(text=text),
        }
        prepare_copy_input(state)


def test_extract_copy_structure_returns_only_analysis_and_tokens() -> None:
    """Structure extraction should expose its result without leaking action state."""

    runtime, llm = _runtime()
    state = _base_state()

    output = extract_copy_structure(state, runtime)

    assert output == {
        "copy_structure": _copy_structure(),
        **TOKEN_OUTPUT,
    }
    assert llm.requests[0].output_schema is CopyStructureOutput
    assert "copy_structure_retry_count" not in output
    assert "copy_structure_error_history" not in output


def test_extract_copy_structure_forwards_segments_and_language() -> None:
    """The node should forward prepared transcript context without transformation."""

    runtime, llm = _runtime()
    state = _base_state()

    extract_copy_structure(state, runtime)

    prompt = llm.requests[0].prompt
    structured_transcription = state.get("structured_transcription")

    assert structured_transcription is not None
    assert _tag_content(prompt, "language") == "es"
    assert _json_tag(prompt, "structured_transcription") == [
        segment.model_dump()
        for segment in structured_transcription
    ]


def test_extract_copy_structure_uses_empty_segments_when_state_has_none() -> None:
    """Missing optional segmentation should be normalized to an empty prompt list."""

    runtime, llm = _runtime()
    state = _base_state()
    state["structured_transcription"] = None

    extract_copy_structure(state, runtime)

    assert _json_tag(llm.requests[0].prompt, "structured_transcription") == []


def test_extract_copy_structure_propagates_exhausted_structured_retry() -> None:
    """The node must propagate failure after the central retry policy is exhausted."""

    llm = _llm(structure_responses=[{}, {}])
    runtime, _ = _runtime(llm)

    with pytest.raises(StructuredOutputError, match="CopyStructureOutput"):
        extract_copy_structure(_base_state(), runtime)

    assert len(llm.requests) == 2
    assert all(
        request.output_schema is CopyStructureOutput
        for request in llm.requests
    )


def test_extract_offer_elements_returns_only_analysis_and_tokens() -> None:
    """Offer extraction should publish only its normalized result and usage."""

    runtime, llm = _runtime()

    output = extract_offer_elements(_base_state(), runtime)

    assert output == {
        "offer_analysis": _offer_analysis(),
        **TOKEN_OUTPUT,
    }
    assert llm.requests[0].output_schema is OfferAnalysisOutput


def test_extract_offer_elements_forwards_exact_structure() -> None:
    """Offer extraction must consume the same structure produced upstream."""

    runtime, llm = _runtime()
    state = _base_state()
    structure = state.get("copy_structure")

    assert structure is not None

    extract_offer_elements(state, runtime)

    assert _json_tag(llm.requests[0].prompt, "copy_structure") == (
        structure.model_dump()
    )


def test_analyse_persuasion_returns_only_analysis_and_tokens() -> None:
    """Persuasion analysis should publish its diagnosis and one usage delta."""

    runtime, llm = _runtime()

    output = analyse_persuasion(_base_state(), runtime)

    assert output == {
        "persuasion_analysis": _persuasion_analysis(),
        **TOKEN_OUTPUT,
    }
    assert llm.requests[0].output_schema is PersuasionAnalysisOutput


def test_analyse_persuasion_forwards_prior_analyses_and_language() -> None:
    """Persuasion analysis must receive both upstream results and source language."""

    runtime, llm = _runtime()
    state = _base_state()

    analyse_persuasion(state, runtime)

    prompt = llm.requests[0].prompt
    copy_structure = state.get("copy_structure")
    offer_analysis = state.get("offer_analysis")

    assert copy_structure is not None
    assert offer_analysis is not None
    assert _tag_content(prompt, "language") == "es"
    assert _json_tag(prompt, "copy_structure") == copy_structure.model_dump()
    assert _json_tag(prompt, "offer_analysis") == offer_analysis.model_dump()


@pytest.mark.parametrize(
    "node",
    (extract_copy_structure, extract_offer_elements, analyse_persuasion),
)
def test_llm_nodes_reject_missing_runtime_context(
    node: CopyAnalysisLLMNode,
) -> None:
    """Every LLM-backed node should fail before state access without context."""

    runtime = cast(
        WorkflowRuntime[CopyAnalysisWorkflowContext],
        WorkflowRuntime(context=None),
    )

    with pytest.raises(
        RuntimeError,
        match="Copy analysis workflow context is required",
    ):
        node(cast(CopyAnalysisState, {}), runtime)


@pytest.mark.parametrize(
    ("node", "state", "message"),
    (
        (
            extract_copy_structure,
            {},
            "clean_transcript is required to extract copy structure",
        ),
        (
            extract_offer_elements,
            {},
            "clean_transcript is required to extract offer analysis",
        ),
        (
            extract_offer_elements,
            {"clean_transcript": "Valid text."},
            "copy structure is required to extract offer analysis",
        ),
        (
            analyse_persuasion,
            {},
            "clean_transcript is required to analyse persuasion",
        ),
        (
            analyse_persuasion,
            {"clean_transcript": "Valid text."},
            "copy structure is required to analyse persuasion",
        ),
        (
            analyse_persuasion,
            {
                "clean_transcript": "Valid text.",
                "copy_structure": _copy_structure(),
            },
            "Offer structure is required to analyse persuasion",
        ),
    ),
)
def test_llm_nodes_reject_missing_state_dependencies_before_calling_llm(
    node: CopyAnalysisLLMNode,
    state: dict[str, Any],
    message: str,
) -> None:
    """Each node should identify its first missing dependency without model usage."""

    runtime, llm = _runtime()

    with pytest.raises(ValueError, match=message):
        node(cast(CopyAnalysisState, state), runtime)

    assert llm.requests == []


def test_build_copy_analysis_consolidates_existing_models_without_loss() -> None:
    """Final consolidation should preserve upstream model instances and language."""

    state = _base_state()
    copy_structure = state.get("copy_structure")
    offer_analysis = state.get("offer_analysis")
    persuasion_analysis = state.get("persuasion_analysis")

    assert copy_structure is not None
    assert offer_analysis is not None
    assert persuasion_analysis is not None

    output = build_copy_analysis(state)

    assert set(output) == {"analysis"}
    analysis = output["analysis"]
    assert isinstance(analysis, CopyAnalysisOutput)
    assert analysis.language == "es"
    assert analysis.copy_structure is copy_structure
    assert analysis.offer_analysis is offer_analysis
    assert analysis.persuasion_analysis is persuasion_analysis
    CopyAnalysisOutput.model_validate_json(analysis.model_dump_json())


@pytest.mark.parametrize(
    ("missing_field", "message"),
    (
        ("copy_structure", "copy_structure is required to build copy analysis"),
        ("offer_analysis", "offer_analysis is required to build copy analysis"),
        (
            "persuasion_analysis",
            "persuasion_analysis is required to build copy analysis",
        ),
    ),
)
def test_build_copy_analysis_rejects_partial_results(
    missing_field: str,
    message: str,
) -> None:
    """Final output must never be produced from incomplete upstream analysis."""

    partial_state = dict(_base_state())
    partial_state.pop(missing_field)

    with pytest.raises(ValueError, match=message):
        build_copy_analysis(cast(CopyAnalysisState, partial_state))
