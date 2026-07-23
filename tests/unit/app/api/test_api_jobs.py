"""Unit tests for authenticated pipeline job endpoints."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Coroutine
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, TypeVar, cast

import pytest
from fastapi import UploadFile, status
from fastapi.routing import APIRoute
from starlette.datastructures import Headers

import app.api.routers.jobs as jobs_module
import app.api.uploads as uploads_module
from app.api.uploads import ValidatedUpload
from app.auth.principal import AuthenticatedPrincipal
from app.errors import (
    InvalidInputError,
    JobNotFoundError,
    JobResultNotReadyError,
)
from app.pipeline.service import PipelineService
from app.schemas.pipeline import (
    CopyAdaptationPipelineInput,
    CopyAnalysisPipelineInput,
    PipelineStartResult,
    PipelineType,
)
from app.settings import AppSettings
from app.store.base import JobStoreBase


ResultT = TypeVar("ResultT")
NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)


def _run(coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    return asyncio.run(coroutine)


def _settings() -> AppSettings:
    """Return deterministic API and pipeline defaults."""

    return AppSettings(
        environment="test",
        storage_dir=Path("/tmp/kyrg-api-jobs-storage"),
        sqlite_path=Path("/tmp/kyrg-api-jobs.sqlite"),
        database_url="sqlite+aiosqlite:////tmp/kyrg-api-jobs.sqlite",
        database_echo=False,
        database_pool_size=5,
        database_max_overflow=10,
        database_pool_pre_ping=True,
        openrouter_api_key=None,
        openai_api_key=None,
        gemini_api_key=None,
        default_llm_provider="openrouter",
        default_analysis_model="analysis-model",
        default_adaptation_model="adaptation-model",
        default_transcriber_provider="whisper_local",
        default_transcriber_model="small",
        max_duration_seconds=300,
        request_timeout_seconds=300,
        celery_broker_url="memory://",
        celery_queue_name="pipeline-test",
        celery_task_soft_time_limit_seconds=1800,
        celery_task_time_limit_seconds=1860,
        accepted_input_media_types=("video/mp4", "audio/mpeg"),
        max_upload_bytes=1024 * 1024,
    )


def _principal(user_id: int = 7) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        user_id=user_id,
        email="owner@example.com",
        name="Job Owner",
        auth_provider="password",
        email_verified=True,
    )


def _upload(
    content: bytes = b"video-content",
    *,
    filename: str = "input.mp4",
) -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": "video/mp4"}),
    )


def _user_profile_payload() -> dict[str, object]:
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


def _analysis_request(**overrides: object) -> str:
    payload: dict[str, object] = {
        "pipeline_type": "copy_analysis",
        "source_type": "video",
        "language": "pt-BR",
        "need_correction": True,
    }
    payload.update(overrides)
    return json.dumps(payload)


def _adaptation_request(**overrides: object) -> str:
    payload: dict[str, object] = {
        "pipeline_type": "copy_adaptation",
        "source_type": "video",
        "user_profile": _user_profile_payload(),
    }
    payload.update(overrides)
    return json.dumps(payload)


def _start_result(
    *,
    pipeline_type: str = "copy_analysis",
) -> PipelineStartResult:
    return PipelineStartResult(
        job_id=41,
        run_id="run-41",
        status="uploaded",
        current_step="queued",
        pipeline_type=cast(PipelineType, pipeline_type),
        storage_backend="local",
        input_file_key="jobs/41/input/input.mp4",
        input_file_uri="/private/storage/jobs/41/input/input.mp4",
    )


class _PipelineServiceStub:
    """Record pipeline submissions without touching storage or the queue."""

    def __init__(self, result: PipelineStartResult | None = None) -> None:
        self.result = result or _start_result()
        self.calls: list[dict[str, Any]] = []
        self.stream_positions: list[int] = []

    async def start_from_upload(self, **kwargs: Any) -> PipelineStartResult:
        self.calls.append(kwargs)
        self.stream_positions.append(kwargs["file"].tell())
        return self.result


class _JobStoreStub:
    """Return one configured persisted job and record requested identifiers."""

    def __init__(self, job: object | None) -> None:
        self.job = job
        self.requested_job_ids: list[int] = []

    async def get_job(self, job_id: int) -> object | None:
        self.requested_job_ids.append(job_id)
        return self.job


def _persisted_job(
    *,
    user_id: int = 7,
    status_value: str = "completed",
) -> dict[str, Any]:
    return {
        "id": 41,
        "user_id": user_id,
        "run_id": "run-41",
        "pipeline_type": "copy_analysis",
        "status": status_value,
        "current_step": "completed" if status_value == "completed" else "run",
        "created_at": NOW,
        "started_at": NOW + timedelta(seconds=1),
        "finished_at": (
            NOW + timedelta(seconds=6)
            if status_value in {"completed", "failed"}
            else None
        ),
        "execution_time_seconds": (
            5.0 if status_value in {"completed", "failed"} else None
        ),
        "output_json": {
            "copy_analysis": {"main_promise": "Clear financial control"},
            "token_usage": {"total_tokens": 250},
        },
        "error_json": (
            {
                "code": "pipeline_execution_failed",
                "technical_message": "private provider failure",
            }
            if status_value == "failed"
            else None
        ),
        "input_json": {"provider_api_key": "private"},
        "storage_backend": "local",
        "input_file_key": "jobs/41/input/input.mp4",
        "input_file_uri": "/private/storage/jobs/41/input/input.mp4",
    }


def _install_upload_validator(
    monkeypatch: pytest.MonkeyPatch,
    *,
    calls: list[tuple[UploadFile, AppSettings]],
) -> None:
    async def validate(
        upload: UploadFile,
        *,
        settings: AppSettings,
    ) -> ValidatedUpload:
        calls.append((upload, settings))
        return ValidatedUpload(
            filename=cast(str, upload.filename),
            content_type=cast(str, upload.content_type),
            size_bytes=13,
            file=upload.file,
        )

    monkeypatch.setattr(jobs_module, "validate_upload", validate)


def test_submit_job_parses_analysis_request_and_validates_upload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parse analysis metadata and validate the exact multipart upload."""

    settings = _settings()
    upload = _upload()
    service = _PipelineServiceStub()
    validation_calls: list[tuple[UploadFile, AppSettings]] = []
    _install_upload_validator(monkeypatch, calls=validation_calls)

    _run(
        jobs_module.submit_job(
            upload,
            _analysis_request(),
            _principal(),
            cast(PipelineService, service),
            settings,
        )
    )

    pipeline_input = service.calls[0]["pipeline_input"]
    assert isinstance(pipeline_input, CopyAnalysisPipelineInput)
    assert pipeline_input.source_type == "video"
    assert pipeline_input.language == "pt-BR"
    assert pipeline_input.need_correction is True
    assert validation_calls == [(upload, settings)]


