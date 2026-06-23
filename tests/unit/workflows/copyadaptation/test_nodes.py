"""Unit tests for copy adaptation workflow nodes.

The tests exercise node-level state transformations with deterministic LLM
doubles. They deliberately exclude graph routing, which has its own test module.
"""

from typing import Any, cast

import pytest
from pydantic import BaseModel

from kyrg.llms.base import LLMBase, OutputT
from kyrg.workflows.copyadaptation.nodes import (
    build_copy_strategy,
    build_script_output,
    correct_script,
    correct_section,
    prepare_adaptation_input,
    review_section_flow,
    validate_script,
    write_script_sections,
)
from kyrg.workflows.copyadaptation.schemas import (
    BuildCopyStrategyOutput,
    CopyAdaptationWorkflowContext,
    ReviewSectionFlowOutput,
    ScriptSectionOutput,
    SectionRevisionInstruction,
    UserProfileOutput,
    ValidateScriptOutput,
    WriteScriptSectionsOutput,
)
from kyrg.workflows.copyadaptation.state import CopyAdaptationState
from kyrg.workflows.copyanalysis.schemas import (
    CopyAnalysisOutput,
    CopySection,
    CopyStructureOutput,
    OfferAnalysisOutput,
    PersuasionAnalysisOutput,
    PersuasionWeakness,
    SectionGap,
)
from kyrg.workflows.core import WorkflowRuntime


INPUT_TOKENS = 13
OUTPUT_TOKENS = 5
TOKEN_OUTPUT = {
    "input_tokens": INPUT_TOKENS,
    "output_tokens": OUTPUT_TOKENS,
    "total_tokens": INPUT_TOKENS + OUTPUT_TOKENS,
}


