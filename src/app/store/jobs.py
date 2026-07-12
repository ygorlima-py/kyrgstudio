"""Job persistence for the application store.

This module stores product-level job state. It does not execute workflows,
commit transactions, upload files, or read binary storage. Callers must pass an
active ``AsyncSession`` and control commit/rollback outside this class.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import JobStoreError
from app.store.base import JobStoreBase
from app.store.database import async_savepoint_scope
from app.store.models import Job, JobEvent


DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100

JOB_STATUS_PENDING = "pending"
JOB_STATUS_UPLOADED = "uploaded"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"

STEP_CREATED = "created"
STEP_UPLOADED = "uploaded"
STEP_RUNNING = "running"
STEP_COMPLETED = "completed"
STEP_FAILED = "failed"

EVENT_STEP_COMPLETED = "step_completed"


class SQLAlchemyJobStore(JobStoreBase):
    """SQLAlchemy implementation of job persistence.

    The store uses atomic conditional updates for status transitions. This
    prevents two workers from finalizing or moving the same job at the same
    time with stale state.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_job(self, payload: dict[str, Any]) -> Job:
        """Create a job or return the existing one for the same ``run_id``.

        ``run_id`` is optional. When it is provided, it acts as an idempotency
        key for repeated client requests.
        """

        operation = "create_job"
        user_id = _required_int(payload, "user_id", operation=operation)
        pipeline_type = _required_str(payload, "pipeline_type", operation=operation)
        input_json = _required_mapping(payload, "input_json", operation=operation)
        run_id = _optional_str(payload.get("run_id"))

        job = Job(
            user_id=user_id,
            run_id=run_id,
            status=JOB_STATUS_PENDING,
            current_step=STEP_CREATED,
            pipeline_type=pipeline_type,
            input_json=dict(input_json),
        )

        try:
            async with async_savepoint_scope(self.session):
                self.session.add(job)
                await self.session.flush()
        except IntegrityError as error:
            if run_id is None:
                raise _job_store_error(
                    operation,
                    "Failed to create job because a database constraint failed.",
                    details={"user_id": user_id, "pipeline_type": pipeline_type},
                    error=error,
                )

            existing_job = await self.get_job_by_run_id(run_id)

            if existing_job is not None:
                return existing_job

            raise _job_store_error(
                operation,
                "Job run_id conflict occurred, but the existing job was not found.",
                details={"run_id": run_id},
                error=error,
            )
        except SQLAlchemyError as error:
            raise _job_store_error(
                operation,
                "Failed to create job.",
                details={"user_id": user_id, "pipeline_type": pipeline_type},
                error=error,
            )

        return job

    async def mark_uploaded(self, job_id: int, payload: dict[str, Any]) -> Job:
        """Save input file references and move a job from pending to uploaded."""

        operation = "mark_uploaded"
        storage_backend = _required_str(payload, "storage_backend", operation=operation)
        input_file_key = _required_str(payload, "input_file_key", operation=operation)
        input_file_uri = _required_str(payload, "input_file_uri", operation=operation)

        return await self._transition_job(
            job_id=job_id,
            operation=operation,
            allowed_statuses=(JOB_STATUS_PENDING,),
            values={
                "status": JOB_STATUS_UPLOADED,
                "current_step": STEP_UPLOADED,
                "storage_backend": storage_backend,
                "input_file_key": input_file_key,
                "input_file_uri": input_file_uri,
            },
        )

    async def mark_running(self, job_id: int, step: str) -> Job:
        """Move an uploaded job to running."""

        operation = "mark_running"
        normalized_step = _normalize_step(step, fallback=STEP_RUNNING)

        return await self._transition_job(
            job_id=job_id,
            operation=operation,
            allowed_statuses=(JOB_STATUS_UPLOADED,),
            values={
                "status": JOB_STATUS_RUNNING,
                "current_step": normalized_step,
                "started_at": func.now(),
            },
        )

    async def mark_step_completed(
        self,
        job_id: int,
        step: str,
        payload: dict[str, Any] | None = None,
    ) -> Job:
        """Register a completed workflow step for a running job."""

        operation = "mark_step_completed"
        normalized_step = _normalize_step(step, fallback=STEP_RUNNING)
        event_payload = dict(payload or {})

        try:
            job = await self._transition_job(
                job_id=job_id,
                operation=operation,
                allowed_statuses=(JOB_STATUS_RUNNING,),
                values={"current_step": normalized_step},
            )
            self.session.add(
                JobEvent(
                    job_id=job_id,
                    step=normalized_step,
                    event_type=EVENT_STEP_COMPLETED,
                    payload_json=event_payload or None,
                )
            )
            await self.session.flush()
            return job
        except SQLAlchemyError as error:
            raise _job_store_error(
                operation,
                "Failed to mark job step as completed.",
                details={"job_id": job_id, "step": normalized_step},
                error=error,
            )

    async def mark_completed(self, job_id: int, output: dict[str, Any]) -> Job:
        """Save final output and move a running job to completed."""

        operation = "mark_completed"

        return await self._transition_job(
            job_id=job_id,
            operation=operation,
            allowed_statuses=(JOB_STATUS_RUNNING,),
            values={
                "status": JOB_STATUS_COMPLETED,
                "current_step": STEP_COMPLETED,
                "output_json": output,
                "token_usage_json": _optional_mapping(output.get("token_usage")),
                "execution_time_seconds": _optional_float(
                    output.get("execution_time_seconds")
                ),
                "finished_at": func.now(),
            },
        )

    async def mark_failed(self, job_id: int, error: dict[str, Any]) -> Job:
        """Save a controlled error and move a job to failed."""

        operation = "mark_failed"

        return await self._transition_job(
            job_id=job_id,
            operation=operation,
            allowed_statuses=(
                JOB_STATUS_PENDING,
                JOB_STATUS_UPLOADED,
                JOB_STATUS_RUNNING,
            ),
            values={
                "status": JOB_STATUS_FAILED,
                "current_step": _error_step(error),
                "error_json": error,
                "finished_at": func.now(),
            },
        )

    async def get_job(self, job_id: int) -> Job | None:
        """Return a job by internal id, or ``None`` when it does not exist."""

        operation = "get_job"

        try:
            return await self.session.get(Job, job_id)
        except SQLAlchemyError as error:
            raise _job_store_error(
                operation,
                "Failed to get job.",
                details={"job_id": job_id},
                error=error,
            )

    async def get_user_job(self, user_id: int, job_id: int) -> Job | None:
        """Return a job only when it belongs to the given user."""

        operation = "get_user_job"

        try:
            result = await self.session.execute(
                select(Job).where(Job.id == job_id, Job.user_id == user_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as error:
            raise _job_store_error(
                operation,
                "Failed to get user job.",
                details={"user_id": user_id, "job_id": job_id},
                error=error,
            )

    async def get_job_by_run_id(self, run_id: str) -> Job | None:
        """Return a job by idempotency key, or ``None`` when absent."""

        operation = "get_job_by_run_id"
        normalized_run_id = _optional_str(run_id)

        if normalized_run_id is None:
            return None

        try:
            result = await self.session.execute(
                select(Job).where(Job.run_id == normalized_run_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as error:
            raise _job_store_error(
                operation,
                "Failed to get job by run_id.",
                details={"run_id": normalized_run_id},
                error=error,
            )

    async def list_user_jobs(
        self,
        user_id: int,
        *,
        limit: int = DEFAULT_PAGE_LIMIT,
        offset: int = 0,
    ) -> list[Job]:
        """Return jobs for a user with stable pagination."""

        operation = "list_user_jobs"
        normalized_limit = _normalize_limit(limit, operation=operation)
        normalized_offset = _normalize_offset(offset, operation=operation)

        try:
            result = await self.session.execute(
                select(Job)
                .where(Job.user_id == user_id)
                .order_by(Job.created_at.desc(), Job.id.desc())
                .limit(normalized_limit)
                .offset(normalized_offset)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as error:
            raise _job_store_error(
                operation,
                "Failed to list user jobs.",
                details={
                    "user_id": user_id,
                    "limit": normalized_limit,
                    "offset": normalized_offset,
                },
                error=error,
            )

    async def _transition_job(
        self,
        *,
        job_id: int,
        operation: str,
        allowed_statuses: Sequence[str],
        values: Mapping[str, Any],
    ) -> Job:
        """Apply an atomic job update guarded by current status."""

        update_values = dict(values)
        update_values["updated_at"] = func.now()

        try:
            result = await self.session.execute(
                update(Job)
                .where(Job.id == job_id, Job.status.in_(allowed_statuses))
                .values(**update_values)
                .returning(Job.id)
            )
            updated_job_id = result.scalar_one_or_none()

            if updated_job_id is None:
                raise JobStoreError(
                    technical_message="Invalid job status transition.",
                    details={
                        "operation": operation,
                        "job_id": job_id,
                        "allowed_statuses": list(allowed_statuses),
                    },
                )

            job = await self.get_job(updated_job_id)

            if job is None:
                raise JobStoreError(
                    technical_message="Updated job was not found after transition.",
                    details={"operation": operation, "job_id": updated_job_id},
                )

            return job
        except JobStoreError:
            raise
        except SQLAlchemyError as error:
            raise _job_store_error(
                operation,
                "Failed to update job status.",
                details={
                    "job_id": job_id,
                    "allowed_statuses": list(allowed_statuses),
                },
                error=error,
            )


def _required_str(
    payload: Mapping[str, Any],
    field: str,
    *,
    operation: str,
) -> str:
    value = payload.get(field)

    if value is None or str(value).strip() == "":
        raise JobStoreError(
            technical_message=f"Required job field is missing: {field}",
            details={"operation": operation, "field": field},
        )

    return str(value).strip()


def _required_int(
    payload: Mapping[str, Any],
    field: str,
    *,
    operation: str,
) -> int:
    value = payload.get(field)

    if isinstance(value, bool):
        raise JobStoreError(
            technical_message=f"Required job field must be an integer: {field}",
            details={"operation": operation, "field": field, "value": value},
        )
    
    if value is None or isinstance(value, bool):
        raise JobStoreError(
            technical_message=f"Required job field must be an integer: {field}",
            details={"operation": operation, "field": field, "value": value},
        )

    try:
        parsed_value = int(value)
    except (TypeError, ValueError) as error:
        raise JobStoreError(
            technical_message=f"Required job field must be an integer: {field}",
            details={"operation": operation, "field": field, "value": value},
        ) from error

    return parsed_value


def _required_mapping(
    payload: Mapping[str, Any],
    field: str,
    *,
    operation: str,
) -> Mapping[str, Any]:
    value = payload.get(field)

    if not isinstance(value, Mapping):
        raise JobStoreError(
            technical_message=f"Required job field must be an object: {field}",
            details={"operation": operation, "field": field},
        )

    return value


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip()
    return normalized or None


def _optional_mapping(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return dict(value)

    return None


def _optional_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_step(step: str, *, fallback: str) -> str:
    normalized = str(step or "").strip()
    return normalized or fallback


def _error_step(error: Mapping[str, Any]) -> str:
    step = error.get("step")
    return _normalize_step(str(step or ""), fallback=STEP_FAILED)


def _normalize_limit(limit: int, *, operation: str) -> int:
    if limit <= 0:
        raise JobStoreError(
            technical_message="Job list limit must be greater than zero.",
            details={"operation": operation, "limit": limit},
        )

    return min(limit, MAX_PAGE_LIMIT)


def _normalize_offset(offset: int, *, operation: str) -> int:
    if offset < 0:
        raise JobStoreError(
            technical_message="Job list offset must be greater than or equal to zero.",
            details={"operation": operation, "offset": offset},
        )

    return offset


def _job_store_error(
    operation: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    error: Exception | None = None,
) -> JobStoreError:
    error_details = {"operation": operation}
    error_details.update(details or {})

    if error is not None:
        error_details["error_type"] = error.__class__.__name__

    return JobStoreError(
        technical_message=message,
        details=error_details,
    )


__all__ = [
    "DEFAULT_PAGE_LIMIT",
    "EVENT_STEP_COMPLETED",
    "JOB_STATUS_COMPLETED",
    "JOB_STATUS_FAILED",
    "JOB_STATUS_PENDING",
    "JOB_STATUS_RUNNING",
    "JOB_STATUS_UPLOADED",
    "SQLAlchemyJobStore",
]
