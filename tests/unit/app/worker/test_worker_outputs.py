"""Unit tests for persisted worker output shaping."""

from typing import Any

from app.schemas.workflow import WorkflowExecutionResult
from app.worker.outputs import (
    build_completed_output,
    build_copy_adaptation_output,
    build_copy_analysis_output,
)


def _internal_transcription() -> dict[str, Any]:
    """Return a transcription containing public and worker-only metadata."""

    return {
        "audio_path": "/tmp/kyrg-job-7/transcription.wav",
        "language": "en",
        "text": "A complete public transcription.",
        "segments": [
            {
                "text": "A timed segment.",
                "words": [{"word": "timed", "probability": 0.99}],
            }
        ],
        "words": [{"word": "internal"}],
        "raw_response": {"provider_payload": "private"},
        "model": "whisper-model",
        "provider": "whisper-local",
    }


def _analysis() -> dict[str, Any]:
    """Return representative analysis data that must remain untouched."""

    return {
        "language": "en",
        "copy_structure": {
            "sections": [{"section_type": "hook", "text": "Public hook"}],
            "section_gaps": [{"section_type": "proof", "gap_type": "weak"}],
            "summary": "Problem-solution structure.",
        },
        "offer_analysis": {
            "target_audience": "Independent professionals",
            "main_promise": "Create predictable financial control",
            "proof_elements": [{"name": "Customer case study"}],
        },
        "persuasion_analysis": {
            "dominant_emotion": "relief",
            "persuasion_signals": [{"name": "Specific promise"}],
            "weaknesses": [{"issue": "Proof needs more detail"}],
        },
    }


def test_copy_analysis_output_persists_only_public_transcription_fields() -> None:
    """Remove temporary paths and provider details before persistence."""

    analysis = _analysis()

    output = build_copy_analysis_output(
        payload={
            "transcription": _internal_transcription(),
            "copy_analysis": analysis,
        },
        token_usage={"total_tokens": 25},
        execution_time_seconds=4.5,
    )

    assert output["transcription"] == {
        "language": "en",
        "text": "A complete public transcription.",
    }
    assert output["copy_analysis"] == analysis
    assert output["token_usage"] == {"total_tokens": 25}
    assert output["execution_time_seconds"] == 4.5


def test_copy_adaptation_output_uses_the_same_transcription_boundary() -> None:
    """Keep transcription and adaptation diagnostics at public boundaries."""

    validation = {
        "validation_passed": False,
        "validation_errors": [{"code": "script_too_short"}],
        "validation_warnings": [],
    }

    output = build_copy_adaptation_output(
        payload={
            "transcription": _internal_transcription(),
            "copy_analysis": _analysis(),
            "adapted_script": {
                "voice_ready_text": "Adapted script",
                "validation_passed": False,
                "validation_errors": [{"code": "script_too_short"}],
                "validation_warnings": [],
                "missing_proofs": ["A verified customer result"],
            },
            "validation": validation,
        },
        token_usage={"total_tokens": 40},
        execution_time_seconds=7.0,
    )

    assert output["transcription"] == {
        "language": "en",
        "text": "A complete public transcription.",
    }
    assert output["adapted_script"] == {
        "voice_ready_text": "Adapted script"
    }
    assert output["validation"] == validation
    assert output["missing_proofs"] == ["A verified customer result"]


def test_completed_adaptation_output_does_not_duplicate_diagnostics() -> None:
    """Persist validation and proof diagnostics only at the result level."""

    output = build_completed_output(
        pipeline_type="copy_adaptation",
        result=WorkflowExecutionResult(
            output_json={
                "transcription": _internal_transcription(),
                "copy_analysis": _analysis(),
                "adapted_script": {
                    "script": "Adapted script",
                    "voice_ready_text": "Adapted script",
                    "validation_passed": False,
                    "validation_errors": [{"code": "script_too_short"}],
                    "validation_warnings": [{"code": "missing_proof"}],
                    "missing_proofs": ["A verified customer result"],
                },
                "validation": {
                    "validation_passed": False,
                    "validation_errors": [{"code": "script_too_short"}],
                    "validation_warnings": [{"code": "missing_proof"}],
                },
            },
            token_usage={"total_tokens": 40},
        ),
        execution_time_seconds=7.0,
    )

    assert output["adapted_script"] == {
        "script": "Adapted script",
        "voice_ready_text": "Adapted script",
    }
    assert output["validation"]["validation_passed"] is False
    assert output["missing_proofs"] == ["A verified customer result"]


def test_completed_output_never_persists_transcription_internals() -> None:
    """Keep forbidden transcription fields out of the final database payload."""

    output = build_completed_output(
        pipeline_type="copy_analysis",
        result=WorkflowExecutionResult(
            output_json={
                "transcription": _internal_transcription(),
                "copy_analysis": _analysis(),
            },
            token_usage={"total_tokens": 25},
        ),
        execution_time_seconds=4.5,
    )
    serialized_output = str(output)

    assert output["copy_analysis"] == _analysis()
    assert "audio_path" not in serialized_output
    assert "segments" not in serialized_output
    assert "words" not in serialized_output
    assert "raw_response" not in serialized_output
    assert "whisper-model" not in serialized_output
    assert "whisper-local" not in serialized_output
