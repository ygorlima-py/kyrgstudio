"""Contract tests for copy analysis LLM actions.

The suite verifies prompt construction and the boundary between each action and
``LLMBase`` without executing graph nodes or making network requests.
"""

import asyncio
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, cast

import pytest
from pydantic import BaseModel

from kyrg.llms.base import LLMBase, OutputT
from kyrg.workflows.base import AIActionBase
from kyrg.workflows.copyanalysis.actions import (
    AnalysePersuasion,
    ExtractCopyStructure,
    ExtractOfferElements,
)
from kyrg.workflows.copyanalysis.schemas import (
    CopySection,
    CopyStructureOutput,
    OfferAnalysisOutput,
    PersuasionAnalysisOutput,
    StructuredTranscript,
)


INPUT_TOKENS = 19
OUTPUT_TOKENS = 7


@dataclass(frozen=True)
class StructuredCall:
    """Record one structured-output request made by an action."""

    mode: Literal["sync", "async"]
    prompt: str
    output_schema: type[BaseModel]


class RecordingLLM(LLMBase):
    """Return deterministic schema responses and record every provider call."""

    def __init__(self, failure: Exception | None = None) -> None:
        super().__init__()
        self.failure = failure
        self.calls: list[StructuredCall] = []
        self.last_response: BaseModel | None = None

    def invoke(self, prompt: str) -> str:
        raise AssertionError("Copy analysis actions must use structured output.")

    async def ainvoke(self, prompt: str) -> str:
        raise AssertionError("Copy analysis actions must use structured output.")

    def _structured_once(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        return self._record_call("sync", prompt, output_schema)

    async def _astructured_once(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        return self._record_call("async", prompt, output_schema)

    def _record_call(
        self,
        mode: Literal["sync", "async"],
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        """Capture one call and either raise the configured failure or respond."""

        self.calls.append(
            StructuredCall(
                mode=mode,
                prompt=prompt,
                output_schema=output_schema,
            )
        )

        if self.failure is not None:
            raise self.failure

        response = _response_for(output_schema)
        self.last_response = response
        self._add_token(INPUT_TOKENS, OUTPUT_TOKENS)
        return response


ActionFactory = Callable[[RecordingLLM], AIActionBase]


def _copy_structure() -> CopyStructureOutput:
    """Return a deterministic structure used by downstream action tests."""

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
                section_type="offer",
                text="Aprende a organizar tus inversiones paso a paso.",
                purpose="Presentar la solución educativa.",
                start=4.0,
                end=9.0,
            ),
        ],
        narrative_flow=["hook", "offer"],
        section_gaps=[],
        summary="La VSL conecta una aspiración financiera con una oferta educativa.",
    )


def _offer_analysis() -> OfferAnalysisOutput:
    """Return a deterministic offer analysis containing Unicode text."""

    return OfferAnalysisOutput(
        product_or_solution="Curso de educación financiera",
        target_audience="Profesionales con ingresos por comisión",
        core_problem="No saben cómo organizar sus inversiones",
        core_desire="Construir una cartera diversificada",
        main_promise="Aprender un proceso responsable de inversión",
        unique_mechanism="Método de Organización de Comisiones",
        call_to_action="Entrar en la lista de interés",
        summary="Una oferta educativa para organizar comisiones e inversiones.",
    )


def _persuasion_analysis() -> PersuasionAnalysisOutput:
    """Return a valid deterministic persuasion response."""

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
        summary="La copy educa antes de presentar la solución.",
    )


def _response_for(output_schema: type[OutputT]) -> OutputT:
    """Build the exact Pydantic response declared by an action."""

    if output_schema is CopyStructureOutput:
        return cast(OutputT, _copy_structure())

    if output_schema is OfferAnalysisOutput:
        return cast(OutputT, _offer_analysis())

    if output_schema is PersuasionAnalysisOutput:
        return cast(OutputT, _persuasion_analysis())

    raise AssertionError(f"No fake response configured for {output_schema.__name__}.")


def _extract_structure_action(llm: RecordingLLM) -> ExtractCopyStructure:
    """Build the structure extraction action with timed transcript segments."""

    return ExtractCopyStructure(
        llm=llm,
        clean_transcript=(
            "Tu comisión también puede trabajar por tu futuro. "
            "Aprende a organizar tus inversiones paso a paso."
        ),
        structured_transcription=[
            StructuredTranscript(
                start=0.0,
                end=4.0,
                text="Tu comisión también puede trabajar por tu futuro.",
            ),
            StructuredTranscript(
                start=4.0,
                end=9.0,
                text="Aprende a organizar tus inversiones paso a paso.",
            ),
        ],
        language="Spanish",
    )


def _extract_offer_action(llm: RecordingLLM) -> ExtractOfferElements:
    """Build the offer extraction action with validated structure context."""

    return ExtractOfferElements(
        llm=llm,
        clean_transcript=(
            "Tu comisión también puede trabajar por tu futuro. "
            "Aprende a organizar tus inversiones paso a paso."
        ),
        copy_structure=_copy_structure(),
        language="Spanish",
    )


def _analyse_persuasion_action(llm: RecordingLLM) -> AnalysePersuasion:
    """Build the persuasion action from prior structured analyses."""

    return AnalysePersuasion(
        llm=llm,
        copy_structure=_copy_structure(),
        offer_analysis=_offer_analysis(),
        language="Spanish",
    )


ACTION_CASES = (
    pytest.param(
        _extract_structure_action,
        CopyStructureOutput,
        id="extract-copy-structure",
    ),
    pytest.param(
        _extract_offer_action,
        OfferAnalysisOutput,
        id="extract-offer-elements",
    ),
    pytest.param(
        _analyse_persuasion_action,
        PersuasionAnalysisOutput,
        id="analyse-persuasion",
    ),
)


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


