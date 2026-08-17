"""Contract tests for copy analysis workflow schemas.

These tests protect the structured boundaries shared by LLM actions, graph
state, checkpoints, and the downstream copy adaptation workflow.
"""

from dataclasses import FrozenInstanceError
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from kyrg.llms.base import LLMBase, OutputT
from kyrg.workflows.copyanalysis.schemas import (
    CopyAnalysisOutput,
    CopyAnalysisWorkflowContext,
    CopySection,
    CopyStructureOutput,
    OfferAnalysisOutput,
    OfferElement,
    PersuasionAnalysisOutput,
    PersuasionSignal,
    PersuasionWeakness,
    SectionGap,
    StructuredTranscript,
)


SECTION_TYPES = (
    "hook",
    "problem",
    "pain",
    "agitation",
    "promise",
    "mechanism",
    "proof",
    "story",
    "objection",
    "offer",
    "cta",
    "urgency",
    "scarcity",
    "transition",
    "education",
    "payoff",
)


class StubLLM(LLMBase):
    """Satisfy the context contract without performing model calls."""

    def invoke(self, prompt: str) -> str:
        raise AssertionError("Schema tests must not call an LLM.")

    async def ainvoke(self, prompt: str) -> str:
        raise AssertionError("Schema tests must not call an LLM.")

    def _structured_once(
        self,
        prompt: str,
        system_prompt: str,
        prompt_cache_key: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        raise AssertionError("Schema tests must not call an LLM.")

    async def _astructured_once(
        self,
        prompt: str,
        system_prompt: str,
        prompt_cache_key: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        raise AssertionError("Schema tests must not call an LLM.")


def _section_payload(
    *,
    section_type: str = "hook",
    text: str = "What if your monthly commission could fund your future?",
    purpose: str = "Capture attention through a relevant financial aspiration.",
    start: float | None = 0.0,
    end: float | None = 4.5,
) -> dict[str, Any]:
    """Return a complete copy section payload with configurable boundaries."""

    return {
        "section_type": section_type,
        "text": text,
        "purpose": purpose,
        "start": start,
        "end": end,
    }


def _gap_payload(
    *,
    section_type: str = "proof",
    gap_type: str = "missing",
) -> dict[str, Any]:
    """Return a complete structural gap payload."""

    return {
        "section_type": section_type,
        "gap_type": gap_type,
        "reason": "The transcription contains no evidence supporting the promise.",
    }


def _structure_payload() -> dict[str, Any]:
    """Return a representative structural analysis payload."""

    return {
        "language": "English",
        "content_type": "VSL",
        "main_hook": "Your commission can become a long-term plan.",
        "sections": [
            _section_payload(),
            _section_payload(
                section_type="problem",
                text="Irregular income makes long-term planning difficult.",
                purpose="Make the audience recognize the planning problem.",
                start=4.5,
                end=10.0,
            ),
            _section_payload(
                section_type="cta",
                text="Join the course waiting list.",
                purpose="Ask the viewer to register interest.",
                start=10.0,
                end=13.0,
            ),
        ],
        "narrative_flow": ["hook", "problem", "cta"],
        "section_gaps": [_gap_payload()],
        "summary": "The copy moves from aspiration to a planning problem and CTA.",
    }


def _offer_payload() -> dict[str, Any]:
    """Return a complete offer analysis grounded in explicit evidence."""

    return {
        "product_or_solution": "A practical personal finance course",
        "target_audience": "Agronomists with irregular commission income",
        "core_problem": "They do not know how to organize commissions for investing",
        "core_desire": "Build a diversified long-term portfolio",
        "main_promise": "Learn a responsible investment planning process",
        "unique_mechanism": "Commission Organization Method",
        "benefits": [
            {
                "name": "Financial organization",
                "description": "Separate commissions by financial objective.",
                "evidence": "The speaker describes organizing every commission.",
            }
        ],
        "objections": [
            {
                "name": "Lack of experience",
                "description": "The audience believes investing is too complex.",
                "evidence": "The narration addresses people who do not know where to start.",
            }
        ],
        "proof_elements": [],
        "bonuses": [],
        "urgency_or_scarcity": [],
        "call_to_action": "Join the course waiting list",
        "price_or_terms": None,
        "summary": "The offer teaches agronomists to organize and invest commissions.",
    }


def _persuasion_payload() -> dict[str, Any]:
    """Return a complete persuasion diagnosis with supporting evidence."""

    return {
        "dominant_emotion": "aspiration",
        "persuasion_pattern": "education-to-offer",
        "hook_strength": "high",
        "promise_clarity": "high",
        "proof_strength": "low",
        "urgency_strength": "low",
        "cta_strength": "medium",
        "persuasion_signals": [
            {
                "name": "future pacing",
                "description": "The opening invites the audience to imagine financial security.",
                "evidence": "Your commission can become a long-term plan.",
                "strength": "high",
            }
        ],
        "weaknesses": [
            {
                "issue": "No concrete proof is presented.",
                "impact": "The promise may feel less credible.",
                "evidence": None,
            }
        ],
        "summary": "The copy uses aspiration and education but has weak proof.",
    }


def _assert_missing_field(
    model: type[BaseModel],
    payload: dict[str, Any],
    field_name: str,
) -> None:
    """Assert that a required schema field produces a precise missing error."""

    payload.pop(field_name)

    with pytest.raises(ValidationError) as captured_error:
        model.model_validate(payload)

    assert any(
        error["type"] == "missing" and error["loc"] == (field_name,)
        for error in captured_error.value.errors()
    )


def test_structured_transcript_accepts_complete_timestamps() -> None:
    """A transcript segment should preserve text and temporal boundaries."""

    segment = StructuredTranscript(start=1.25, end=3.75, text="Invest with a plan.")

    assert segment.start == 1.25
    assert segment.end == 3.75
    assert segment.text == "Invest with a plan."


def test_structured_transcript_accepts_null_timestamps_and_round_trips() -> None:
    """Providers without timestamps should still produce serializable segments."""

    original = StructuredTranscript(text="Invest with a plan.")
    restored = StructuredTranscript.model_validate_json(original.model_dump_json())

    assert original.start is None
    assert original.end is None
    assert restored == original


def test_structured_transcript_rejects_missing_text() -> None:
    """A segment without spoken text must fail at the schema boundary."""

    _assert_missing_field(
        StructuredTranscript,
        {"start": 0.0, "end": 1.0, "text": "Required text."},
        "text",
    )


@pytest.mark.parametrize("section_type", SECTION_TYPES)
def test_copy_section_accepts_every_canonical_section_type(section_type: str) -> None:
    """Every shared canonical section type should be valid for copy analysis."""

    section = CopySection.model_validate(_section_payload(section_type=section_type))

    assert section.section_type == section_type


def test_copy_section_rejects_noncanonical_section_type() -> None:
    """Unregistered classifications must not silently enter downstream workflows."""

    with pytest.raises(ValidationError) as captured_error:
        CopySection.model_validate(_section_payload(section_type="authority"))

    assert captured_error.value.errors()[0]["loc"] == ("section_type",)
    assert captured_error.value.errors()[0]["type"] == "literal_error"


def test_copy_section_preserves_content_and_accepts_missing_timestamps() -> None:
    """A valid section should retain its content even without timing evidence."""

    payload = _section_payload(start=None, end=None)
    section = CopySection.model_validate(payload)

    assert section.text == payload["text"]
    assert section.purpose == payload["purpose"]
    assert section.start is None
    assert section.end is None


@pytest.mark.parametrize("gap_type", ("missing", "incomplete", "weak"))
def test_section_gap_accepts_supported_gap_types(gap_type: str) -> None:
    """Structural diagnostics should distinguish every supported gap condition."""

    gap = SectionGap.model_validate(_gap_payload(gap_type=gap_type))

    assert gap.gap_type == gap_type


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    (
        ("gap_type", "invalid"),
        ("section_type", "authority"),
    ),
)
def test_section_gap_rejects_invalid_classifications(
    field_name: str,
    invalid_value: str,
) -> None:
    """Gap classifications must remain compatible with downstream routing logic."""

    payload = _gap_payload()
    payload[field_name] = invalid_value

    with pytest.raises(ValidationError) as captured_error:
        SectionGap.model_validate(payload)

    assert any(
        error["type"] == "literal_error" and error["loc"] == (field_name,)
        for error in captured_error.value.errors()
    )


def test_section_gap_requires_reason_and_round_trips() -> None:
    """Every structural gap must remain explainable and checkpoint-safe."""

    _assert_missing_field(SectionGap, _gap_payload(), "reason")

    original = SectionGap.model_validate(_gap_payload(gap_type="weak"))
    restored = SectionGap.model_validate_json(original.model_dump_json())

    assert restored == original


def test_copy_structure_accepts_complete_payload_and_preserves_order() -> None:
    """Structural output should preserve the original persuasive sequence."""

    structure = CopyStructureOutput.model_validate(_structure_payload())

    assert [section.section_type for section in structure.sections] == [
        "hook",
        "problem",
        "cta",
    ]
    assert structure.section_gaps[0].section_type == "proof"


def test_copy_structure_accepts_optional_language_and_hook() -> None:
    """Analysis should remain valid when detection cannot identify language or hook."""

    payload = _structure_payload()
    payload["language"] = None
    payload["main_hook"] = None

    structure = CopyStructureOutput.model_validate(payload)

    assert structure.language is None
    assert structure.main_hook is None


def test_copy_structure_default_lists_are_not_shared() -> None:
    """Mutable structural defaults must remain isolated between model instances."""

    first = CopyStructureOutput(content_type="VSL", summary="First analysis.")
    second = CopyStructureOutput(content_type="VSL", summary="Second analysis.")

    first.sections.append(CopySection.model_validate(_section_payload()))
    first.narrative_flow.append("hook")
    first.section_gaps.append(SectionGap.model_validate(_gap_payload()))

    assert second.sections == []
    assert second.narrative_flow == []
    assert second.section_gaps == []


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    (
        ("sections", [_section_payload(section_type="authority")]),
        ("section_gaps", [_gap_payload(section_type="authority")]),
    ),
)
def test_copy_structure_rejects_invalid_nested_classifications(
    field_name: str,
    invalid_value: list[dict[str, Any]],
) -> None:
    """Invalid nested section types must fail before entering graph state."""

    payload = _structure_payload()
    payload[field_name] = invalid_value

    with pytest.raises(ValidationError) as captured_error:
        CopyStructureOutput.model_validate(payload)

    assert captured_error.value.errors()[0]["loc"][0] == field_name


