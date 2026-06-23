"""Unit tests for deterministic copy adaptation utilities."""

from typing import Any

import pytest

from kyrg.workflows.copyadaptation._utils import (
    _add_words_count_per_section,
    _BuildScriptOutput,
    _calculate_time_estimated,
    _resolve_final_sections,
    _resolve_pause,
)
from kyrg.workflows.copyadaptation.constants import SECTION_PAUSE_SECONDS
from kyrg.workflows.copyadaptation.schemas import (
    ScriptSectionOutput,
    WriteScriptSectionsOutput,
)
from kyrg.workflows.copyadaptation.state import CopyAdaptationState


def _section(
    *,
    order: int = 1,
    section_type: str = "hook",
    text: str = "one two three four five",
    pause_intent: str = "medium",
) -> dict[str, Any]:
    """Build one validated script section as workflow state data."""

    return ScriptSectionOutput.model_validate(
        {
            "order": order,
            "section_type": section_type,
            "text": text,
            "purpose": f"Serve the {section_type} role.",
            "adaptation_mode": "adapted_from_reference",
            "source_reference_section_type": section_type,
            "proof_used": None,
            "missing_proof": False,
            "transition_hint": "Continue to the next section.",
            "pause_intent": pause_intent,
        }
    ).model_dump()


def _state(
    *,
    sections: list[dict[str, Any]] | None = None,
    desired_duration: float | None = 1.0,
) -> CopyAdaptationState:
    """Build the timing subset of workflow state required by utility functions."""

    state: CopyAdaptationState = {
        "sections": sections
        if sections is not None
        else [
            _section(text="one two three four five six seven eight nine ten"),
            _section(
                order=2,
                section_type="cta",
                text="one two three four five",
                pause_intent="short",
            ),
        ],
    }
    if desired_duration is not None:
        state["desired_duration"] = desired_duration
    return state


def test_add_words_count_recalculates_each_section_from_text() -> None:
    """Word counts should be derived from text instead of model estimates."""

    output = WriteScriptSectionsOutput(
        sections=[
            ScriptSectionOutput.model_validate(_section(text="three exact words")),
            ScriptSectionOutput.model_validate(
                _section(order=2, section_type="cta", text="join today")
            ),
        ],
        adaptation_notes="Test output.",
    )

    sections = _add_words_count_per_section(output)

    assert [section["word_count"] for section in sections] == [3, 2]


@pytest.mark.parametrize(
    ("section_type", "expected_pause"),
    tuple(SECTION_PAUSE_SECONDS.items()),
)
def test_resolve_pause_uses_the_section_base_for_medium_intent(
    section_type: str,
    expected_pause: float,
) -> None:
    """Medium intent should preserve every configured section base pause."""

    assert _resolve_pause(section_type, "medium") == expected_pause


@pytest.mark.parametrize(
    ("intent", "coefficient"),
    (
        ("short", 0.75),
        ("medium", 1.0),
        ("long", 1.35),
        ("dramatic", 1.75),
    ),
)
def test_resolve_pause_applies_intent_coefficients(
    intent: str,
    coefficient: float,
) -> None:
    """Narrative intent should scale the section's deterministic base pause."""

    expected = round(SECTION_PAUSE_SECONDS["story"] * coefficient, 2)
    assert _resolve_pause("story", intent) == expected


def test_resolve_pause_uses_fallbacks_for_unknown_values() -> None:
    """Unknown section and intent values should use stable neutral defaults."""

    assert _resolve_pause("unknown", "medium") == 0.4
    assert _resolve_pause("hook", "unknown") == SECTION_PAUSE_SECONDS["hook"]