def test_submit_job_parses_adaptation_request_and_user_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preserve the validated offer profile in adaptation submissions."""

    service = _PipelineServiceStub(
        _start_result(pipeline_type="copy_adaptation")
    )
    _install_upload_validator(monkeypatch, calls=[])

    _run(
        jobs_module.submit_job(
            _upload(),
            _adaptation_request(),
            _principal(),
            cast(PipelineService, service),
            _settings(),
        )
    )

    pipeline_input = service.calls[0]["pipeline_input"]
    assert isinstance(pipeline_input, CopyAdaptationPipelineInput)
    assert pipeline_input.user_profile.product_or_solution == (
        "Commission planning software"
    )
    assert pipeline_input.user_profile.call_to_action == "Start the free trial"
    assert pipeline_input.adaptation_model == "adaptation-model"


def test_submit_job_uses_authenticated_user_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Derive ownership exclusively from the authenticated principal."""

    service = _PipelineServiceStub()
    _install_upload_validator(monkeypatch, calls=[])

    _run(
        jobs_module.submit_job(
            _upload(),
            _analysis_request(),
            _principal(user_id=73),
            cast(PipelineService, service),
            _settings(),
        )
    )

    assert service.calls[0]["user_id"] == 73


def test_submit_job_forwards_idempotency_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Map the idempotency header to run_id when metadata omits one."""

    service = _PipelineServiceStub()
    _install_upload_validator(monkeypatch, calls=[])

    _run(
        jobs_module.submit_job(
            _upload(),
            _analysis_request(),
            _principal(),
            cast(PipelineService, service),
            _settings(),
            idempotency_key="submission-key-41",
        )
    )

    assert service.calls[0]["pipeline_input"].run_id == "submission-key-41"


def test_submit_job_calls_pipeline_service_with_rewound_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass a stream positioned at its beginning after size validation."""

    async def run_directly(function: Any, *args: Any) -> Any:
        return function(*args)

    monkeypatch.setattr(
        uploads_module,
        "run_in_threadpool",
        run_directly,
    )
    upload = _upload(b"complete-video")
    upload.file.seek(5)
    service = _PipelineServiceStub()

    _run(
        jobs_module.submit_job(
            upload,
            _analysis_request(),
            _principal(),
            cast(PipelineService, service),
            _settings(),
        )
    )

    assert service.calls[0]["file"] is upload.file
    assert service.calls[0]["filename"] == "input.mp4"
    assert service.stream_positions == [0]