def test_copy_structure_round_trips_through_json() -> None:
    """Complete structural analysis should serialize without losing nested models."""

    original = CopyStructureOutput.model_validate(_structure_payload())
    restored = CopyStructureOutput.model_validate_json(original.model_dump_json())

    assert restored == original
    assert isinstance(restored.sections[0], CopySection)
    assert isinstance(restored.section_gaps[0], SectionGap)


def test_offer_analysis_accepts_complete_grounded_payload() -> None:
    """A complete offer analysis should retain facts and their supporting evidence."""

    offer = OfferAnalysisOutput.model_validate(_offer_payload())

    assert offer.product_or_solution == "A practical personal finance course"
    assert offer.benefits[0].evidence is not None
    assert offer.objections[0].name == "Lack of experience"
    assert offer.proof_elements == []


def test_offer_analysis_accepts_partial_offer_with_empty_defaults() -> None:
    """Content without a commercial offer should use nulls and empty collections."""

    offer = OfferAnalysisOutput(summary="No commercial offer is present.")

    assert offer.product_or_solution is None
    assert offer.call_to_action is None
    assert offer.price_or_terms is None
    assert offer.benefits == []
    assert offer.objections == []
    assert offer.proof_elements == []
    assert offer.bonuses == []
    assert offer.urgency_or_scarcity == []