class StaticLLM(LLMBase):
    """Return configured Pydantic responses and record every generated prompt."""

    def __init__(self, responses: dict[type[BaseModel], BaseModel]) -> None:
        super().__init__()
        self.responses = responses
        self.prompts: list[str] = []

    def invoke(self, prompt: str) -> str:
        raise AssertionError("Copy adaptation nodes must use structured output.")

    async def ainvoke(self, prompt: str) -> str:
        raise AssertionError("Copy adaptation nodes must use structured output.")

    def structured(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        return self._respond(prompt, output_schema)

    async def astructured(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        return self._respond(prompt, output_schema)

    def _respond(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        self.prompts.append(prompt)
        self._add_token(INPUT_TOKENS, OUTPUT_TOKENS)

        try:
            response = self.responses[output_schema]
        except KeyError as error:
            raise AssertionError(
                f"No response configured for {output_schema.__name__}."
            ) from error

        assert type(response) is output_schema
        return cast(OutputT, response)


def _user_profile(
    *,
    target_language: str | None = "English",
    proof_assets: list[str] | None = None,
    unique_mechanism: str | None = "Commission Organization Method",
) -> UserProfileOutput:
    """Build a complete user profile with configurable adaptation constraints."""

    return UserProfileOutput(
        product_or_solution="A practical personal finance course",
        target_audience="Agronomists who want to invest their commissions",
        core_problem="They lack a reliable long-term investment plan",
        core_desire="Build a diversified portfolio for the future",
        main_promise="Learn to organize and invest commissions responsibly",
        unique_mechanism=unique_mechanism,
        benefits=["A repeatable portfolio planning process"],
        objections=["I do not know where to start"],
        proof_assets=(
            ["Recorded curriculum demonstration"]
            if proof_assets is None
            else proof_assets
        ),
        offer_details="Online course with a waiting list",
        call_to_action="Join the course waiting list",
        tone="Clear and practical",
        target_language=target_language,
        platform="YouTube",
        desired_duration=2.5,
        restrictions=["Do not promise guaranteed financial returns"],
    )


def _copy_analysis(
    *,
    analysis_language: str | None = "English",
    structure_language: str | None = "English",
    section_gaps: list[SectionGap] | None = None,
    weaknesses: list[PersuasionWeakness] | None = None,
    hook_strength: str = "high",
    promise_clarity: str = "high",
    proof_strength: str = "high",
    urgency_strength: str = "high",
    cta_strength: str = "high",
) -> CopyAnalysisOutput:
    """Build a validated reference analysis for node tests."""

    return CopyAnalysisOutput(
        language=analysis_language,
        copy_structure=CopyStructureOutput(
            language=structure_language,
            content_type="VSL",
            main_hook="Your commission should support your future.",
            sections=[
                CopySection(
                    section_type="hook",
                    text="Your commission should support your future.",
                    purpose="Capture attention through a relevant aspiration.",
                    start=0.0,
                    end=4.0,
                ),
                CopySection(
                    section_type="offer",
                    text="Learn a process for organizing your investments.",
                    purpose="Present the educational solution.",
                    start=4.0,
                    end=9.0,
                ),
            ],
            narrative_flow=["hook", "offer"],
            section_gaps=[] if section_gaps is None else section_gaps,
            summary="A short educational VSL that moves from aspiration to offer.",
        ),
        offer_analysis=OfferAnalysisOutput(
            product_or_solution="A financial education course",
            summary="The offer teaches responsible long-term investing.",
        ),
        persuasion_analysis=PersuasionAnalysisOutput(
            dominant_emotion="confidence",
            persuasion_pattern="education-to-offer",
            hook_strength=hook_strength,
            promise_clarity=promise_clarity,
            proof_strength=proof_strength,
            urgency_strength=urgency_strength,
            cta_strength=cta_strength,
            weaknesses=[] if weaknesses is None else weaknesses,
            summary="The copy educates before presenting the solution.",
        ),
    )


def _section(
    *,
    order: int = 1,
    section_type: str = "hook",
    text: str = "Your commission can support the future you are planning.",
    pause_intent: str = "medium",
) -> dict[str, Any]:
    """Build a validated section represented as workflow state data."""

    return ScriptSectionOutput.model_validate(
        {
            "order": order,
            "section_type": section_type,
            "text": text,
            "purpose": f"Serve the {section_type} role in the script.",
            "adaptation_mode": "adapted_from_reference",
            "source_reference_section_type": section_type,
            "proof_used": None,
            "missing_proof": False,
            "transition_hint": "Continue to the next persuasive beat.",
            "pause_intent": pause_intent,
        }
    ).model_dump()


def _strategy_output() -> BuildCopyStrategyOutput:
    return BuildCopyStrategyOutput(
        main_angle="Turn irregular commissions into a long-term plan",
        awareness_level="problem_aware",
        main_promise="Learn a responsible investment planning process",
        persuasion_pattern="education_to_offer",
        objections_to_address=["I do not know where to start"],
        proof_plan={"mechanism": "Use the curriculum demonstration"},
        unique_mechanism="Commission Organization Method",
        strategy_notes="Educate the audience before presenting the course.",
    )


def _written_output(
    *,
    sections: list[dict[str, Any]] | None = None,
    notes: str = "The reference structure was adapted to the new offer.",
) -> WriteScriptSectionsOutput:
    return WriteScriptSectionsOutput(
        sections=[
            ScriptSectionOutput.model_validate(section)
            for section in (sections or [_section()])
        ],
        missing_proofs=[],
        adaptation_notes=notes,
    )


def _review_output() -> ReviewSectionFlowOutput:
    return ReviewSectionFlowOutput(
        flow_approved=False,
        flow_issues=["The hook does not transition into the offer."],
        revision_instructions=[
            SectionRevisionInstruction(
                section_order=1,
                section_type="hook",
                issue="The transition is abrupt.",
                action="adjust_transition",
                instruction="Connect the aspiration to the planning problem.",
                priority="high",
            )
        ],
        sections_revised=[
            ScriptSectionOutput.model_validate(
                _section(text="Reviewed hook with a clearer transition.")
            )
        ],
    )


def _validation_output() -> ValidateScriptOutput:
    return ValidateScriptOutput(
        validation_passed=False,
        validation_errors=["The script contains an unsupported claim."],
        validation_warnings=["The script is shorter than the target duration."],
    )


def _base_state() -> CopyAdaptationState:
    """Return state containing every dependency shared by downstream nodes."""

    return {
        "copy_analysis": _copy_analysis(),
        "user_profile": _user_profile(),
        "mapped_sections": [],
        "sections_to_create": ["proof"],
        "gaps_to_fix": ["weak section 'offer': The terms are unclear."],
        "target_language": "English",
        "platform": "YouTube",
        "desired_duration": 2.5,
        "main_angle": "Turn irregular commissions into a long-term plan",
        "awareness_level": "problem_aware",
        "main_promise": "Learn a responsible investment planning process",
        "persuasion_pattern": "education_to_offer",
        "objections_to_address": ["I do not know where to start"],
        "proof_plan": {"mechanism": "Use the curriculum demonstration"},
        "unique_mechanism": "Commission Organization Method",
        "sections": [
            _section(text="Original hook."),
            _section(
                order=2,
                section_type="cta",
                text="Join the course waiting list.",
                pause_intent="short",
            ),
        ],
        "missing_proofs": [],
        "adaptation_notes": "The reference structure was adapted.",
        "flow_issues": ["The hook does not transition into the offer."],
        "revision_instructions": [
            {
                "section_order": 1,
                "section_type": "hook",
                "issue": "The transition is abrupt.",
                "action": "adjust_transition",
                "instruction": "Connect the aspiration to the planning problem.",
                "priority": "high",
            }
        ],
        "validation_errors": ["The script contains an unsupported claim."],
        "validation_warnings": [],
    }


def _runtime(
    *,
    strategy_response: BuildCopyStrategyOutput | None = None,
    writing_response: WriteScriptSectionsOutput | None = None,
    review_response: ReviewSectionFlowOutput | None = None,
    validation_response: ValidateScriptOutput | None = None,
) -> tuple[
    WorkflowRuntime[CopyAdaptationWorkflowContext],
    dict[str, StaticLLM],
]:
    """Build a workflow runtime and expose its role-specific LLM doubles."""

    llms = {
        "strategy": StaticLLM(
            {BuildCopyStrategyOutput: strategy_response or _strategy_output()}
        ),
        "writing": StaticLLM(
            {WriteScriptSectionsOutput: writing_response or _written_output()}
        ),
        "review": StaticLLM(
            {ReviewSectionFlowOutput: review_response or _review_output()}
        ),
        "validation": StaticLLM(
            {ValidateScriptOutput: validation_response or _validation_output()}
        ),
    }
    context = CopyAdaptationWorkflowContext(
        strategy_llm=llms["strategy"],
        writing_llm=llms["writing"],
        review_llm=llms["review"],
        validation_llm=llms["validation"],
        max_retry=2,
    )
    return WorkflowRuntime(context=context), llms


def _assert_token_output(output: dict[str, Any]) -> None:
    """Assert the standard token fields emitted by LLM-backed nodes."""

    for key, value in TOKEN_OUTPUT.items():
        assert output[key] == value


def test_prepare_adaptation_input_maps_sections_and_classifies_gaps() -> None:
    """Preparation should separate missing sections from correctable weaknesses."""

    gaps = [
        SectionGap(
            section_type="proof",
            gap_type="missing",
            reason="No evidence is presented.",
        ),
        SectionGap(
            section_type="proof",
            gap_type="missing",
            reason="The proof section is absent.",
        ),
        SectionGap(
            section_type="offer",
            gap_type="weak",
            reason="The terms are unclear.",
        ),
        SectionGap(
            section_type="cta",
            gap_type="incomplete",
            reason="The requested action is vague.",
        ),
    ]
    state: CopyAdaptationState = {
        "copy_analysis": _copy_analysis(section_gaps=gaps),
        "user_profile": _user_profile(),
    }

    output = prepare_adaptation_input(state)

    assert output["sections_to_create"] == ["proof"]
    assert output["gaps_to_fix"] == [
        "weak section 'offer': The terms are unclear.",
        "incomplete section 'cta': The requested action is vague.",
    ]
    assert output["mapped_sections"][0] == {
        "reference_section_type": "hook",
        "reference_text": "Your commission should support your future.",
        "reference_purpose": "Capture attention through a relevant aspiration.",
        "start": 0.0,
        "end": 4.0,
        "has_direct_equivalent": True,
        "user_profile_fields": ["main_promise", "core_problem", "core_desire"],
    }


def test_prepare_adaptation_input_adds_persuasion_and_profile_gaps_once() -> None:
    """Preparation should preserve actionable diagnostics without duplicates."""

    repeated_issue = "The offer lacks a concrete next step."
    analysis = _copy_analysis(
        proof_strength="low",
        cta_strength="low",
        weaknesses=[
            PersuasionWeakness(
                issue=repeated_issue,
                impact="The viewer may not know how to continue.",
            ),
            PersuasionWeakness(
                issue=repeated_issue,
                impact="The viewer may not know how to continue.",
            ),
        ],
    )
    profile = _user_profile(proof_assets=[], unique_mechanism=None)

    state: CopyAdaptationState = {
        "copy_analysis": analysis,
        "user_profile": profile,
    }

    output = prepare_adaptation_input(state)

    assert output["gaps_to_fix"] == [
        "Low persuasion score: proof_strength",
        "Low persuasion score: cta_strength",
        repeated_issue,
        "User profile has no proof assets available",
        "User profile has no unique mechanism defined",
    ]


@pytest.mark.parametrize(
    ("profile_language", "analysis_language", "structure_language", "expected"),
    (
        ("Portuguese", "Spanish", "English", "Portuguese"),
        (None, "Spanish", "English", "Spanish"),
        (None, None, "English", "English"),
    ),
)
def test_prepare_adaptation_input_uses_language_precedence(
    profile_language: str | None,
    analysis_language: str | None,
    structure_language: str | None,
    expected: str,
) -> None:
    """Target language should follow profile, analysis, then structure priority."""

    state: CopyAdaptationState = {
        "copy_analysis": _copy_analysis(
            analysis_language=analysis_language,
            structure_language=structure_language,
        ),
        "user_profile": _user_profile(target_language=profile_language),
    }

    output = prepare_adaptation_input(state)

    assert output["target_language"] == expected


@pytest.mark.parametrize(
    ("state", "message"),
    (
        ({"user_profile": _user_profile()}, "copy_analysis is required"),
        ({"copy_analysis": _copy_analysis()}, "user_profile is required"),
        (
            {
                "copy_analysis": _copy_analysis(
                    analysis_language=None,
                    structure_language=None,
                ),
                "user_profile": _user_profile(target_language=None),
            },
            "target_language is required",
        ),
    ),
)
def test_prepare_adaptation_input_rejects_missing_dependencies(
    state: dict[str, Any],
    message: str,
) -> None:
    """Preparation should fail immediately when its required inputs are absent."""

    with pytest.raises(ValueError, match=message):
        prepare_adaptation_input(cast(CopyAdaptationState, state))


def test_build_copy_strategy_returns_only_strategy_and_token_fields() -> None:
    """Strategy node output should not leak action-only fields into workflow state."""

    runtime, _ = _runtime()
    state = _base_state()

    output = build_copy_strategy(state, runtime)

    assert output == {
        "main_angle": "Turn irregular commissions into a long-term plan",
        "awareness_level": "problem_aware",
        "main_promise": "Learn a responsible investment planning process",
        "persuasion_pattern": "education_to_offer",
        "objections_to_address": ["I do not know where to start"],
        "proof_plan": {"mechanism": "Use the curriculum demonstration"},
        "unique_mechanism": "Commission Organization Method",
        **TOKEN_OUTPUT,
    }


def test_write_script_sections_calculates_word_counts_deterministically() -> None:
    """Writing node should derive section and total word counts from generated text."""

    generated_sections = [
        _section(text="Three simple words"),
        _section(order=2, section_type="cta", text="Join the list today"),
    ]
    runtime, _ = _runtime(
        writing_response=_written_output(sections=generated_sections)
    )

    output = write_script_sections(_base_state(), runtime)

    assert [section["word_count"] for section in output["sections"]] == [3, 4]
    assert output["word_count"] == 7
    assert output["missing_proofs"] == []
    _assert_token_output(output)


def test_review_section_flow_converts_nested_models_to_state_dictionaries() -> None:
    """Review node should emit checkpoint-safe dictionaries for nested outputs."""

    runtime, _ = _runtime()

    output = review_section_flow(_base_state(), runtime)

    assert output["flow_approved"] is False
    assert output["flow_issues"] == [
        "The hook does not transition into the offer."
    ]
    assert output["revision_instructions"][0]["action"] == "adjust_transition"
    assert output["sections_revised"][0]["text"] == (
        "Reviewed hook with a clearer transition."
    )
    assert isinstance(output["revision_instructions"][0], dict)
    assert isinstance(output["sections_revised"][0], dict)
    _assert_token_output(output)


def test_correct_section_uses_resolved_sections_and_increments_only_its_retry() -> None:
    """Flow correction should consume reviewed sections and clear stale revisions."""

    corrected = _written_output(
        sections=[_section(text="Corrected hook with a natural transition.")]
    )
    runtime, llms = _runtime(writing_response=corrected)
    state = _base_state()
    state["sections_revised"] = [
        _section(text="Reviewed hook selected as correction input.")
    ]
    state["retry_count_correction_section"] = 2
    state["retry_count_correction_script"] = 7

    output = correct_section(state, runtime)

    assert "Reviewed hook selected as correction input." in llms["writing"].prompts[0]
    assert "Original hook." not in llms["writing"].prompts[0]
    assert output["sections"][0]["text"] == (
        "Corrected hook with a natural transition."
    )
    assert output["retry_count_correction_section"] == 3
    assert "retry_count_correction_script" not in output
    assert output["sections_revised"] == []
    _assert_token_output(output)


def test_validate_script_uses_deterministic_timing_metrics() -> None:
    """Validation node should expose and send code-generated timing diagnostics."""

    runtime, llms = _runtime()

    output = validate_script(_base_state(), runtime)

    assert output["validation_passed"] is False
    assert output["timing_metrics"]["word_count"] == 7
    assert output["timing_metrics"]["duration_status"] == "too_short"
    assert output["timing_metrics"]["pause_seconds"] > 0
    assert '"duration_status": "too_short"' in llms["validation"].prompts[0]
    _assert_token_output(output)


def test_correct_script_replaces_resolved_sections_and_clears_stale_revisions() -> None:
    """Validation correction should replace the current version and isolate its retry."""

    corrected = _written_output(
        sections=[_section(text="Corrected script without the unsupported claim.")]
    )
    runtime, _ = _runtime(writing_response=corrected)
    state = _base_state()
    state["sections_revised"] = [
        _section(text="Reviewed script used as validation correction input.")
    ]
    state["retry_count_correction_section"] = 4
    state["retry_count_correction_script"] = 1

    output = correct_script(state, runtime)

    assert output["sections_before_script_correction"][0]["text"] == (
        "Reviewed script used as validation correction input."
    )
    assert output["sections_after_script_correction"][0]["text"] == (
        "Corrected script without the unsupported claim."
    )
    assert output["sections"] == output["sections_after_script_correction"]
    assert output["sections_revised"] == []
    assert output["retry_count_correction_script"] == 2
    assert "retry_count_correction_section" not in output
    _assert_token_output(output)


def test_build_script_output_returns_only_the_public_adapted_script() -> None:
    """Final node should expose one consolidated, serializable public result."""

    state = _base_state()
    state["validation_passed"] = True

    output = build_script_output(state)

    assert set(output) == {"adapted_script"}
    adapted_script = output["adapted_script"]
    assert adapted_script["validation_passed"] is True
    assert adapted_script["cta"] == "Join the course waiting list."
    assert adapted_script["hooks"] == ["Original hook."]
    assert adapted_script["estimated_duration_seconds"] > 0
    assert adapted_script["sections"][-1]["pause_after_seconds"] == 0.0
    assert "scene_planning_input" not in adapted_script


@pytest.mark.parametrize(
    "node",
    (
        build_copy_strategy,
        write_script_sections,
        review_section_flow,
        correct_section,
        validate_script,
        correct_script,
    ),
)
def test_llm_backed_nodes_reject_missing_runtime_context(node: Any) -> None:
    """LLM-backed nodes should fail before accessing state without context."""

    runtime = cast(
        WorkflowRuntime[CopyAdaptationWorkflowContext],
        WorkflowRuntime(context=None),
    )

    with pytest.raises(
        RuntimeError,
        match="Copy adaptation workflow context is required",
    ):
        node({}, runtime)


@pytest.mark.parametrize(
    ("node", "state", "message"),
    (
        (build_copy_strategy, {}, "copy_analysis is required"),
        (write_script_sections, {}, "user_profile is required"),
        (review_section_flow, {}, "sections is required"),
        (correct_section, {}, "user_profile is required"),
        (validate_script, {}, "user_profile is required"),
        (correct_script, {}, "user_profile is required"),
    ),
)
def test_llm_backed_nodes_reject_missing_state_dependencies(
    node: Any,
    state: dict[str, Any],
    message: str,
) -> None:
    """Each node should report its first missing state dependency clearly."""

    runtime, _ = _runtime()

    with pytest.raises(ValueError, match=message):
        node(cast(CopyAdaptationState, state), runtime)
