"""Contract tests for copy adaptation LLM actions.

The suite verifies the boundary between each action and ``LLMBase`` without
performing network requests. It protects output schemas, prompt context,
synchronous and asynchronous execution, retry inputs, and token visibility.
"""

import asyncio
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, cast

import pytest
from pydantic import BaseModel

from kyrg.llms.base import LLMBase, OutputT
from kyrg.workflows.base import AIActionBase
from kyrg.workflows.copyadaptation.actions import (
    BuildCopyStrategy,
    CorrectScriptSections,
    CorrectValidatedScript,
    ReviewAction,
    ValidateScriptAction,
    WriteScriptSection,
)
from kyrg.workflows.copyadaptation.schemas import (
    BuildCopyStrategyOutput,
    ReviewSectionFlowOutput,
    ScriptSectionOutput,
    UserProfileOutput,
    ValidationIssue,
    ValidateScriptOutput,
    WriteScriptSectionsOutput,
)
from kyrg.workflows.copyadaptation.system_prompt import CopyAdaptationSystemPrompts
from kyrg.workflows.copyanalysis.schemas import (
    CopyAnalysisOutput,
    CopySection,
    CopyStructureOutput,
    OfferAnalysisOutput,
    PersuasionAnalysisOutput,
)


INPUT_TOKENS = 17
OUTPUT_TOKENS = 9


@dataclass(frozen=True)
class StructuredCall:
    """Recorded structured-output call made by an action."""

    mode: Literal["sync", "async"]
    prompt: str
    system_prompt: str
    prompt_cache_key: str
    output_schema: type[BaseModel]