@pytest.mark.parametrize(("action_factory", "expected_schema"), ACTION_CASES)
def test_execute_uses_declared_structured_output_schema(
    action_factory: ActionFactory,
    expected_schema: type[BaseModel],
) -> None:
    """Every synchronous action should request and return its declared schema."""

    llm = RecordingLLM()
    action = action_factory(llm)

    result = action.execute()

    assert result is llm.last_response
    assert type(result) is expected_schema
    assert len(llm.calls) == 1
    assert llm.calls[0].mode == "sync"
    assert llm.calls[0].output_schema is expected_schema


@pytest.mark.parametrize(("action_factory", "expected_schema"), ACTION_CASES)
def test_aexecute_uses_declared_structured_output_schema(
    action_factory: ActionFactory,
    expected_schema: type[BaseModel],
) -> None:
    """Every asynchronous action should request and return its declared schema."""

    llm = RecordingLLM()
    action = action_factory(llm)

    result = asyncio.run(action.aexecute())

    assert result is llm.last_response
    assert type(result) is expected_schema
    assert len(llm.calls) == 1
    assert llm.calls[0].mode == "async"
    assert llm.calls[0].output_schema is expected_schema


@pytest.mark.parametrize(("action_factory", "expected_schema"), ACTION_CASES)
def test_action_renders_complete_prompt_and_exposes_tokens(
    action_factory: ActionFactory,
    expected_schema: type[BaseModel],
) -> None:
    """Rendered prompts must be complete and token usage must remain observable."""

    llm = RecordingLLM()
    action = action_factory(llm)

    action.execute()

    prompt = llm.calls[0].prompt
    unresolved_placeholder = re.search(r"\{[a-z_][a-z0-9_]*\}", prompt)
    assert unresolved_placeholder is None
    assert action.tokens_usage == {
        "input_tokens": INPUT_TOKENS,
        "output_tokens": OUTPUT_TOKENS,
        "total_tokens": INPUT_TOKENS + OUTPUT_TOKENS,
    }


@pytest.mark.parametrize(("action_factory", "expected_schema"), ACTION_CASES)
def test_sync_and_async_actions_render_equivalent_prompts(
    action_factory: ActionFactory,
    expected_schema: type[BaseModel],
) -> None:
    """Execution mode must not change the prompt or requested output contract."""

    sync_llm = RecordingLLM()
    async_llm = RecordingLLM()

    action_factory(sync_llm).execute()
    asyncio.run(action_factory(async_llm).aexecute())

    assert sync_llm.calls[0].prompt == async_llm.calls[0].prompt
    assert sync_llm.calls[0].output_schema is expected_schema
    assert async_llm.calls[0].output_schema is expected_schema


@pytest.mark.parametrize(("action_factory", "expected_schema"), ACTION_CASES)
def test_action_propagates_nonrecoverable_llm_failure_without_local_retry(
    action_factory: ActionFactory,
    expected_schema: type[BaseModel],
) -> None:
    """Actions must propagate provider failures without implementing another retry."""

    llm = RecordingLLM(failure=RuntimeError("Provider unavailable"))
    action = action_factory(llm)

    with pytest.raises(RuntimeError, match="Provider unavailable"):
        action.execute()

    assert len(llm.calls) == 1
    assert llm.calls[0].output_schema is expected_schema


def test_extract_copy_structure_serializes_transcript_context_by_tag() -> None:
    """Structure extraction should separate source text from timing metadata."""

    action = _extract_structure_action(RecordingLLM())
    prompt = action._build_prompt()

    assert _tag_content(prompt, "language") == action.language
    assert _tag_content(prompt, "clean_transcript") == action.clean_transcript
    assert _json_tag(prompt, "structured_transcription") == [
        segment.model_dump()
        for segment in action.structured_transcription
    ]


def test_extract_copy_structure_supports_empty_segments_without_retry_history() -> None:
    """Untimed transcription should render an empty segment list and no legacy state."""

    action = ExtractCopyStructure(
        llm=RecordingLLM(),
        clean_transcript="Una transcripción sin marcas de tiempo.",
        structured_transcription=[],
        language="Spanish",
    )
    prompt = action._build_prompt()

    assert _json_tag(prompt, "structured_transcription") == []
    assert "schema_validation_error_history" not in prompt
    assert "copy_structure_retry_count" not in prompt


def test_extract_offer_elements_serializes_structure_without_mutation() -> None:
    """Offer extraction should receive valid JSON without mutating prior analysis."""

    action = _extract_offer_action(RecordingLLM())
    structure_before = action.copy_structure.model_dump()
    prompt = action._build_prompt()

    assert _tag_content(prompt, "language") == action.language
    assert _tag_content(prompt, "clean_transcript") == action.clean_transcript
    assert _json_tag(prompt, "copy_structure") == structure_before
    assert action.copy_structure.model_dump() == structure_before


def test_analyse_persuasion_serializes_only_required_prior_analyses() -> None:
    """Persuasion analysis should consume structured context, not raw transcript text."""

    action = _analyse_persuasion_action(RecordingLLM())
    prompt = action._build_prompt()

    assert _tag_content(prompt, "language") == action.language
    assert _json_tag(prompt, "copy_structure") == action.copy_structure.model_dump()
    assert _json_tag(prompt, "offer_analysis") == action.offer_analysis.model_dump()
    assert "<clean_transcript>" not in prompt


def test_analyse_persuasion_preserves_unicode_json() -> None:
    """Prompt serialization should keep multilingual marketing text human-readable."""

    action = _analyse_persuasion_action(RecordingLLM())
    prompt = action._build_prompt()

    assert "educación financiera" in prompt
    assert "aspiración" in prompt
    assert "\\u00f3" not in prompt

