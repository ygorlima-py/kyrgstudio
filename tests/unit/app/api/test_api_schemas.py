"""Unit tests for public API job schemas and response mappers."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.jobs import (
    CreateCopyAdaptationJobRequest,
    CreateCopyAnalysisJobRequest,
    build_job_result_response,
    build_job_status_response,
    build_job_submission_response,
    build_pipeline_input,
    parse_create_job_request,
)
from app.schemas.pipeline import (
    CopyAdaptationPipelineInput,
    CopyAnalysisPipelineInput,
    PipelineStartResult,
)
from app.settings import AppSettings


NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)


def _settings() -> AppSettings:
    """Build deterministic application defaults for schema mapping tests."""

    return AppSettings(
        environment="test",
        storage_dir=Path("/tmp/kyrg-api-schema-storage"),
        sqlite_path=Path("/tmp/kyrg-api-schema.sqlite"),
        database_url="sqlite+aiosqlite:////tmp/kyrg-api-schema.sqlite",
        database_echo=False,
        database_pool_size=5,
        database_max_overflow=10,
        database_pool_pre_ping=True,
        openrouter_api_key=None,
        openai_api_key=None,
        gemini_api_key=None,
        default_llm_provider="openrouter",
        default_analysis_model="default-analysis-model",
        default_adaptation_model="default-adaptation-model",
        default_transcriber_provider="whisper_local",
        default_transcriber_model="small",
        max_duration_seconds=300,
        request_timeout_seconds=60,
        celery_broker_url="amqp://guest:guest@localhost:5672//",
        celery_queue_name="pipeline",
        celery_task_soft_time_limit_seconds=60,
        celery_task_time_limit_seconds=90,
    )


def _user_profile_payload() -> dict[str, object]:
    """Return the minimum complete offer profile accepted by adaptation."""

    return {
        "product_or_solution": "Commission planning software",
        "target_audience": "Independent sales professionals",
        "core_problem": "Income is difficult to organize",
        "core_desire": "Build predictable financial control",
        "main_promise": "Organize variable income with a clear plan",
        "unique_mechanism": "Commission allocation framework",
        "benefits": ["Clear allocation decisions"],
        "objections": ["My income changes every month"],
        "proof_assets": ["Existing customer case study"],
        "offer_details": "Monthly subscription",
        "call_to_action": "Start the free trial",
        "tone": "Direct and practical",
        "target_language": "English",
        "platform": "YouTube",
        "desired_duration": 2.0,
        "restrictions": ["Do not promise guaranteed earnings"],
    }


def _analysis_request_json(**overrides: object) -> str:
    values: dict[str, object] = {
        "pipeline_type": "copy_analysis",
        "source_type": "video",
        "language": "pt-BR",
        "need_correction": True,
        "output_formats": ["json", "markdown"],
    }
    values.update(overrides)

    import json

    return json.dumps(values)


def _adaptation_request_json(**overrides: object) -> str:
    values: dict[str, object] = {
        "pipeline_type": "copy_adaptation",
        "source_type": "audio",
        "user_profile": _user_profile_payload(),
    }
    values.update(overrides)

    import json

    return json.dumps(values)


def test_parse_copy_analysis_job_request() -> None:
    """Parse multipart JSON into the concrete copy-analysis request schema."""

    request = parse_create_job_request(_analysis_request_json())

    assert isinstance(request, CreateCopyAnalysisJobRequest)
    assert request.pipeline_type == "copy_analysis"
    assert request.source_type == "video"
    assert request.language == "pt-BR"
    assert request.need_correction is True
    assert request.output_formats == ["json", "markdown"]


def test_parse_copy_adaptation_job_request() -> None:
    """Parse adaptation JSON and validate its nested offer profile."""

    request = parse_create_job_request(_adaptation_request_json())

    assert isinstance(request, CreateCopyAdaptationJobRequest)
    assert request.pipeline_type == "copy_adaptation"
    assert request.source_type == "audio"
    assert request.user_profile.product_or_solution == (
        "Commission planning software"
    )
    assert request.user_profile.desired_duration == 2.0


def test_parse_job_request_rejects_invalid_json() -> None:
    """Reject malformed JSON before pipeline input construction."""

    with pytest.raises(ValidationError):
        parse_create_job_request('{"pipeline_type": "copy_analysis"')


def test_parse_job_request_rejects_unknown_pipeline_type() -> None:
    """Reject pipeline discriminators not supported by the application."""

    with pytest.raises(ValidationError):
        parse_create_job_request(
            _analysis_request_json(pipeline_type="unknown_pipeline")
        )


def test_parse_job_request_rejects_extra_fields() -> None:
    """Forbid undeclared request metadata at the HTTP boundary."""

    with pytest.raises(ValidationError):
        parse_create_job_request(
            _analysis_request_json(unexpected_field="not-allowed")
        )


def test_build_analysis_pipeline_input_uses_settings_defaults() -> None:
    """Fill omitted analysis provider and duration fields from settings."""

    request = parse_create_job_request(
        _analysis_request_json(output_formats=["markdown", "text"])
    )

    pipeline_input = build_pipeline_input(request, settings=_settings())

    assert isinstance(pipeline_input, CopyAnalysisPipelineInput)
    assert pipeline_input.transcriber_provider == "whisper_local"
    assert pipeline_input.transcriber_model == "small"
    assert pipeline_input.llm_provider == "openrouter"
    assert pipeline_input.analysis_model == "default-analysis-model"
    assert pipeline_input.max_duration_seconds == 300
    assert pipeline_input.output_formats == ["md", "txt"]
    assert pipeline_input.need_correction is True


def test_build_adaptation_pipeline_input_uses_settings_defaults() -> None:
    """Fill omitted adaptation models while preserving the user profile."""

    request = parse_create_job_request(_adaptation_request_json())

    pipeline_input = build_pipeline_input(request, settings=_settings())

    assert isinstance(pipeline_input, CopyAdaptationPipelineInput)
    assert pipeline_input.transcriber_provider == "whisper_local"
    assert pipeline_input.llm_provider == "openrouter"
    assert pipeline_input.analysis_model == "default-analysis-model"
    assert pipeline_input.adaptation_model == "default-adaptation-model"
    assert pipeline_input.max_duration_seconds == 300
    assert pipeline_input.user_profile.call_to_action == "Start the free trial"


def test_request_run_id_has_priority_over_idempotency_key() -> None:
    """Use the explicit request run id when both identifiers are supplied."""

    request = parse_create_job_request(
        _analysis_request_json(run_id="request-run-id")
    )

    pipeline_input = build_pipeline_input(
        request,
        settings=_settings(),
        idempotency_key="header-idempotency-key",
    )

    assert pipeline_input.run_id == "request-run-id"


def test_idempotency_key_is_used_when_run_id_is_missing() -> None:
    """Use the validated idempotency header when request JSON omits run id."""

    request = parse_create_job_request(_analysis_request_json())

    pipeline_input = build_pipeline_input(
        request,
        settings=_settings(),
        idempotency_key="  header-idempotency-key  ",
    )

    assert pipeline_input.run_id == "header-idempotency-key"


def test_build_job_submission_response_hides_storage_references() -> None:
    """Exclude private storage data from the accepted-job response."""

    result = PipelineStartResult(
        job_id=41,
        run_id="run-41",
        status="uploaded",
        current_step="queued",
        pipeline_type="copy_analysis",
        storage_backend="local",
        input_file_key="jobs/41/input/video.mp4",
        input_file_uri="/private/storage/jobs/41/input/video.mp4",
    )

    response = build_job_submission_response(result)
    payload = response.model_dump()

    assert payload == {
        "job_id": 41,
        "run_id": "run-41",
        "status": "uploaded",
        "current_step": "queued",
        "pipeline_type": "copy_analysis",
    }
    assert "storage_backend" not in payload
    assert "input_file_key" not in payload
    assert "input_file_uri" not in payload


def test_build_job_status_response_maps_public_fields() -> None:
    """Map persisted status metadata without exposing job internals."""

    job = SimpleNamespace(
        id=41,
        user_id=7,
        run_id="run-41",
        pipeline_type="copy_adaptation",
        status="running",
        current_step="copy_analysis",
        created_at=NOW,
        started_at=NOW + timedelta(seconds=1),
        finished_at=None,
        execution_time_seconds="12.5",
        input_json={"private": "input"},
        input_file_uri="/private/storage/input.mp4",
        error_json=None,
    )

    response = build_job_status_response(job)
    payload = response.model_dump()

    assert payload == {
        "job_id": 41,
        "run_id": "run-41",
        "pipeline_type": "copy_adaptation",
        "status": "running",
        "current_step": "copy_analysis",
        "created_at": NOW,
        "started_at": NOW + timedelta(seconds=1),
        "finished_at": None,
        "execution_time_seconds": 12.5,
        "error": None,
    }
    assert "user_id" not in payload
    assert "input_json" not in payload
    assert "input_file_uri" not in payload


def test_build_failed_job_status_hides_internal_error_details() -> None:
    """Expose stable error identity while removing persisted technical details."""

    job = {
        "id": 42,
        "run_id": "run-42",
        "pipeline_type": "copy_analysis",
        "status": "failed",
        "current_step": "transcribing",
        "created_at": NOW,
        "started_at": NOW,
        "finished_at": NOW + timedelta(seconds=4),
        "execution_time_seconds": 4.0,
        "error_json": {
            "code": "transcription_failed",
            "step": "transcribing",
            "technical_message": "Provider returned an internal stack trace",
            "local_path": "/private/storage/input.mp4",
            "details": {"api_key": "secret"},
        },
    }

    response = build_job_status_response(job)

    assert response.error is not None
    assert response.error.code == "transcription_failed"
    assert response.error.step == "transcribing"
    assert response.error.details == {}
    assert "technical_message" not in response.model_dump_json()
    assert "/private/storage" not in response.model_dump_json()
    assert "secret" not in response.model_dump_json()


def test_build_job_result_response_requires_completed_job() -> None:
    """Reject result mapping until the persisted job reaches completion."""

    job = {
        "id": 41,
        "run_id": "run-41",
        "pipeline_type": "copy_analysis",
        "status": "running",
        "output_json": {"copy_analysis": {}},
    }

    with pytest.raises(ValueError, match="completed"):
        build_job_result_response(job)


def test_build_job_result_response_returns_only_public_output() -> None:
    """Return completed output without storage, ownership, or input metadata."""

    job = {
        "id": 41,
        "user_id": 7,
        "run_id": "run-41",
        "pipeline_type": "copy_analysis",
        "status": "completed",
        "output_json": {
            "copy_analysis": {"main_promise": "Organize variable income"},
            "token_usage": {"total_tokens": 250},
        },
        "input_json": {"provider": "private-provider"},
        "storage_backend": "local",
        "input_file_key": "jobs/41/input/video.mp4",
        "input_file_uri": "/private/storage/jobs/41/input/video.mp4",
    }

    response = build_job_result_response(job)
    payload = response.model_dump()

    assert payload == {
        "job_id": 41,
        "run_id": "run-41",
        "pipeline_type": "copy_analysis",
        "status": "completed",
        "output": {
            "copy_analysis": {
                "main_promise": "Organize variable income",
            },
            "token_usage": {"total_tokens": 250},
        },
    }
    assert "user_id" not in payload
    assert "input_json" not in payload
    assert "storage_backend" not in payload
    assert "input_file_uri" not in payload