class RecordingLLM(LLMBase):
    """Deterministic LLM test double that records structured-output calls."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[StructuredCall] = []
        self.last_response: BaseModel | None = None

    def invoke(self, prompt: str) -> str:
        raise AssertionError("Copy adaptation actions must use structured output.")

    async def ainvoke(self, prompt: str) -> str:
        raise AssertionError("Copy adaptation actions must use structured output.")

    def _structured_once(
        self,
        prompt: str,
        system_prompt: str,
        prompt_cache_key: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        return self._record_structured_call(
            "sync",
            prompt,
            system_prompt,
            prompt_cache_key,
            output_schema,
        )

    async def _astructured_once(
        self,
        prompt: str,
        system_prompt: str,
        prompt_cache_key: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        return self._record_structured_call(
            "async",
            prompt,
            system_prompt,
            prompt_cache_key,
            output_schema,
        )

    def _record_structured_call(
        self,
        mode: Literal["sync", "async"],
        prompt: str,
        system_prompt: str,
        prompt_cache_key: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        response = _response_for(output_schema)
        self.calls.append(
            StructuredCall(
                mode=mode,
                prompt=prompt,
                system_prompt=system_prompt,
                prompt_cache_key=prompt_cache_key,
                output_schema=output_schema,
            )
        )
        self.last_response = response
        self._add_token(INPUT_TOKENS, OUTPUT_TOKENS)
        return response


ActionFactory = Callable[[RecordingLLM], AIActionBase]


EXPECTED_LLM_CONTEXT: dict[type[AIActionBase], tuple[str, str]] = {
    BuildCopyStrategy: (
        CopyAdaptationSystemPrompts.SYSTEM_PROMPT_BUILD_COPY_STRATEGY,
        "copy-adaptation:strategy",
    ),
    WriteScriptSection: (
        CopyAdaptationSystemPrompts.SYSTEM_PROMPT_WRITE_SCRIPT_SECTIONS,
        "copy-adaptation:write-sections",
    ),
    CorrectScriptSections: (
        CopyAdaptationSystemPrompts.SYSTEM_PROMPT_CORRECT_SCRIPT_SECTIONS,
        "copy-adaptation:correct-sections",
    ),
    CorrectValidatedScript: (
        CopyAdaptationSystemPrompts.SYSTEM_PROMPT_CORRECT_VALIDATED_SCRIPT,
        "copy-adaptation:correct-validated-script",
    ),
    ReviewAction: (
        CopyAdaptationSystemPrompts.SYSTEM_PROMPT_REVIEW_SECTION_FLOW,
        "copy-adaptation:review-flow",
    ),
    ValidateScriptAction: (
        CopyAdaptationSystemPrompts.SYSTEM_PROMPT_VALIDATE_SCRIPT,
        "copy-adaptation:validate-script",
    ),
}


def _assert_llm_context(action: AIActionBase, call: StructuredCall) -> None:
    """Assert that an action sends its stable system prompt and cache key."""

    expected_system_prompt, expected_cache_key = EXPECTED_LLM_CONTEXT[type(action)]
    assert call.system_prompt == expected_system_prompt
    assert call.prompt_cache_key == expected_cache_key


def _user_profile() -> UserProfileOutput:
    """Return a complete offer profile shared by action tests."""

    return UserProfileOutput(
        product_or_solution="A practical personal finance course",
        target_audience="Agronomists who want to invest their commissions",
        core_problem="They lack a reliable long-term investment plan",
        core_desire="Build a diversified portfolio for the future",
        main_promise="Learn to organize and invest commissions responsibly",
        unique_mechanism="Commission Organization Method",
        benefits=["A repeatable portfolio planning process"],
        objections=["I do not know where to start"],
        proof_assets=["Recorded curriculum demonstration"],
        offer_details="Online course with a waiting list",
        call_to_action="Join the course waiting list",
        tone="Clear and practical",
        target_language="English",
        platform="YouTube",
        desired_duration=2.5,
        restrictions=["Do not promise guaranteed financial returns"],
    )


def _copy_analysis() -> CopyAnalysisOutput:
    """Return a minimal validated analysis from the preceding workflow."""

    return CopyAnalysisOutput(
        language="English",
        copy_structure=CopyStructureOutput(
            language="English",
            content_type="VSL",
            main_hook="Your commission should support your future.",
            sections=[
                CopySection(
                    section_type="hook",
                    text="Your commission should support your future.",
                    purpose="Capture attention through a relevant aspiration.",
                    start=0.0,
                    end=4.0,
                )
            ],
            narrative_flow=["hook", "education", "offer"],
            section_gaps=[],
            summary="An educational VSL that moves from aspiration to offer.",
        ),
        offer_analysis=OfferAnalysisOutput(
            product_or_solution="A financial education course",
            summary="The offer teaches responsible long-term investing.",
        ),
        persuasion_analysis=PersuasionAnalysisOutput(
            dominant_emotion="confidence",
            persuasion_pattern="education-to-offer",
            hook_strength="medium",
            promise_clarity="high",
            proof_strength="medium",
            urgency_strength="low",
            cta_strength="medium",
            summary="The copy educates before presenting the solution.",
        ),
    )


def _mapped_sections() -> list[dict[str, Any]]:
    """Return normalized reference sections prepared for adaptation."""

    return [
        {
            "reference_section_type": "hook",
            "reference_text": "Your commission should support your future.",
            "reference_purpose": "Capture attention.",
            "has_direct_equivalent": True,
            "user_profile_fields": ["main_promise", "core_desire"],
        }
    ]


def _section() -> dict[str, Any]:
    """Return one validated script section represented as workflow state data."""

    return ScriptSectionOutput(
        order=1,
        section_type="hook",
        text="Your commission can support the future you are planning.",
        purpose="Capture attention through a relevant aspiration.",
        adaptation_mode="adapted_from_reference",
        source_reference_section_type="hook",
        proof_used=None,
        missing_proof=False,
        transition_hint="Connect the aspiration to the current problem.",
        pause_intent="medium",
    ).model_dump()


def _timing_metrics() -> dict[str, Any]:
    """Return deterministic timing context supplied to validation actions."""

    return {
        "word_count": 120,
        "speech_seconds": 48.0,
        "pause_seconds": 2.0,
        "total_seconds": 50.0,
        "estimated_duration_seconds": 50.0,
        "min_words": 140,
        "max_words": 160,
        "duration_status": "too_short",
    }


def _response_for(output_schema: type[OutputT]) -> OutputT:
    """Build a valid deterministic response for a requested action schema."""

    if output_schema is BuildCopyStrategyOutput:
        response = BuildCopyStrategyOutput(
            main_angle="Turn irregular commissions into a long-term plan",
            awareness_level="problem_aware",
            main_promise="Learn a responsible investment planning process",
            persuasion_pattern="education_to_offer",
            objections_to_address=["I do not know where to start"],
            proof_plan={"mechanism": "Use the curriculum demonstration"},
            unique_mechanism="Commission Organization Method",
            strategy_notes="Educate the audience before presenting the course.",
        )
        return cast(OutputT, response)

    if output_schema is WriteScriptSectionsOutput:
        response = WriteScriptSectionsOutput(
            sections=[ScriptSectionOutput.model_validate(_section())],
            missing_proofs=[],
            adaptation_notes="The reference hook was adapted to the new audience.",
        )
        return cast(OutputT, response)

    if output_schema is ReviewSectionFlowOutput:
        response = ReviewSectionFlowOutput(
            flow_approved=True,
            flow_issues=[],
            revision_instructions=[],
            sections_revised=[],
        )
        return cast(OutputT, response)

    if output_schema is ValidateScriptOutput:
        response = ValidateScriptOutput(
            validation_passed=True,
            validation_errors=[],
            validation_warnings=[],
        )
        return cast(OutputT, response)

    raise AssertionError(f"No fake response configured for {output_schema.__name__}.")


def _build_strategy_action(llm: RecordingLLM) -> BuildCopyStrategy:
    return BuildCopyStrategy(
        llm=llm,
        user_profile=_user_profile(),
        copy_analysis=_copy_analysis(),
        mapped_sections=_mapped_sections(),
        sections_to_create=["proof"],
        gaps_to_fix=["Weak section 'offer': The terms are unclear."],
        target_language="English",
        platform="YouTube",
        desired_duration=2.5,
    )


def _write_script_action(llm: RecordingLLM) -> WriteScriptSection:
    return WriteScriptSection(
        llm=llm,
        user_profile=_user_profile(),
        mapped_sections=_mapped_sections(),
        sections_to_create=["proof"],
        gaps_to_fix=["Weak section 'offer': The terms are unclear."],
        target_language="English",
        platform="YouTube",
        desired_duration=2.5,
        main_angle="Turn irregular commissions into a long-term plan",
        awareness_level="problem_aware",
        main_promise="Learn a responsible investment planning process",
        persuasion_pattern="education_to_offer",
        objections_to_address=["I do not know where to start"],
        proof_plan={"mechanism": "Use the curriculum demonstration"},
        unique_mechanism="Commission Organization Method",
    )


def _correct_sections_action(llm: RecordingLLM) -> CorrectScriptSections:
    return CorrectScriptSections(
        llm=llm,
        user_profile=_user_profile(),
        previous_sections=[_section()],
        flow_issues=["The hook does not transition into the problem."],
        revision_instructions=[
            {
                "section_order": 1,
                "section_type": "hook",
                "issue": "The transition is abrupt.",
                "action": "adjust_transition",
                "instruction": "Connect the aspiration to the planning problem.",
                "priority": "high",
            }
        ],
        missing_proofs=["proof"],
        target_language="English",
        platform="YouTube",
        desired_duration=2.5,
        main_angle="Turn irregular commissions into a long-term plan",
        awareness_level="problem_aware",
        main_promise="Learn a responsible investment planning process",
        persuasion_pattern="education_to_offer",
        objections_to_address=["I do not know where to start"],
        proof_plan={"mechanism": "Use the curriculum demonstration"},
        unique_mechanism="Commission Organization Method",
        retry_count=2,
    )


def _correct_validated_action(llm: RecordingLLM) -> CorrectValidatedScript:
    validation_error = ValidationIssue(
        category="claim",
        code="unsupported_return_guarantee",
        section_order=1,
        section_type="hook",
        field="text",
        message="The script contains an unsupported return guarantee.",
        correction_action="soften",
    )

    return CorrectValidatedScript(
        llm=llm,
        user_profile=_user_profile(),
        sections=[_section()],
        validation_errors=[validation_error.model_dump()],
        validation_warnings=["The script is shorter than the target duration."],
        timing_metrics=_timing_metrics(),
        missing_proofs=["proof"],
        target_language="English",
        platform="YouTube",
        desired_duration=2.5,
        main_angle="Turn irregular commissions into a long-term plan",
        main_promise="Learn a responsible investment planning process",
        proof_plan={"mechanism": "Use the curriculum demonstration"},
        unique_mechanism="Commission Organization Method",
        retry_count=1,
    )


def _review_action(llm: RecordingLLM) -> ReviewAction:
    return ReviewAction(
        llm=llm,
        sections=[_section()],
        missing_proofs=["proof"],
        target_language="English",
        platform="YouTube",
        desired_duration=2.5,
        main_angle="Turn irregular commissions into a long-term plan",
        awareness_level="problem_aware",
        main_promise="Learn a responsible investment planning process",
        persuasion_pattern="education_to_offer",
        objections_to_address=["I do not know where to start"],
        proof_plan={"mechanism": "Use the curriculum demonstration"},
        unique_mechanism="Commission Organization Method",
    )


def _validate_action(llm: RecordingLLM) -> ValidateScriptAction:
    return ValidateScriptAction(
        llm=llm,
        user_profile=_user_profile(),
        mapped_sections=_mapped_sections(),
        sections=[_section()],
        missing_proofs=["proof"],
        target_language="English",
        platform="YouTube",
        desired_duration=2.5,
        main_angle="Turn irregular commissions into a long-term plan",
        main_promise="Learn a responsible investment planning process",
        unique_mechanism="Commission Organization Method",
        proof_plan={"mechanism": "Use the curriculum demonstration"},
        timing_metrics=_timing_metrics(),
    )


ACTION_CASES = (
    pytest.param(
        _build_strategy_action,
        BuildCopyStrategyOutput,
        id="build-copy-strategy",
    ),
    pytest.param(
        _write_script_action,
        WriteScriptSectionsOutput,
        id="write-script-sections",
    ),
    pytest.param(
        _correct_sections_action,
        WriteScriptSectionsOutput,
        id="correct-script-sections",
    ),
    pytest.param(
        _correct_validated_action,
        WriteScriptSectionsOutput,
        id="correct-validated-script",
    ),
    pytest.param(
        _review_action,
        ReviewSectionFlowOutput,
        id="review-section-flow",
    ),
    pytest.param(
        _validate_action,
        ValidateScriptOutput,
        id="validate-script",
    ),
)


@pytest.mark.parametrize(("action_factory", "expected_schema"), ACTION_CASES)
def test_execute_uses_the_expected_structured_output_schema(
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
    _assert_llm_context(action, llm.calls[0])


@pytest.mark.parametrize(("action_factory", "expected_schema"), ACTION_CASES)
def test_aexecute_uses_the_expected_structured_output_schema(
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
    _assert_llm_context(action, llm.calls[0])


@pytest.mark.parametrize(("action_factory", "expected_schema"), ACTION_CASES)
def test_action_prompt_has_no_unresolved_placeholders_and_exposes_tokens(
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
def test_action_prompt_places_common_values_in_their_named_tags(
    action_factory: ActionFactory,
    expected_schema: type[BaseModel],
) -> None:
    """Common execution context should remain explicit and unambiguous."""

    llm = RecordingLLM()
    action = action_factory(llm)
    prompt = action._build_prompt()

    assert _tag_content(prompt, "target_language") == "English"
    assert _tag_content(prompt, "platform") == "YouTube"
    assert _tag_content(prompt, "desired_duration") == "2.5"


def test_build_strategy_prompt_serializes_reference_and_offer_context() -> None:
    """Strategy generation should receive readable JSON in the correct tags."""

    action = _build_strategy_action(RecordingLLM())
    prompt = action._build_prompt()

    assert _json_tag(
        prompt,
        "reference_copy_analysis",
    ) == action.copy_analysis.model_dump()
    assert _json_tag(prompt, "offer_profile") == action.user_profile.model_dump()
    assert _json_tag(prompt, "mapped_reference_sections") == action.mapped_sections
    assert _json_tag(prompt, "sections_create") == action.sections_to_create
    assert _json_tag(prompt, "gaps_to_fix") == action.gaps_to_fix


def test_write_prompt_serializes_strategy_and_section_inputs() -> None:
    """Initial writing should receive mapped sections and approved strategy data."""

    action = _write_script_action(RecordingLLM())
    prompt = action._build_prompt()

    assert _json_tag(prompt, "offer_profile") == action.user_profile.model_dump()
    assert _json_tag(prompt, "mapped_sections") == action.mapped_sections
    assert _json_tag(prompt, "sections_to_create") == action.sections_to_create
    assert _json_tag(prompt, "gaps_to_fix") == action.gaps_to_fix
    assert _json_tag(prompt, "objections_to_address") == action.objections_to_address
    assert _json_tag(prompt, "proof_plan") == action.proof_plan


def test_section_correction_prompt_contains_retry_state_and_review_feedback() -> None:
    """Flow correction should receive the prior version and actionable feedback."""

    action = _correct_sections_action(RecordingLLM())
    prompt = action._build_prompt()

    assert _tag_content(prompt, "retry_count") == "2"
    assert _json_tag(prompt, "previous_sections") == action.previous_sections
    assert _json_tag(prompt, "flow_issues") == action.flow_issues
    assert _json_tag(prompt, "revision_instructions") == action.revision_instructions
    assert _json_tag(prompt, "missing_proofs") == action.missing_proofs


def test_validated_correction_prompt_contains_real_validation_diagnostics() -> None:
    """Final correction should receive actual validator errors and timing metrics."""

    action = _correct_validated_action(RecordingLLM())
    prompt = action._build_prompt()

    assert _tag_content(prompt, "retry_count") == "1"
    assert _json_tag(prompt, "sections") == action.sections
    assert _json_tag(prompt, "validation_errors") == action.validation_errors
    assert _json_tag(prompt, "validation_warnings") == action.validation_warnings
    assert _json_tag(prompt, "timing_metrics") == action.timing_metrics
    assert _json_tag(prompt, "missing_proofs") == action.missing_proofs


def test_review_prompt_serializes_sections_and_proof_gaps() -> None:
    """Flow review should receive the written sections and known proof gaps."""

    action = _review_action(RecordingLLM())
    prompt = action._build_prompt()

    assert _json_tag(prompt, "sections") == action.sections
    assert _json_tag(prompt, "missing_proofs") == action.missing_proofs
    assert _json_tag(prompt, "objections_to_address") == action.objections_to_address
    assert _json_tag(prompt, "proof_plan") == action.proof_plan


def test_validation_prompt_serializes_source_sections_and_timing_metrics() -> None:
    """Final validation should receive source mappings, script, and measured timing."""

    action = _validate_action(RecordingLLM())
    prompt = action._build_prompt()

    assert _json_tag(prompt, "offer_profile") == action.user_profile.model_dump()
    assert _json_tag(prompt, "mapped_reference_sections") == action.mapped_sections
    assert _json_tag(prompt, "sections") == action.sections
    assert _json_tag(prompt, "missing_proofs") == action.missing_proofs
    assert _json_tag(prompt, "timing_metrics") == action.timing_metrics


def _tag_content(prompt: str, tag_name: str) -> str:
    """Extract and normalize text enclosed by a named XML-style prompt tag."""

    match = re.search(
        rf"<{tag_name}>\s*(.*?)\s*</{tag_name}>",
        prompt,
        flags=re.DOTALL,
    )
    assert match is not None, f"Prompt tag <{tag_name}> was not found."
    return match.group(1).strip()


def _json_tag(prompt: str, tag_name: str) -> Any:
    """Decode JSON enclosed by a named XML-style prompt tag."""

    return json.loads(_tag_content(prompt, tag_name))