def test_resolve_pause_clamps_extreme_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pause resolution should enforce the supported production interval."""

    monkeypatch.setitem(SECTION_PAUSE_SECONDS, "tiny", 0.01)
    monkeypatch.setitem(SECTION_PAUSE_SECONDS, "oversized", 2.0)

    assert _resolve_pause("tiny", "short") == 0.1
    assert _resolve_pause("oversized", "dramatic") == 1.8


def test_calculate_time_estimated_sums_speech_and_non_final_pauses() -> None:
    """Total duration should include speech and exclude a final trailing pause."""

    metrics = _calculate_time_estimated(_state(desired_duration=None))

    assert metrics == {
        "word_count": 15,
        "speech_seconds": 6.0,
        "pause_seconds": 0.5,
        "total_seconds": 6.5,
        "estimated_duration_seconds": 6.5,
        "min_words": None,
        "max_words": None,
        "duration_status": "unknown",
    }


@pytest.mark.parametrize(
    ("desired_duration", "expected_status"),
    (
        (0.2, "too_short"),
        (0.1, "too_long"),
        (6.7 / 60, "ok"),
    ),
)
def test_calculate_time_estimated_assigns_duration_statuses(
    desired_duration: float,
    expected_status: str,
) -> None:
    """Duration status should follow deterministic target boundaries."""

    metrics = _calculate_time_estimated(
        _state(desired_duration=desired_duration)
    )

    assert metrics["duration_status"] == expected_status


def test_calculate_time_estimated_uses_custom_words_per_minute() -> None:
    """Workflow-specific narration rates should override default WPM values."""

    state = _state(desired_duration=None)
    state["min_words_per_minute"] = 60
    state["max_words_per_minute"] = 60

    metrics = _calculate_time_estimated(state)

    assert metrics["speech_seconds"] == 15.0
    assert metrics["total_seconds"] == 15.5


@pytest.mark.parametrize(
    "operation",
    (
        _calculate_time_estimated,
        _resolve_final_sections,
        _BuildScriptOutput,
    ),
)
def test_section_dependent_utilities_reject_empty_sections(operation: Any) -> None:
    """Utilities should fail clearly when no script sections are available."""

    with pytest.raises(ValueError, match="sections is required"):
        operation({"sections": [], "desired_duration": 1.0})


def test_resolve_final_sections_replaces_matching_orders_and_sorts_new_ones() -> None:
    """Reviewed sections should replace matching orders and append in order."""

    state = _state(
        sections=[
            _section(order=1, text="Original first section."),
            _section(order=3, section_type="cta", text="Original final section."),
        ]
    )
    state["sections_revised"] = [
        _section(order=1, text="Revised first section."),
        _section(order=2, section_type="offer", text="Inserted offer section."),
    ]

    resolved = _resolve_final_sections(state)

    assert [section["order"] for section in resolved] == [1, 2, 3]
    assert resolved[0]["text"] == "Revised first section."
    assert resolved[1]["text"] == "Inserted offer section."


def test_resolve_final_sections_does_not_mutate_original_sections() -> None:
    """Resolving revisions should leave checkpointed source sections unchanged."""

    original = _section(text="Original immutable section.")
    state = _state(sections=[original])
    state["sections_revised"] = [_section(text="Revised section.")]

    _resolve_final_sections(state)

    assert state["sections"][0]["text"] == "Original immutable section."


def test_build_script_output_creates_a_continuous_timeline() -> None:
    """Each section should start after the previous speech and pause complete."""

    builder = _BuildScriptOutput(_state())

    sections = builder._final_sections()

    assert sections[0].start_seconds == 0.0
    assert sections[1].start_seconds == round(
        sections[0].end_seconds + sections[0].pause_after_seconds,
        2,
    )
    assert sections[-1].pause_after_seconds == 0.0


def test_build_script_output_extracts_hooks_ctas_and_rendered_text() -> None:
    """Output helpers should expose presentation and narration representations."""

    state = _state(
        sections=[
            _section(section_type="hook", text="First hook."),
            _section(order=2, section_type="hook", text="Second hook."),
            _section(order=3, section_type="cta", text="Join now."),
        ]
    )
    builder = _BuildScriptOutput(state)

    assert builder._hooks() == ["First hook.", "Second hook."]
    assert builder._cta_sections() == ["Join now."]
    assert builder._voice_ready_text() == "First hook.\n\nSecond hook.\n\nJoin now."
    assert builder._script() == (
        "## hook\nFirst hook.\n\n"
        "## hook\nSecond hook.\n\n"
        "## cta\nJoin now."
    )