def test_offer_analysis_default_lists_are_not_shared() -> None:
    """Offer collections must not leak extracted elements across analyses."""

    first = OfferAnalysisOutput(summary="First offer.")
    second = OfferAnalysisOutput(summary="Second offer.")

    first.benefits.append(
        OfferElement(name="Benefit", description="A grounded benefit.")
    )
    first.objections.append(
        OfferElement(name="Objection", description="A grounded objection.")
    )

    assert second.benefits == []
    assert second.objections == []


def test_offer_analysis_round_trips_through_json() -> None:
    """Offer analysis must remain stable across checkpoint serialization."""

    original = OfferAnalysisOutput.model_validate(_offer_payload())
    restored = OfferAnalysisOutput.model_validate_json(original.model_dump_json())

    assert restored == original
    assert isinstance(restored.benefits[0], OfferElement)


def test_persuasion_analysis_accepts_complete_grounded_payload() -> None:
    """Persuasion output should preserve signals, weaknesses, and evidence."""

    analysis = PersuasionAnalysisOutput.model_validate(_persuasion_payload())

    assert analysis.dominant_emotion == "aspiration"
    assert analysis.hook_strength == "high"
    assert analysis.persuasion_signals[0].evidence is not None
    assert analysis.weaknesses[0].issue == "No concrete proof is presented."


def test_persuasion_analysis_accepts_optional_fields_and_empty_defaults() -> None:
    """A sparse diagnosis should remain valid when optional signals are unavailable."""

    analysis = PersuasionAnalysisOutput(summary="No persuasive pattern detected.")

    assert analysis.dominant_emotion is None
    assert analysis.persuasion_pattern is None
    assert analysis.hook_strength is None
    assert analysis.persuasion_signals == []
    assert analysis.weaknesses == []


