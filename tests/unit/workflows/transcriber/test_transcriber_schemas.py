"""Unit tests for the transcriber workflow schemas."""

from typing import Any, TypedDict

import pytest
from pydantic import ValidationError

from kyrg.workflows.transcriber.schemas import (
    CorrectedSegment,
    CorrectedTranscriptionOutput,
    DomainContextOutput,
    PossibleCorrection,
    TranscriberWorkflowContext,
    TranscriptorConfig,
    UncertainTerm,
)


DOMAIN_REQUIRED_FIELDS = (
    "language",
    "main_subject",
    "content_type",
    "summary",
)
DOMAIN_LIST_FIELDS = (
    "important_terms",
    "named_entities",
    "technical_terms",
    "possible_corrections",
    "uncertain_terms",
    "correction_rules",
)


class DomainPayload(TypedDict):
    """Represent the required fields of a domain context payload."""

    language: str
    main_subject: str
    content_type: str
    summary: str


def domain_payload() -> DomainPayload:
    """Return the minimum valid domain context payload."""
    return {
        "language": "English",
        "main_subject": "Schema contracts",
        "content_type": "lesson",
        "summary": "A concise schema overview.",
    }


@pytest.mark.parametrize("missing_field", DOMAIN_REQUIRED_FIELDS)
def test_domain_context_requires_core_fields(missing_field: str) -> None:
    """Reject a domain context when any core field is absent."""
    payload: dict[str, Any] = dict(domain_payload())
    payload.pop(missing_field)

    with pytest.raises(ValidationError):
        DomainContextOutput(**payload)


def test_domain_context_list_defaults_are_independent() -> None:
    """Create independent empty list defaults for every domain list field."""
    first = DomainContextOutput(**domain_payload())
    second = DomainContextOutput(**domain_payload())

    for field_name in DOMAIN_LIST_FIELDS:
        first_list = getattr(first, field_name)
        second_list = getattr(second, field_name)
        assert first_list == []
        assert second_list == []
        assert first_list is not second_list
        first_list.append("sentinel")
        assert second_list == []


def test_domain_context_accepts_complete_nested_lists() -> None:
    """Accept complete correction and uncertain-term entries."""
    context = DomainContextOutput(
        **domain_payload(),
        possible_corrections=[
            PossibleCorrection(
                original="pie right",
                corrected="Pyright",
                confidence=0.95,
                reason="The surrounding discussion is about type checking.",
            )
        ],
        uncertain_terms=[
            UncertainTerm(
                term="pie test",
                reason="The pronunciation could refer to pytest.",
            )
        ],
    )

    assert context.possible_corrections[0].corrected == "Pyright"
    assert context.uncertain_terms[0].term == "pie test"


def test_domain_context_accepts_empty_strings_and_duplicates() -> None:
    """Preserve empty strings and duplicate list items without restrictions."""
    context = DomainContextOutput(
        language="",
        main_subject="",
        content_type="",
        summary="",
        important_terms=["", "duplicate", "duplicate"],
        named_entities=["same", "same"],
        technical_terms=["", ""],
        correction_rules=["rule", "rule"],
    )

    assert context.language == ""
    assert context.important_terms == ["", "duplicate", "duplicate"]
    assert context.named_entities == ["same", "same"]
    assert context.technical_terms == ["", ""]
    assert context.correction_rules == ["rule", "rule"]


def test_domain_context_json_round_trip_is_lossless() -> None:
    """Restore a complete domain context from its JSON representation."""
    context = DomainContextOutput(
        **domain_payload(),
        important_terms=["Pydantic"],
        named_entities=["Kyrg"],
        technical_terms=["default_factory"],
        possible_corrections=[
            PossibleCorrection(
                original="pie dantic",
                corrected="Pydantic",
                confidence=1,
                reason="It is the discussed validation library.",
            )
        ],
        uncertain_terms=[UncertainTerm(term="Kyrg", reason="Uncommon name.")],
        correction_rules=["Preserve technical terms."],
    )

    restored = DomainContextOutput.model_validate_json(context.model_dump_json())

    assert restored == context


@pytest.mark.parametrize(
    "missing_field",
    ("original", "corrected", "confidence", "reason"),
)
def test_possible_correction_requires_every_field(missing_field: str) -> None:
    """Reject a possible correction when a declared field is absent."""
    payload: dict[str, Any] = {
        "original": "old",
        "corrected": "new",
        "confidence": 0.5,
        "reason": "Context supports the change.",
    }
    payload.pop(missing_field)

    with pytest.raises(ValidationError):
        PossibleCorrection(**payload)


@pytest.mark.parametrize("missing_field", ("term", "reason"))
def test_uncertain_term_requires_every_field(missing_field: str) -> None:
    """Reject an uncertain term when a declared field is absent."""
    payload = {"term": "ambiguous", "reason": "Audio is unclear."}
    payload.pop(missing_field)

    with pytest.raises(ValidationError):
        UncertainTerm(**payload)


@pytest.mark.parametrize("confidence", (0.0, 1.0))
def test_possible_correction_accepts_confidence_boundaries(
    confidence: float,
) -> None:
    """Accept confidence values at both inclusive boundaries."""
    correction = PossibleCorrection(
        original="old",
        corrected="new",
        confidence=confidence,
        reason="Context supports the change.",
    )

    assert correction.confidence == confidence


