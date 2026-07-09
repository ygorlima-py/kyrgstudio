"""Unit tests for pipeline input validation and normalization.

These tests protect the boundary before the application touches storage,
database, queue, or workflow execution.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.errors import InvalidInputError
from app.pipeline.input import get_pipeline_type, normalize_pipeline_input
from app.schemas.pipeline import (
    CopyAdaptationPipelineInput,
    CopyAnalysisPipelineInput,
)
from kyrg.workflows.copyadaptation import UserProfileOutput


def test_normalize_copy_analysis_input() -> None:
    """Copy analysis input should be trimmed and normalized consistently."""

    pipeline_input = _copy_analysis_input(
        source_path="  video.mp4  ",
        source_type="VIDEO",
        run_id="  run_123  ",
        language="  pt-BR  ",
        transcriber_provider="  WHISPER_LOCAL  ",
        transcriber_model="  small  ",
        llm_provider="  OPENROUTER  ",
        analysis_model="  deepseek/deepseek-v4-flash  ",
        output_formats=[" JSON "],
    )

    normalized = normalize_pipeline_input(pipeline_input)

    assert isinstance(normalized, CopyAnalysisPipelineInput)
    assert get_pipeline_type(normalized) == "copy_analysis"
    assert normalized.source_path == "video.mp4"
    assert normalized.source_type == "video"
    assert normalized.run_id == "run_123"
    assert normalized.language == "pt-BR"
    assert normalized.transcriber_provider == "whisper_local"
    assert normalized.transcriber_model == "small"
    assert normalized.llm_provider == "openrouter"
    assert normalized.analysis_model == "deepseek/deepseek-v4-flash"
    assert normalized.output_formats == ["json"]


def test_normalize_copy_adaptation_input() -> None:
    """Copy adaptation input should normalize common fields and model choice."""

    pipeline_input = _copy_adaptation_input(
        source_path="  input.wav  ",
        source_type="AUDIO",
        transcriber_provider="  OPENAI  ",
        transcriber_model="  whisper-1  ",
        llm_provider="  GEMINI  ",
        analysis_model="  gemini-2.5-flash  ",
        adaptation_model="  gemini-2.5-pro  ",
        output_formats=[],
    )

    normalized = normalize_pipeline_input(pipeline_input)

    assert isinstance(normalized, CopyAdaptationPipelineInput)
    assert get_pipeline_type(normalized) == "copy_adaptation"
    assert normalized.source_path == "input.wav"
    assert normalized.source_type == "audio"
    assert normalized.transcriber_provider == "openai"
    assert normalized.transcriber_model == "whisper-1"
    assert normalized.llm_provider == "gemini"
    assert normalized.analysis_model == "gemini-2.5-flash"
    assert normalized.adaptation_model == "gemini-2.5-pro"
    assert normalized.output_formats == ["json"]


def test_rejects_invalid_source_type() -> None:
    """Invalid source_type should fail before storage or queue execution."""

    pipeline_input = CopyAnalysisPipelineInput.model_construct(
        source_path="video.pdf",
        source_type="pdf",
        transcriber_provider="whisper_local",
        transcriber_model="small",
        llm_provider="openrouter",
        analysis_model="deepseek/deepseek-v4-flash",
        output_formats=["json"],
    )

    with pytest.raises(InvalidInputError) as error:
        normalize_pipeline_input(pipeline_input)

    assert error.value.details["field"] == "source_type"
    assert error.value.details["value"] == "pdf"
    assert error.value.details["supported_values"] == ["video", "audio"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_path", " "),
        ("transcriber_provider", " "),
        ("transcriber_model", " "),
        ("llm_provider", " "),
        ("analysis_model", " "),
    ],
)
def test_rejects_missing_required_provider_or_model(
    field: str,
    value: str,
) -> None:
    """Required input, provider, and model fields should not accept blanks."""

    overrides = {field: value}
    pipeline_input = _copy_analysis_input(**overrides)

    with pytest.raises(InvalidInputError) as error:
        normalize_pipeline_input(pipeline_input)

    assert error.value.details["field"] == field
    assert error.value.details["pipeline_type"] == "copy_analysis"


def test_rejects_unsupported_llm_provider() -> None:
    """Unsupported LLM providers should fail before provider construction."""

    pipeline_input = _copy_analysis_input(llm_provider="anthropic")

    with pytest.raises(InvalidInputError) as error:
        normalize_pipeline_input(pipeline_input)

    assert error.value.details["field"] == "llm_provider"
    assert error.value.details["value"] == "anthropic"
    assert set(error.value.details["supported_values"]) == {
        "gemini",
        "openai",
        "openrouter",
    }


def test_rejects_unsupported_transcriber_provider() -> None:
    """Unsupported transcriber providers should fail before factory usage."""

    pipeline_input = _copy_analysis_input(transcriber_provider="elevenlabs")

    with pytest.raises(InvalidInputError) as error:
        normalize_pipeline_input(pipeline_input)

    assert error.value.details["field"] == "transcriber_provider"
    assert error.value.details["value"] == "elevenlabs"
    assert set(error.value.details["supported_values"]) == {
        "openai",
        "openrouter",
        "whisper_local",
    }


def test_rejects_non_positive_max_duration() -> None:
    """max_duration_seconds should be positive when provided."""

    pipeline_input = _copy_analysis_input(max_duration_seconds=0)

    with pytest.raises(InvalidInputError) as error:
        normalize_pipeline_input(pipeline_input)

    assert error.value.details == {
        "field": "max_duration_seconds",
        "value": 0,
        "pipeline_type": "copy_analysis",
    }


def test_normalizes_output_formats_and_aliases() -> None:
    """Output formats should be canonical, deduplicated, and alias-aware."""

    pipeline_input = _copy_analysis_input(
        output_formats=[
            " JSON ",
            "markdown",
            "MD",
            "text",
            "txt",
            "",
            "json",
        ]
    )

    normalized = normalize_pipeline_input(pipeline_input)

    assert normalized.output_formats == ["json", "md", "txt"]


def _copy_analysis_input(**overrides: Any) -> CopyAnalysisPipelineInput:
    """Build a valid copy analysis pipeline input for unit tests."""

    payload: dict[str, Any] = {
        "source_path": "video.mp4",
        "source_type": "video",
        "run_id": "run_123",
        "language": "pt-BR",
        "transcriber_provider": "whisper_local",
        "transcriber_model": "small",
        "llm_provider": "openrouter",
        "analysis_model": "deepseek/deepseek-v4-flash",
        "max_duration_seconds": 300,
        "output_formats": ["json"],
    }
    payload.update(overrides)

    if payload["source_type"] not in {"video", "audio"}:
        return CopyAnalysisPipelineInput.model_construct(**payload)

    return CopyAnalysisPipelineInput(**payload)


def _copy_adaptation_input(**overrides: Any) -> CopyAdaptationPipelineInput:
    """Build a valid copy adaptation pipeline input for unit tests."""

    payload: dict[str, Any] = {
        "source_path": "video.mp4",
        "source_type": "video",
        "run_id": "run_123",
        "language": "pt-BR",
        "transcriber_provider": "whisper_local",
        "transcriber_model": "small",
        "llm_provider": "openrouter",
        "analysis_model": "deepseek/deepseek-v4-flash",
        "adaptation_model": "deepseek/deepseek-v4-flash",
        "user_profile": _user_profile(),
        "max_duration_seconds": 300,
        "output_formats": ["json"],
    }
    payload.update(overrides)

    if payload["source_type"] not in {"video", "audio"}:
        return CopyAdaptationPipelineInput.model_construct(**payload)

    return CopyAdaptationPipelineInput(**payload)


def _user_profile() -> UserProfileOutput:
    """Build the minimum complete user profile required by adaptation input."""

    return UserProfileOutput(
        product_or_solution="A practical personal finance course",
        target_audience="Agronomists who want to invest commissions",
        core_problem="They do not know how to build an investment plan",
        core_desire="Invest commissions with more clarity and consistency",
        main_promise="Learn to organize commissions into a long-term portfolio",
        unique_mechanism="Commission Organization Method",
        benefits=["Clear investment planning steps"],
        objections=["I do not know where to start"],
        proof_assets=["Recorded curriculum walkthrough"],
        offer_details="Online course with waiting list",
        call_to_action="Join the waiting list",
        tone="Clear and practical",
        target_language="Portuguese",
        platform="YouTube",
        desired_duration=2.5,
        restrictions=["Do not promise guaranteed financial returns"],
    )
