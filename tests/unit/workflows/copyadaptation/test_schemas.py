"""Contract tests for copy adaptation workflow schemas.

These tests protect the validation boundaries shared by workflow nodes, LLM
actions, checkpoints, and the final consumer-facing output.
"""

from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from kyrg.workflows.copyadaptation.schemas import (
    AdaptedScriptOutput,
    BuildCopyStrategyOutput,
    ScriptSectionOutput,
    SectionRevisionInstruction,
    TimedScriptSectionOutput,
    UserProfileOutput,
    ValidationIssue,
)


REQUIRED_USER_PROFILE_FIELDS = (
    "product_or_solution",
    "target_audience",
    "core_problem",
    "core_desire",
    "main_promise",
    "call_to_action",
    "desired_duration",
)


def _user_profile_payload() -> dict[str, Any]:
    """Return the smallest complete user profile accepted by the schema."""

    return {
        "product_or_solution": "A practical personal finance course",
        "target_audience": "Agronomists who want to invest their commissions",
        "core_problem": "They lack a reliable long-term investment plan",
        "core_desire": "Build a diversified portfolio for the future",
        "main_promise": "Learn to organize and invest commissions responsibly",
        "call_to_action": "Join the course waiting list",
        "desired_duration": 2.5,
    }


def _script_section_payload() -> dict[str, Any]:
    """Return a complete script section with valid constrained values."""

    return {
        "order": 1,
        "section_type": "hook",
        "text": "Your commission can support the future you are planning.",
        "purpose": "Capture attention through a relevant financial aspiration.",
        "adaptation_mode": "adapted_from_reference",
        "source_reference_section_type": "hook",
        "proof_used": None,
        "missing_proof": False,
        "transition_hint": "Connect the aspiration to the current problem.",
        "pause_intent": "medium",
    }


def _strategy_payload() -> dict[str, Any]:
    """Return a valid copy strategy output payload."""

    return {
        "main_angle": "Turn irregular commissions into a long-term plan",
        "awareness_level": "problem_aware",
        "main_promise": "Learn a repeatable process for responsible investing",
        "persuasion_pattern": "education_to_offer",
        "objections_to_address": ["I do not know where to start"],
        "proof_plan": {"mechanism": "Use the course curriculum demonstration"},
        "unique_mechanism": "Commission Organization Method",
        "strategy_notes": "Educate before presenting the course.",
    }


def _assert_literal_validation_error(
    model: type[BaseModel],
    payload: dict[str, Any],
    field_name: str,
) -> None:
    """Assert that Pydantic rejects an invalid constrained field value."""

    with pytest.raises(ValidationError) as captured_error:
        model.model_validate(payload)

    errors = captured_error.value.errors()
    assert any(
        error["type"] == "literal_error" and error["loc"] == (field_name,)
        for error in errors
    )


def test_user_profile_accepts_a_complete_payload() -> None:
    """A complete offer profile should preserve input and initialize defaults."""

    profile = UserProfileOutput.model_validate(_user_profile_payload())

    assert profile.product_or_solution == "A practical personal finance course"
    assert profile.desired_duration == 2.5
    assert profile.benefits == []
    assert profile.objections == []
    assert profile.proof_assets == []
    assert profile.restrictions == []


@pytest.mark.parametrize("missing_field", REQUIRED_USER_PROFILE_FIELDS)
def test_user_profile_rejects_each_missing_required_field(
    missing_field: str,
) -> None:
    """Every required offer field should fail independently when omitted."""

    payload = _user_profile_payload()
    payload.pop(missing_field)

    with pytest.raises(ValidationError) as captured_error:
        UserProfileOutput.model_validate(payload)

    assert any(
        error["type"] == "missing" and error["loc"] == (missing_field,)
        for error in captured_error.value.errors()
    )