def test_submit_job_returns_202_public_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expose the submission endpoint as HTTP 202 with its public schema."""

    service = _PipelineServiceStub()
    _install_upload_validator(monkeypatch, calls=[])

    response = _run(
        jobs_module.submit_job(
            _upload(),
            _analysis_request(),
            _principal(),
            cast(PipelineService, service),
            _settings(),
        )
    )
    routes = [
        route
        for route in jobs_module.router.routes
        if isinstance(route, APIRoute) and route.endpoint is jobs_module.submit_job
    ]

    assert len(routes) == 1
    assert routes[0].status_code == status.HTTP_202_ACCEPTED
    assert routes[0].response_model is type(response)
    assert response.status == "uploaded"


def test_submit_job_does_not_return_storage_references(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Remove storage backend, key, and URI from submission responses."""

    service = _PipelineServiceStub()
    _install_upload_validator(monkeypatch, calls=[])

    response = _run(
        jobs_module.submit_job(
            _upload(),
            _analysis_request(),
            _principal(),
            cast(PipelineService, service),
            _settings(),
        )
    )
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


def test_submit_job_rejects_invalid_request_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject malformed metadata before upload validation or submission."""

    validation_calls: list[tuple[UploadFile, AppSettings]] = []
    service = _PipelineServiceStub()
    _install_upload_validator(monkeypatch, calls=validation_calls)

    with pytest.raises(
        InvalidInputError,
        match="metadata is invalid",
    ) as error_info:
        _run(
            jobs_module.submit_job(
                _upload(),
                '{"pipeline_type": "copy_analysis"',
                _principal(),
                cast(PipelineService, service),
                _settings(),
            )
        )

    assert error_info.value.step == "validating_request"
    assert validation_calls == []
    assert service.calls == []


def test_get_job_status_returns_owned_job() -> None:
    """Return public status when persisted ownership matches the caller."""

    job = _persisted_job(status_value="running")
    store = _JobStoreStub(job)

    response = _run(
        jobs_module.get_job_status(
            41,
            _principal(),
            cast(JobStoreBase, store),
        )
    )

    assert store.requested_job_ids == [41]
    assert response.job_id == 41
    assert response.status == "running"
    assert response.pipeline_type == "copy_analysis"


def test_get_job_status_rejects_missing_job() -> None:
    """Return the stable not-found error when persistence has no job."""

    store = _JobStoreStub(None)

    with pytest.raises(JobNotFoundError) as error_info:
        _run(
            jobs_module.get_job_status(
                404,
                _principal(),
                cast(JobStoreBase, store),
            )
        )

    assert error_info.value.details == {"job_id": 404}


def test_get_job_status_hides_job_owned_by_another_user() -> None:
    """Treat another user's job as absent to prevent ownership disclosure."""

    store = _JobStoreStub(_persisted_job(user_id=99))

    with pytest.raises(JobNotFoundError) as error_info:
        _run(
            jobs_module.get_job_status(
                41,
                _principal(user_id=7),
                cast(JobStoreBase, store),
            )
        )

    assert error_info.value.details == {"job_id": 41}


def test_get_job_result_returns_completed_owned_job() -> None:
    """Return only persisted output for an owned completed job."""

    store = _JobStoreStub(_persisted_job())

    response = _run(
        jobs_module.get_job_result(
            41,
            _principal(),
            cast(JobStoreBase, store),
        )
    )

    assert response.job_id == 41
    assert response.status == "completed"
    assert response.output == {
        "copy_analysis": {"main_promise": "Clear financial control"},
        "token_usage": {"total_tokens": 250},
    }


def test_get_job_result_rejects_incomplete_job() -> None:
    """Reject result access until the owned job reaches completion."""

    store = _JobStoreStub(_persisted_job(status_value="running"))

    with pytest.raises(JobResultNotReadyError) as error_info:
        _run(
            jobs_module.get_job_result(
                41,
                _principal(),
                cast(JobStoreBase, store),
            )
        )

    assert error_info.value.details == {
        "job_id": 41,
        "status": "running",
    }


def test_get_job_result_hides_job_owned_by_another_user() -> None:
    """Return not-found rather than exposing another user's completed result."""

    store = _JobStoreStub(_persisted_job(user_id=99))

    with pytest.raises(JobNotFoundError):
        _run(
            jobs_module.get_job_result(
                41,
                _principal(user_id=7),
                cast(JobStoreBase, store),
            )
        )


def test_job_responses_do_not_expose_input_or_storage_fields() -> None:
    """Keep persisted input and storage metadata out of status and result."""

    job = _persisted_job()
    status_response = _run(
        jobs_module.get_job_status(
            41,
            _principal(),
            cast(JobStoreBase, _JobStoreStub(job)),
        )
    )
    result_response = _run(
        jobs_module.get_job_result(
            41,
            _principal(),
            cast(JobStoreBase, _JobStoreStub(job)),
        )
    )

    serialized_responses = (
        status_response.model_dump_json() + result_response.model_dump_json()
    )

    assert "input_json" not in serialized_responses
    assert "storage_backend" not in serialized_responses
    assert "input_file_key" not in serialized_responses
    assert "input_file_uri" not in serialized_responses
    assert "/private/storage" not in serialized_responses
