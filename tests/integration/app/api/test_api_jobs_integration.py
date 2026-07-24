"""Integration tests for authenticated pipeline job HTTP endpoints."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Coroutine
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, TypeVar
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.main import create_app
from app.auth.dependencies import get_current_user
from app.auth.principal import AuthenticatedPrincipal
from app.errors import PipelineExecutionError, StorageError
from app.queue.base import QueueBase
from app.settings import AppSettings
from app.storage.base import StoredFile
from app.storage.local import LocalStorage
from app.store.jobs import (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_UPLOADED,
    SQLAlchemyJobStore,
)
from app.store.models import Job
from app.store.users import SQLAlchemyUserStore


API_BASE_URL = "https://api.example.com"
BeforeEnqueue = Callable[[int], Awaitable[None]]
ResultT = TypeVar("ResultT")


def _run_async(coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    """Execute one asynchronous HTTP integration scenario."""

    return asyncio.run(coroutine)


class RecordingQueue(QueueBase):
    """Record enqueue attempts and optionally inspect or reject them."""

    def __init__(
        self,
        *,
        before_enqueue: BeforeEnqueue | None = None,
        error: Exception | None = None,
    ) -> None:
        self.before_enqueue = before_enqueue
        self.error = error
        self.attempted_job_ids: list[int] = []
        self.queued_job_ids: list[int] = []

    async def enqueue(self, job_id: int) -> None:
        self.attempted_job_ids.append(job_id)

        if self.before_enqueue is not None:
            await self.before_enqueue(job_id)

        if self.error is not None:
            raise self.error

        self.queued_job_ids.append(job_id)


class FailingUploadStorage(LocalStorage):
    """Fail input persistence with one controlled retryable storage error."""

    def save_upload(
        self,
        file: BinaryIO,
        destination_key: str,
    ) -> StoredFile:
        del file
        raise StorageError(
            technical_message="Integration upload failure.",
            details={
                "destination_key": destination_key,
                "retryable": True,
            },
        )


def _settings(
    *,
    database_url: str,
    storage_dir: Path,
) -> AppSettings:
    """Return complete settings for the in-process integration API."""

    return AppSettings(
        environment="test",
        storage_dir=storage_dir,
        sqlite_path=storage_dir / "unused.sqlite",
        database_url=database_url,
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


def _application(
    *,
    settings: AppSettings,
    session_factory: async_sessionmaker[AsyncSession],
    storage: LocalStorage,
    queue: QueueBase,
    principal: AuthenticatedPrincipal,
) -> FastAPI:
    """Compose the production API with controlled integration resources."""

    application = create_app(settings)
    application.state.session_factory = session_factory
    application.state.storage = storage
    application.state.queue = queue
    _authenticate_as(application, principal)
    return application


def _authenticate_as(
    application: FastAPI,
    principal: AuthenticatedPrincipal,
) -> None:
    """Override authentication with one already-persisted test identity."""

    async def current_user() -> AuthenticatedPrincipal:
        return principal

    application.dependency_overrides[get_current_user] = current_user


def _transport(application: FastAPI) -> httpx.ASGITransport:
    return httpx.ASGITransport(
        app=application,
        raise_app_exceptions=False,
    )


async def _create_user(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    label: str,
) -> AuthenticatedPrincipal:
    """Persist one user and return the matching authenticated principal."""

    email = f"{label}-{uuid4().hex}@example.com"

    async with session_factory.begin() as session:
        user = await SQLAlchemyUserStore(session).create_user(
            {
                "email": email,
                "password_hash": "integration-password-hash",
                "name": label.title(),
                "email_verified_at": datetime.now(timezone.utc),
            }
        )

    return AuthenticatedPrincipal(
        user_id=user.id,
        email=user.email,
        name=user.name,
        auth_provider=user.auth_provider,
        email_verified=True,
    )


async def _get_job(
    session_factory: async_sessionmaker[AsyncSession],
    job_id: int,
) -> Job | None:
    async with session_factory() as session:
        return await SQLAlchemyJobStore(session).get_job(job_id)


async def _get_job_by_run_id(
    session_factory: async_sessionmaker[AsyncSession],
    run_id: str,
) -> Job | None:
    async with session_factory() as session:
        return await SQLAlchemyJobStore(session).get_job_by_run_id(run_id)


async def _complete_job(
    session_factory: async_sessionmaker[AsyncSession],
    job_id: int,
    output: dict[str, Any],
) -> None:
    """Apply the same durable transitions used by the worker."""

    async with session_factory.begin() as session:
        store = SQLAlchemyJobStore(session)
        await store.mark_running(job_id, "running_pipeline")
        await store.mark_completed(job_id, output)


def _analysis_request(*, run_id: str | None = None) -> dict[str, Any]:
    request: dict[str, Any] = {
        "pipeline_type": "copy_analysis",
        "source_type": "video",
        "language": "pt-BR",
        "output_formats": ["json"],
    }

    if run_id is not None:
        request["run_id"] = run_id

    return request


def _adaptation_request(*, run_id: str) -> dict[str, Any]:
    return {
        "pipeline_type": "copy_adaptation",
        "source_type": "video",
        "run_id": run_id,
        "user_profile": {
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
        },
    }


async def _submit_job(
    client: httpx.AsyncClient,
    request_payload: dict[str, Any] | str,
    *,
    content: bytes = b"integration-video",
    content_type: str = "video/mp4",
) -> httpx.Response:
    request_json = (
        request_payload
        if isinstance(request_payload, str)
        else json.dumps(request_payload)
    )
    return await client.post(
        "/v1/jobs",
        data={"request": request_json},
        files={"file": ("input.mp4", content, content_type)},
    )


def test_analysis_upload_persists_file_job_and_queue_message(
    api_database_url: str,
    api_session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """Submit analysis through HTTP and persist every startup checkpoint."""

    async def scenario() -> None:
        principal = await _create_user(
            api_session_factory,
            label="analysis-owner",
        )
        storage = LocalStorage(tmp_path / "storage")
        queue = RecordingQueue()
        application = _application(
            settings=_settings(
                database_url=api_database_url,
                storage_dir=tmp_path / "storage",
            ),
            session_factory=api_session_factory,
            storage=storage,
            queue=queue,
            principal=principal,
        )

        async with httpx.AsyncClient(
            transport=_transport(application),
            base_url=API_BASE_URL,
        ) as client:
            response = await _submit_job(client, _analysis_request())

        assert response.status_code == 202
        payload = response.json()
        job = await _get_job(api_session_factory, payload["job_id"])

        assert job is not None
        assert job.user_id == principal.user_id
        assert job.status == JOB_STATUS_UPLOADED
        assert job.storage_backend == "local"
        assert job.input_file_key == f"jobs/{job.id}/input.mp4"
        assert storage.exists(job.input_file_key)
        assert Path(job.input_file_uri or "").read_bytes() == (
            b"integration-video"
        )
        assert queue.queued_job_ids == [job.id]

    _run_async(scenario())


def test_adaptation_upload_persists_normalized_user_profile(
    api_database_url: str,
    api_session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """Persist adaptation-specific profile data in normalized job input."""

    async def scenario() -> None:
        principal = await _create_user(
            api_session_factory,
            label="adaptation-owner",
        )
        queue = RecordingQueue()
        storage = LocalStorage(tmp_path / "storage")
        run_id = f"adaptation-{uuid4().hex}"
        application = _application(
            settings=_settings(
                database_url=api_database_url,
                storage_dir=tmp_path / "storage",
            ),
            session_factory=api_session_factory,
            storage=storage,
            queue=queue,
            principal=principal,
        )

        async with httpx.AsyncClient(
            transport=_transport(application),
            base_url=API_BASE_URL,
        ) as client:
            response = await _submit_job(
                client,
                _adaptation_request(run_id=run_id),
            )

        assert response.status_code == 202
        job = await _get_job_by_run_id(api_session_factory, run_id)

        assert job is not None
        assert job.pipeline_type == "copy_adaptation"
        assert job.input_json["adaptation_model"] == "adaptation-model"
        assert job.input_json["user_profile"]["main_promise"] == (
            "Organize variable income with a clear plan"
        )
        assert "password_hash" not in json.dumps(job.input_json)

    _run_async(scenario())


def test_upload_failure_persists_failed_job_and_public_error(
    api_database_url: str,
    api_session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """Persist failure when storage rejects an upload after job creation."""

    async def scenario() -> None:
        principal = await _create_user(
            api_session_factory,
            label="upload-failure-owner",
        )
        run_id = f"upload-failure-{uuid4().hex}"
        queue = RecordingQueue()
        application = _application(
            settings=_settings(
                database_url=api_database_url,
                storage_dir=tmp_path / "storage",
            ),
            session_factory=api_session_factory,
            storage=FailingUploadStorage(tmp_path / "storage"),
            queue=queue,
            principal=principal,
        )

        async with httpx.AsyncClient(
            transport=_transport(application),
            base_url=API_BASE_URL,
        ) as client:
            response = await _submit_job(
                client,
                _analysis_request(run_id=run_id),
            )

        job = await _get_job_by_run_id(api_session_factory, run_id)

        assert response.status_code == 503
        assert response.json()["code"] == "storage_error"
        assert "Integration upload failure" not in response.text
        assert job is not None
        assert job.status == JOB_STATUS_FAILED
        assert job.error_json is not None
        assert job.error_json["code"] == "storage_error"
        assert queue.attempted_job_ids == []

    _run_async(scenario())


def test_queue_failure_persists_failed_job_and_public_error(
    api_database_url: str,
    api_session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """Persist failure when an uploaded job cannot be sent to the broker."""

    async def scenario() -> None:
        principal = await _create_user(
            api_session_factory,
            label="queue-failure-owner",
        )
        run_id = f"queue-failure-{uuid4().hex}"
        queue = RecordingQueue(
            error=PipelineExecutionError(
                technical_message="Integration broker failure.",
                step="enqueue_job",
                details={"retryable": True},
            )
        )
        storage = LocalStorage(tmp_path / "storage")
        application = _application(
            settings=_settings(
                database_url=api_database_url,
                storage_dir=tmp_path / "storage",
            ),
            session_factory=api_session_factory,
            storage=storage,
            queue=queue,
            principal=principal,
        )

        async with httpx.AsyncClient(
            transport=_transport(application),
            base_url=API_BASE_URL,
        ) as client:
            response = await _submit_job(
                client,
                _analysis_request(run_id=run_id),
            )

        job = await _get_job_by_run_id(api_session_factory, run_id)

        assert response.status_code == 503
        assert response.json()["code"] == "pipeline_execution_failed"
        assert "Integration broker failure" not in response.text
        assert job is not None
        assert job.status == JOB_STATUS_FAILED
        assert job.error_json is not None
        assert job.error_json["code"] == "pipeline_execution_failed"
        assert queue.attempted_job_ids == [job.id]

    _run_async(scenario())


def test_uploaded_transition_is_committed_before_enqueue(
    api_database_url: str,
    api_session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """Make uploaded state visible to a new session before queue invocation."""

    async def scenario() -> None:
        observed_statuses: list[str] = []

        async def inspect_committed_job(job_id: int) -> None:
            job = await _get_job(api_session_factory, job_id)
            assert job is not None
            observed_statuses.append(job.status)

        principal = await _create_user(
            api_session_factory,
            label="commit-owner",
        )
        queue = RecordingQueue(before_enqueue=inspect_committed_job)
        application = _application(
            settings=_settings(
                database_url=api_database_url,
                storage_dir=tmp_path / "storage",
            ),
            session_factory=api_session_factory,
            storage=LocalStorage(tmp_path / "storage"),
            queue=queue,
            principal=principal,
        )

        async with httpx.AsyncClient(
            transport=_transport(application),
            base_url=API_BASE_URL,
        ) as client:
            response = await _submit_job(client, _analysis_request())

        assert response.status_code == 202
        assert observed_statuses == [JOB_STATUS_UPLOADED]

    _run_async(scenario())


def test_public_job_responses_hide_local_storage_paths(
    api_database_url: str,
    api_session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """Keep internal file references out of submission and status responses."""

    async def scenario() -> None:
        principal = await _create_user(
            api_session_factory,
            label="privacy-owner",
        )
        storage_root = tmp_path / "private-storage"
        application = _application(
            settings=_settings(
                database_url=api_database_url,
                storage_dir=storage_root,
            ),
            session_factory=api_session_factory,
            storage=LocalStorage(storage_root),
            queue=RecordingQueue(),
            principal=principal,
        )

        async with httpx.AsyncClient(
            transport=_transport(application),
            base_url=API_BASE_URL,
        ) as client:
            submission = await _submit_job(client, _analysis_request())
            status_response = await client.get(
                f"/v1/jobs/{submission.json()['job_id']}"
            )

        combined_response = submission.text + status_response.text

        assert submission.status_code == 202
        assert status_response.status_code == 200
        assert str(storage_root) not in combined_response
        assert "input_file_key" not in combined_response
        assert "input_file_uri" not in combined_response
        assert "storage_backend" not in combined_response

    _run_async(scenario())


def test_user_cannot_read_another_users_job_or_result(
    api_database_url: str,
    api_session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """Return identical not-found responses for foreign status and result."""

    async def scenario() -> None:
        owner = await _create_user(api_session_factory, label="owner")
        stranger = await _create_user(api_session_factory, label="stranger")
        application = _application(
            settings=_settings(
                database_url=api_database_url,
                storage_dir=tmp_path / "storage",
            ),
            session_factory=api_session_factory,
            storage=LocalStorage(tmp_path / "storage"),
            queue=RecordingQueue(),
            principal=owner,
        )

        async with httpx.AsyncClient(
            transport=_transport(application),
            base_url=API_BASE_URL,
        ) as client:
            submission = await _submit_job(client, _analysis_request())
            job_id = submission.json()["job_id"]
            _authenticate_as(application, stranger)
            status_response = await client.get(f"/v1/jobs/{job_id}")
            result_response = await client.get(
                f"/v1/jobs/{job_id}/result"
            )

        assert status_response.status_code == 404
        assert result_response.status_code == 404
        assert status_response.json() == result_response.json()
        assert status_response.json()["code"] == "job_not_found"

    _run_async(scenario())


def test_incomplete_result_returns_conflict(
    api_database_url: str,
    api_session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """Return a controlled conflict while the persisted job is uploaded."""

    async def scenario() -> None:
        principal = await _create_user(
            api_session_factory,
            label="incomplete-owner",
        )
        application = _application(
            settings=_settings(
                database_url=api_database_url,
                storage_dir=tmp_path / "storage",
            ),
            session_factory=api_session_factory,
            storage=LocalStorage(tmp_path / "storage"),
            queue=RecordingQueue(),
            principal=principal,
        )

        async with httpx.AsyncClient(
            transport=_transport(application),
            base_url=API_BASE_URL,
        ) as client:
            submission = await _submit_job(client, _analysis_request())
            job_id = submission.json()["job_id"]
            response = await client.get(f"/v1/jobs/{job_id}/result")

        assert response.status_code == 409
        assert response.json() == {
            "code": "job_result_not_ready",
            "step": "loading_job_result",
            "details": {
                "job_id": job_id,
                "status": JOB_STATUS_UPLOADED,
            },
        }

    _run_async(scenario())


def test_completed_result_returns_persisted_public_output(
    api_database_url: str,
    api_session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """Read completed output from the database through the HTTP contract."""

    async def scenario() -> None:
        principal = await _create_user(
            api_session_factory,
            label="completed-owner",
        )
        application = _application(
            settings=_settings(
                database_url=api_database_url,
                storage_dir=tmp_path / "storage",
            ),
            session_factory=api_session_factory,
            storage=LocalStorage(tmp_path / "storage"),
            queue=RecordingQueue(),
            principal=principal,
        )

        async with httpx.AsyncClient(
            transport=_transport(application),
            base_url=API_BASE_URL,
        ) as client:
            submission = await _submit_job(client, _analysis_request())
            job_id = submission.json()["job_id"]
            expected_output = {
                "copy_analysis": {"main_promise": "Clear financial control"},
                "token_usage": {"total_tokens": 250},
                "execution_time_seconds": 2.5,
            }
            await _complete_job(
                api_session_factory,
                job_id,
                expected_output,
            )
            response = await client.get(f"/v1/jobs/{job_id}/result")

        assert response.status_code == 200
        assert response.json() == {
            "job_id": job_id,
            "run_id": None,
            "pipeline_type": "copy_analysis",
            "status": JOB_STATUS_COMPLETED,
            "output": expected_output,
        }

    _run_async(scenario())


@pytest.mark.parametrize(
    ("request_payload", "content_type", "expected_status", "expected_code"),
    [
        (
            '{"pipeline_type": "copy_analysis"',
            "video/mp4",
            422,
            "invalid_input",
        ),
        (
            _analysis_request(),
            "text/plain",
            415,
            "unsupported_media_type",
        ),
    ],
)
def test_invalid_requests_use_stable_public_error_contract(
    request_payload: dict[str, Any] | str,
    content_type: str,
    expected_status: int,
    expected_code: str,
    api_database_url: str,
    api_session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """Translate invalid multipart input without exposing internal details."""

    async def scenario() -> None:
        principal = await _create_user(
            api_session_factory,
            label="invalid-request-owner",
        )
        storage_root = tmp_path / "private-storage"
        application = _application(
            settings=_settings(
                database_url=api_database_url,
                storage_dir=storage_root,
            ),
            session_factory=api_session_factory,
            storage=LocalStorage(storage_root),
            queue=RecordingQueue(),
            principal=principal,
        )

        async with httpx.AsyncClient(
            transport=_transport(application),
            base_url=API_BASE_URL,
        ) as client:
            response = await _submit_job(
                client,
                request_payload,
                content_type=content_type,
            )

        assert response.status_code == expected_status
        assert response.json()["code"] == expected_code
        assert "technical_message" not in response.text
        assert str(storage_root) not in response.text

    _run_async(scenario())