def test_user_profile_default_lists_are_not_shared() -> None:
    """Mutable defaults must remain isolated between workflow executions."""

    first_profile = UserProfileOutput.model_validate(_user_profile_payload())
    second_profile = UserProfileOutput.model_validate(_user_profile_payload())

    first_profile.benefits.append("Portfolio diversification")
    first_profile.objections.append("Investing feels too complex")
    first_profile.proof_assets.append("Recorded curriculum demonstration")
    first_profile.restrictions.append("Do not promise guaranteed returns")

    assert second_profile.benefits == []
    assert second_profile.objections == []
    assert second_profile.proof_assets == []
    assert second_profile.restrictions == []


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    (
        ("section_type", "authority"),
        ("adaptation_mode", "copied_verbatim"),
        ("pause_intent", "very_long"),
    ),
)
def test_script_section_rejects_invalid_constrained_values(
    field_name: str,
    invalid_value: str,
) -> None:
    """Script sections should reject values outside their canonical literals."""

    payload = _script_section_payload()
    payload[field_name] = invalid_value

    _assert_literal_validation_error(ScriptSectionOutput, payload, field_name)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    (
        ("awareness_level", "fully_unaware"),
        ("persuasion_pattern", "four_ps"),
    ),
)
def test_copy_strategy_rejects_invalid_constrained_values(
    field_name: str,
    invalid_value: str,
) -> None:
    """Strategy outputs should remain within supported workflow classifications."""

    payload = _strategy_payload()
    payload[field_name] = invalid_value

    _assert_literal_validation_error(BuildCopyStrategyOutput, payload, field_name)


def test_revision_instruction_rejects_an_unknown_action() -> None:
    """Revision instructions should expose only actions implemented by the flow."""

    payload = {
        "section_order": 2,
        "section_type": "promise",
        "issue": "The promise is disconnected from the mechanism.",
        "action": "replace_entire_script",
        "instruction": "Connect the promise to the approved mechanism.",
        "priority": "high",
    }

    _assert_literal_validation_error(
        SectionRevisionInstruction,
        payload,
        "action",
    )


def test_timed_section_preserves_copy_data_and_accepts_timing_metrics() -> None:
    """Timing enrichment must not discard the original script section contract."""

    payload = {
        **_script_section_payload(),
        "word_count": 9,
        "estimated_duration_seconds": 3.6,
        "pause_after_seconds": 0.5,
        "start_seconds": 0.0,
        "end_seconds": 3.6,
    }

    section = TimedScriptSectionOutput.model_validate(payload)

    assert section.text == payload["text"]
    assert section.purpose == payload["purpose"]
    assert section.adaptation_mode == payload["adaptation_mode"]
    assert section.word_count == 9
    assert section.estimated_duration_seconds == 3.6
    assert section.pause_after_seconds == 0.5
    assert section.start_seconds == 0.0
    assert section.end_seconds == 3.6


def test_adapted_script_round_trips_through_json() -> None:
    """The public workflow output should serialize and restore without data loss."""

    section = TimedScriptSectionOutput.model_validate(
        {
            **_script_section_payload(),
            "word_count": 9,
            "estimated_duration_seconds": 3.6,
            "pause_after_seconds": 0.0,
            "start_seconds": 0.0,
            "end_seconds": 3.6,
        }
    )
    original = AdaptedScriptOutput(
        script=f"## hook\n{section.text}",
        sections=[section],
        hooks=[section.text],
        cta=None,
        estimated_duration_seconds=3.6,
        word_count=9,
        voice_ready_text=section.text,
        adaptation_notes="The hook was adapted to the new audience.",
        validation_warnings=[
            ValidationIssue(
                category="duration",
                code="review_narration_pace",
                message="Review the final narration pace.",
                correction_action="custom",
                custom_instruction="Review pacing before production.",
            )
        ],
        validation_errors=[],
        validation_passed=True,
        missing_proofs=[],
    )

    restored = AdaptedScriptOutput.model_validate_json(original.model_dump_json())

    assert restored == original
    assert isinstance(restored.sections[0], TimedScriptSectionOutput)
