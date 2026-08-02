"""Unit tests for app job store behavior.

These tests cover input validation, transition intent, and controlled error
wrapping without opening a real database connection. Real SQL execution belongs
to integration tests.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager
from typing import Any, cast

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

import app.store.jobs as jobs
from app.errors import JobStoreError
from app.store.jobs import SQLAlchemyJobStore
from app.store.models import Job


def _run_async(awaitable: Any) -> Any:
    """Run an async store method from a synchronous unit test."""

    return asyncio.run(awaitable)


def _store(session: object | None = None) -> SQLAlchemyJobStore:
    """Build a job store around a typed fake session."""

    return SQLAlchemyJobStore(cast(AsyncSession, session or object()))


class _NoRowResult:
    """SQLAlchemy result fake that represents an update with no returned row."""

    def scalar_one_or_none(self) -> None:
        return None


class _ExecuteNoRowSession:
    """Session fake used when a transition update affects no job."""

    async def execute(self, statement: object) -> _NoRowResult:
        self.statement = statement
        return _NoRowResult()


class _GetNoneSession:
    """Session fake whose get operation does not find a model."""

    async def get(self, model: type[object], model_id: int) -> None:
        self.model = model
        self.model_id = model_id
        return None


class _GetRaisesSession:
    """Session fake that raises a SQLAlchemy infrastructure error."""

    async def get(self, model: type[object], model_id: int) -> None:
        raise SQLAlchemyError("database failed")


class _ScalarsResult:
    """SQLAlchemy result fake for list queries."""

    def __init__(self, rows: list[Job] | None = None) -> None:
        self._rows = rows or []

    def scalars(self) -> "_ScalarsResult":
        return self

    def all(self) -> list[Job]:
        return self._rows


class _ExecuteListSession:
    """Session fake that captures the select statement used by list_user_jobs."""

    def __init__(self, rows: list[Job] | None = None) -> None:
        self.statement: object | None = None
        self.rows = rows or []

    async def execute(self, statement: object) -> _ScalarsResult:
        self.statement = statement
        return _ScalarsResult(self.rows)


class _CreateJobSession:
    """Session fake for create_job without a real transaction or database."""

    def __init__(self) -> None:
        self.added: list[Job] = []
        self.flush_called = False

    def add(self, instance: Job) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        self.flush_called = True


class _TransitionSpyJobStore(SQLAlchemyJobStore):
    """Store spy that records transition helper calls."""

    def __init__(self) -> None:
        super().__init__(cast(AsyncSession, object()))
        self.transition_calls: list[dict[str, Any]] = []

    async def _transition_job(
        self,
        *,
        job_id: int,
        operation: str,
        allowed_statuses: Sequence[str],
        values: Mapping[str, Any],
    ) -> Job:
        self.transition_calls.append(
            {
                "job_id": job_id,
                "operation": operation,
                "allowed_statuses": tuple(allowed_statuses),
                "values": dict(values),
            }
        )
        return cast(Job, object())


def test_create_job_requires_user_id() -> None:
    """create_job should reject payloads without a user identifier."""

    store = _store()

    with pytest.raises(JobStoreError) as error:
        _run_async(
            store.create_job(
                {
                    "pipeline_type": "copy_adaptation",
                    "input_json": {"source": "video.mp4"},
                }
            )
        )

    assert error.value.details == {
        "operation": "create_job",
        "field": "user_id",
        "value": None,
    }


def test_create_job_requires_pipeline_type() -> None:
    """create_job should reject payloads without a pipeline type."""

    store = _store()

    with pytest.raises(JobStoreError) as error:
        _run_async(
            store.create_job(
                {
                    "user_id": 1,
                    "input_json": {"source": "video.mp4"},
                }
            )
        )

    assert error.value.details == {
        "operation": "create_job",
        "field": "pipeline_type",
    }


def test_create_job_requires_input_json_object() -> None:
    """create_job should accept only object-like input_json payloads."""

    store = _store()

    with pytest.raises(JobStoreError) as error:
        _run_async(
            store.create_job(
                {
                    "user_id": 1,
                    "pipeline_type": "copy_adaptation",
                    "input_json": ["not", "an", "object"],
                }
            )
        )

    assert error.value.details == {
        "operation": "create_job",
        "field": "input_json",
    }


def test_create_job_normalizes_blank_run_id_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blank run_id values should not be persisted as empty strings."""

    @asynccontextmanager
    async def fake_savepoint(session: object) -> AsyncIterator[object]:
        yield session

    monkeypatch.setattr(jobs, "async_savepoint_scope", fake_savepoint)
    session = _CreateJobSession()
    store = _store(session)

    job = cast(
        Job,
        _run_async(
            store.create_job(
                {
                    "user_id": 1,
                    "run_id": "   ",
                    "pipeline_type": "copy_adaptation",
                    "input_json": {"source": "video.mp4"},
                }
            )
        )
    )

    assert job.run_id is None
    assert session.added == [job]
    assert session.flush_called is True


def test_mark_uploaded_requires_storage_backend_and_input_file_references() -> None:
    """mark_uploaded should require all input storage references."""

    store = _store()
    valid_payload = {
        "storage_backend": "local",
        "input_file_key": "jobs/run/input.mp4",
        "input_file_uri": "/storage/jobs/run/input.mp4",
    }

    for field in valid_payload:
        payload = dict(valid_payload)
        payload.pop(field)

        with pytest.raises(JobStoreError) as error:
            _run_async(store.mark_uploaded(1, payload))

        assert error.value.details == {
            "operation": "mark_uploaded",
            "field": field,
        }