def test_persuasion_analysis_default_lists_are_not_shared() -> None:
    """Persuasion collections must remain isolated between workflow executions."""

    first = PersuasionAnalysisOutput(summary="First diagnosis.")
    second = PersuasionAnalysisOutput(summary="Second diagnosis.")

    first.persuasion_signals.append(
        PersuasionSignal(
            name="Curiosity",
            description="The hook opens an information gap.",
            strength="high",
        )
    )
    first.weaknesses.append(
        PersuasionWeakness(
            issue="Weak proof",
            impact="The promise may feel less credible.",
        )
    )

    assert second.persuasion_signals == []
    assert second.weaknesses == []


@pytest.mark.parametrize("strength", ("low", "medium", "high"))
def test_persuasion_analysis_preserves_conventional_strength_values(
    strength: str,
) -> None:
    """Conventional strength values should pass unchanged through the schema."""

    payload = _persuasion_payload()
    payload["hook_strength"] = strength

    analysis = PersuasionAnalysisOutput.model_validate(payload)

    assert analysis.hook_strength == strength


def test_persuasion_analysis_round_trips_through_json() -> None:
    """Persuasion diagnosis should retain nested evidence after serialization."""

    original = PersuasionAnalysisOutput.model_validate(_persuasion_payload())
    restored = PersuasionAnalysisOutput.model_validate_json(
        original.model_dump_json()
    )

    assert restored == original
    assert isinstance(restored.persuasion_signals[0], PersuasionSignal)
    assert isinstance(restored.weaknesses[0], PersuasionWeakness)


def test_copy_analysis_consolidates_all_outputs_with_nullable_language() -> None:
    """The final schema should combine all analyses without requiring language."""

    analysis = CopyAnalysisOutput(
        language=None,
        copy_structure=CopyStructureOutput.model_validate(_structure_payload()),
        offer_analysis=OfferAnalysisOutput.model_validate(_offer_payload()),
        persuasion_analysis=PersuasionAnalysisOutput.model_validate(
            _persuasion_payload()
        ),
    )

    assert analysis.language is None
    assert analysis.copy_structure.content_type == "VSL"
    assert analysis.offer_analysis.call_to_action == "Join the course waiting list"
    assert analysis.persuasion_analysis.proof_strength == "low"


@pytest.mark.parametrize(
    "missing_field",
    ("copy_structure", "offer_analysis", "persuasion_analysis"),
)
def test_copy_analysis_rejects_missing_required_analysis(
    missing_field: str,
) -> None:
    """The consolidated output must never expose a partially completed analysis."""

    payload = {
        "language": "English",
        "copy_structure": _structure_payload(),
        "offer_analysis": _offer_payload(),
        "persuasion_analysis": _persuasion_payload(),
    }

    _assert_missing_field(CopyAnalysisOutput, payload, missing_field)


def test_copy_analysis_round_trips_through_json() -> None:
    """The public analysis contract should survive JSON persistence intact."""

    original = CopyAnalysisOutput(
        language="English",
        copy_structure=CopyStructureOutput.model_validate(_structure_payload()),
        offer_analysis=OfferAnalysisOutput.model_validate(_offer_payload()),
        persuasion_analysis=PersuasionAnalysisOutput.model_validate(
            _persuasion_payload()
        ),
    )
    restored = CopyAnalysisOutput.model_validate_json(original.model_dump_json())

    assert restored == original
    assert isinstance(restored.copy_structure, CopyStructureOutput)
    assert isinstance(restored.offer_analysis, OfferAnalysisOutput)
    assert isinstance(restored.persuasion_analysis, PersuasionAnalysisOutput)


def test_workflow_context_requires_and_preserves_llm_dependency() -> None:
    """Workflow context should require one explicit LLM dependency by construction."""

    with pytest.raises(TypeError):
        CopyAnalysisWorkflowContext()  # type: ignore[call-arg]

    llm = StubLLM()
    context = CopyAnalysisWorkflowContext(analysis_llm=llm)

    assert context.analysis_llm is llm


def test_workflow_context_is_frozen_and_has_no_graph_retry_configuration() -> None:
    """Context must remain immutable and free of the removed graph retry policy."""

    context = CopyAnalysisWorkflowContext(analysis_llm=StubLLM())

    assert not hasattr(context, "max_retry_errors")

    with pytest.raises(FrozenInstanceError):
        context.analysis_llm = StubLLM()  # type: ignore[misc]