@pytest.mark.parametrize("confidence", (-0.001, 1.001))
def test_possible_correction_rejects_out_of_range_confidence(
    confidence: float,
) -> None:
    """Reject confidence values outside the inclusive unit interval."""
    with pytest.raises(ValidationError):
        PossibleCorrection(
            original="old",
            corrected="new",
            confidence=confidence,
            reason="Context supports the change.",
        )


def test_possible_correction_accepts_empty_texts() -> None:
    """Accept empty text fields in a possible correction."""
    correction = PossibleCorrection(
        original="",
        corrected="",
        confidence=0.5,
        reason="",
    )

    assert correction.original == correction.corrected == correction.reason == ""


def test_uncertain_term_accepts_empty_texts() -> None:
    """Accept empty text fields in an uncertain term."""
    uncertain_term = UncertainTerm(term="", reason="")

    assert uncertain_term.term == uncertain_term.reason == ""


@pytest.mark.parametrize(
    ("schema", "payload"),
    (
        (CorrectedSegment, {"text": "corrected"}),
        (CorrectedSegment, {"id": 1}),
        (CorrectedTranscriptionOutput, {}),
    ),
)
def test_corrected_schemas_require_declared_fields(
    schema: Any,
    payload: dict[str, Any],
) -> None:
    """Reject corrected output models when a required field is absent."""
    with pytest.raises(ValidationError):
        schema(**payload)


def test_corrected_segments_default_is_empty_and_independent() -> None:
    """Create an independent empty corrected-segment list per output."""
    first = CorrectedTranscriptionOutput(corrected_text="First")
    second = CorrectedTranscriptionOutput(corrected_text="Second")

    assert first.corrected_segments == []
    assert second.corrected_segments == []
    assert first.corrected_segments is not second.corrected_segments
    first.corrected_segments.append(CorrectedSegment(id=1, text="Changed"))
    assert second.corrected_segments == []


def test_corrected_output_accepts_unrestricted_segment_ids() -> None:
    """Accept negative, duplicate, and otherwise unknown segment IDs."""
    output = CorrectedTranscriptionOutput(
        corrected_text="Corrected globally.",
        corrected_segments=[
            CorrectedSegment(id=-1, text="Negative"),
            CorrectedSegment(id=-1, text="Duplicate"),
            CorrectedSegment(id=999_999, text="Unknown"),
        ],
    )

    assert [segment.id for segment in output.corrected_segments] == [
        -1,
        -1,
        999_999,
    ]


def test_corrected_output_accepts_global_and_segment_text_divergence() -> None:
    """Allow global corrected text to diverge from segment text."""
    output = CorrectedTranscriptionOutput(
        corrected_text="Global text with unrelated content.",
        corrected_segments=[CorrectedSegment(id=7, text="Segment text.")],
    )

    assert output.corrected_text != output.corrected_segments[0].text


def test_corrected_output_json_round_trip_is_lossless() -> None:
    """Restore corrected output and nested segments from JSON."""
    output = CorrectedTranscriptionOutput(
        corrected_text="Complete corrected transcript.",
        corrected_segments=[
            CorrectedSegment(id=3, text="First correction."),
            CorrectedSegment(id=8, text="Second correction."),
        ],
    )

    restored = CorrectedTranscriptionOutput.model_validate_json(
        output.model_dump_json()
    )

    assert restored == output


@pytest.mark.parametrize(
    "missing_field",
    ("correction_llm", "extract_context_llm", "transcriptor_config"),
)
def test_workflow_context_requires_all_constructor_arguments(
    missing_field: str,
) -> None:
    """Require every workflow context argument at construction time."""
    payload: dict[str, Any] = {
        "correction_llm": object(),
        "extract_context_llm": object(),
        "transcriptor_config": object(),
    }
    payload.pop(missing_field)

    with pytest.raises(TypeError):
        TranscriberWorkflowContext(**payload)


def test_transcriptor_config_defaults() -> None:
    """Default transcriber temperature to zero and API key to none."""
    transcriptor: Any = object()

    config = TranscriptorConfig(transcriptor=transcriptor)

    assert config.transcriptor_temperature == 0.0
    assert config.transcriptor_api_key is None


def test_transcriptor_config_accepts_none_temperature() -> None:
    """Accept an explicit none value for transcriber temperature."""
    transcriptor: Any = object()

    config = TranscriptorConfig(
        transcriptor=transcriptor,
        transcriptor_temperature=None,
    )

    assert config.transcriptor_temperature is None


def test_context_dataclasses_do_not_validate_types_at_runtime() -> None:
    """Preserve incompatible values because dataclasses skip runtime checks."""
    incompatible: Any = object()
    config = TranscriptorConfig(
        transcriptor=incompatible,
        transcriptor_temperature=incompatible,
        transcriptor_api_key=incompatible,
    )
    context = TranscriberWorkflowContext(
        correction_llm=incompatible,
        extract_context_llm=incompatible,
        transcriptor_config=incompatible,
    )

    assert config.transcriptor is incompatible
    assert config.transcriptor_temperature is incompatible
    assert config.transcriptor_api_key is incompatible
    assert context.correction_llm is incompatible
    assert context.extract_context_llm is incompatible
    assert context.transcriptor_config is incompatible