def test_mark_running_rejects_invalid_transition_when_update_returns_no_row() -> None:
    """A guarded transition with no updated row should raise JobStoreError."""

    store = _store(_ExecuteNoRowSession())

    with pytest.raises(JobStoreError) as error:
        _run_async(store.mark_running(1, "transcribing"))

    assert error.value.details == {
        "operation": "mark_running",
        "job_id": 1,
        "allowed_statuses": [jobs.JOB_STATUS_UPLOADED],
    }


def test_mark_completed_uses_running_as_allowed_status() -> None:
    """mark_completed should only finalize jobs currently in running status."""

    store = _TransitionSpyJobStore()

    _run_async(
        store.mark_completed(
            1,
            {
                "result": {"script": "final"},
                "token_usage": {"total": 10},
                "execution_time_seconds": 12.5,
            },
        )
    )

    assert store.transition_calls[0]["operation"] == "mark_completed"
    assert store.transition_calls[0]["allowed_statuses"] == (
        jobs.JOB_STATUS_RUNNING,
    )


def test_mark_failed_accepts_pending_uploaded_and_running() -> None:
    """mark_failed should be valid before, during, or after upload starts."""

    store = _TransitionSpyJobStore()

    _run_async(
        store.mark_failed(
            1,
            {
                "code": "pipeline_execution_failed",
                "step": "copy_analysis",
            },
        )
    )

    assert store.transition_calls[0]["operation"] == "mark_failed"
    assert store.transition_calls[0]["allowed_statuses"] == (
        jobs.JOB_STATUS_PENDING,
        jobs.JOB_STATUS_UPLOADED,
        jobs.JOB_STATUS_RUNNING,
    )


def test_list_user_jobs_rejects_non_positive_limit() -> None:
    """list_user_jobs should reject zero or negative limits."""

    store = _store()

    for invalid_limit in (0, -1):
        with pytest.raises(JobStoreError) as error:
            _run_async(store.list_user_jobs(1, limit=invalid_limit))

        assert error.value.details == {
            "operation": "list_user_jobs",
            "limit": invalid_limit,
        }


def test_list_user_jobs_caps_limit_to_maximum() -> None:
    """list_user_jobs should cap large limits to MAX_PAGE_LIMIT."""

    session = _ExecuteListSession()
    store = _store(session)

    result = _run_async(
        store.list_user_jobs(1, limit=jobs.MAX_PAGE_LIMIT + 500)
    )

    assert result.items == ()
    assert result.has_more is False
    assert session.statement is not None
    limit_clause = getattr(session.statement, "_limit_clause")
    assert getattr(limit_clause, "value") == jobs.MAX_PAGE_LIMIT + 1


def test_list_user_jobs_rejects_negative_offset() -> None:
    """list_user_jobs should reject negative offsets."""

    store = _store()

    with pytest.raises(JobStoreError) as error:
        _run_async(store.list_user_jobs(1, offset=-1))

    assert error.value.details == {
        "operation": "list_user_jobs",
        "offset": -1,
    }


def test_list_user_jobs_filters_in_sql_and_uses_stable_order() -> None:
    """Owner and optional filters should be part of the database statement."""

    session = _ExecuteListSession()
    store = _store(session)

    _run_async(
        store.list_user_jobs(
            7,
            job_id=41,
            status="running",
            pipeline_type="copy_analysis",
            limit=20,
            offset=5,
        )
    )

    assert session.statement is not None
    statement_text = str(session.statement)
    statement_parameters = session.statement.compile().params

    assert "jobs.user_id" in statement_text
    assert "jobs.id" in statement_text
    assert "jobs.status" in statement_text
    assert "jobs.pipeline_type" in statement_text
    assert "ORDER BY jobs.created_at DESC, jobs.id DESC" in statement_text
    assert {7, 41, "running", "copy_analysis"} <= set(
        statement_parameters.values()
    )


def test_list_user_jobs_reports_and_removes_extra_page_row() -> None:
    """One extra SQL row should indicate another page without leaking it."""

    rows = [Job(id=1), Job(id=2), Job(id=3)]
    store = _store(_ExecuteListSession(rows))

    page = _run_async(store.list_user_jobs(7, limit=2))

    assert tuple(job.id for job in page.items) == (1, 2)
    assert page.has_more is True


@pytest.mark.parametrize("status", ["", "queued", "COMPLETED_JOB"])
def test_list_user_jobs_rejects_unsupported_status(status: str) -> None:
    """Store callers cannot bypass the public lifecycle status allowlist."""

    with pytest.raises(JobStoreError):
        _run_async(_store().list_user_jobs(1, status=status))


def test_list_user_jobs_rejects_unsupported_pipeline_type() -> None:
    """Store callers cannot query an unknown pipeline type."""

    with pytest.raises(JobStoreError):
        _run_async(_store().list_user_jobs(1, pipeline_type="unknown"))


def test_get_job_returns_none_when_session_get_returns_none() -> None:
    """get_job should return None when the session cannot find the job."""

    session = _GetNoneSession()
    store = _store(session)

    result = cast(Job | None, _run_async(store.get_job(123)))

    assert result is None
    assert session.model is Job
    assert session.model_id == 123


def test_sqlalchemy_errors_are_wrapped_as_job_store_error() -> None:
    """SQLAlchemy infrastructure errors should become controlled store errors."""

    store = _store(_GetRaisesSession())

    with pytest.raises(JobStoreError) as error:
        _run_async(store.get_job(123))

    assert error.value.details == {
        "operation": "get_job",
        "job_id": 123,
        "error_type": "SQLAlchemyError",
    }
