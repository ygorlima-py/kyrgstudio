"""Pipeline orchestration service for the application layer."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, BinaryIO, cast

from app.errors import (
    AppError,
    FileNotFoundAppError,
    IdempotencyConflictError,
    InvalidInputError,
    JobNotFoundError,
    JobStoreError,
    ProviderConfigError,
)
from app.pipeline.files import (
    PipelineInputFile,
    build_pipeline_input_key,
    save_pipeline_file,
    save_pipeline_upload,
)
from app.pipeline.input import (
    PipelineInput,
    get_pipeline_type,
    normalize_pipeline_input,
)
from app.pipeline.jobs import (
    build_input_json,
    create_pipeline_job,
    mark_pipeline_job_failed,
    mark_pipeline_job_uploaded,
)
from app.pipeline.transactional_job_store import PipelineJobStoreBase
from app.queue.base import QueueBase
from app.schemas.pipeline import PipelineStartResult, PipelineType
from app.storage.base import (
    ObjectMetadataStorage,
    PresignedUploadStorage,
    StorageBase,
    StoredFile,
)


class PipelineService:
    """Application facade used to create, upload, and enqueue pipeline jobs."""

    def __init__(
        self,
        *,
        job_store: PipelineJobStoreBase,
        storage: StorageBase,
        queue: QueueBase,
    ) -> None:
        self.job_store = job_store
        self.storage = storage
        self.queue = queue

    async def start_from_upload(
        self,
        *,
        user_id: int,
        pipeline_input: PipelineInput,
        filename: str,
        file: BinaryIO,
    ) -> PipelineStartResult:
        """Create a job, save an uploaded stream, and enqueue processing."""

        return await self._start(
            user_id=user_id,
            pipeline_input=pipeline_input,
            save_input_file=lambda job_id: save_pipeline_upload(
                storage=self.storage,
                job_id=job_id,
                filename=filename,
                file=file,
            ),
        )

    async def prepare_presigned_upload(
        self,
        *,
        user_id: int,
        pipeline_input: PipelineInput,
        filename: str,
        content_type: str,
        size_bytes: int,
        expires_in: int,
    ) -> PresignedUploadStartResult:
        """Create a pending job and a temporary direct-upload URL."""

        if not isinstance(self.storage, PresignedUploadStorage):
            raise ProviderConfigError(
                technical_message=(
                    "Configured storage does not support direct uploads."
                ),
                step="configuring_storage",
                details={"storage_backend": self.storage.backend},
            )

        normalized_input = normalize_pipeline_input(pipeline_input)
        request_fingerprint = _direct_upload_fingerprint(
            normalized_input,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
        )
        job = await create_pipeline_job(
            job_store=self.job_store,
            user_id=user_id,
            pipeline_input=normalized_input,
            upload_metadata={
                "filename": filename,
                "content_type": content_type,
                "size_bytes": size_bytes,
                "request_fingerprint": request_fingerprint,
            },
        )
        _ensure_matching_idempotent_request(
            job,
            request_fingerprint=request_fingerprint,
        )
        job_id = _job_id(job)
        object_key = build_pipeline_input_key(
            job_id=job_id,
            filename=filename,
        )

        try:
            upload_url = self.storage.create_presigned_upload_url(
                destination_key=object_key,
                content_type=content_type,
                expires_in=expires_in,
            )
        except Exception as error:
            await self._mark_failed_safely(job_id=job_id, error=error)
            raise

        return PresignedUploadStartResult(
            job_id=job_id,
            object_key=object_key,
            upload_url=upload_url,
            expires_in=expires_in,
        )

    async def confirm_presigned_upload(
        self,
        *,
        user_id: int,
        job_id: int,
    ) -> PipelineStartResult:
        """Verify a direct upload and persist the uploaded job state.

        The object reference is committed before queue scheduling. A retry
        after a successful confirmation returns the committed ``uploaded``
        state without enqueueing the same job twice.
        """

        if not isinstance(self.storage, ObjectMetadataStorage):
            raise ProviderConfigError(
                technical_message=(
                    "Upload confirmation requires object metadata support."
                ),
                step="configuring_storage",
                details={"storage_backend": self.storage.backend},
            )

        job = await self.job_store.get_job(job_id)

        if job is None or _job_value(job, "user_id") != user_id:
            raise JobNotFoundError(
                technical_message="Job was not found for the authenticated user.",
                details={"job_id": job_id},
            )

        job_status = _job_required_str(job, "status")
        upload_metadata = _direct_upload_metadata(job)
        object_key = build_pipeline_input_key(
            job_id=job_id,
            filename=upload_metadata["filename"],
        )

        if job_status == "uploaded":
            if _job_value(job, "input_file_key") != object_key:
                raise InvalidInputError(
                    technical_message="Job upload reference does not match.",
                    step="confirming_upload",
                    details={"field": "input_file_key"},
                )

            return _pipeline_start_result(job)

        if job_status != "pending":
            raise InvalidInputError(
                technical_message="Job is not waiting for upload confirmation.",
                step="confirming_upload",
                details={"field": "status", "status": job_status},
            )

        metadata = self.storage.get_object_metadata(object_key)

        if metadata is None:
            raise FileNotFoundAppError(
                technical_message="Uploaded object was not found in storage.",
                step="confirming_upload",
                details={"field": "upload"},
            )

        if metadata.size_bytes != upload_metadata["size_bytes"]:
            raise InvalidInputError(
                technical_message="Uploaded object size does not match metadata.",
                step="confirming_upload",
                details={
                    "field": "size_bytes",
                    "size_bytes": metadata.size_bytes,
                },
            )

        if metadata.content_type != upload_metadata["content_type"]:
            raise InvalidInputError(
                technical_message="Uploaded object content type does not match.",
                step="confirming_upload",
                details={"field": "content_type", "type": "mismatch"},
            )

        input_file = PipelineInputFile(
            stored_file=StoredFile(
                key=object_key,
                uri=self.storage.uri(object_key),
                backend=self.storage.backend,
            )
        )

        try:
            uploaded_job = await mark_pipeline_job_uploaded(
                job_store=self.job_store,
                job_id=job_id,
                input_file=input_file,
            )
        except JobStoreError:
            # A browser retry may race with the first confirmation. If the
            # transition already succeeded, return the committed state rather
            # than reporting a false failure.
            current_job = await self.job_store.get_job(job_id)

            if (
                current_job is not None
                and _job_value(current_job, "user_id") == user_id
                and _job_value(current_job, "status") == "uploaded"
                and _job_value(current_job, "input_file_key") == object_key
            ):
                return _pipeline_start_result(current_job)

            raise

        try:
            await self.queue.enqueue(job_id)
        except Exception as error:
            await self._mark_failed_safely(job_id=job_id, error=error)
            raise

        return _pipeline_start_result(uploaded_job)

    async def start_from_file(
        self,
        *,
        user_id: int,
        pipeline_input: PipelineInput,
        source_path: Path | str,
        filename: str | None = None,
    ) -> PipelineStartResult:
        """Create a job, save an existing local file, and enqueue processing."""

        resolved_filename = filename or Path(source_path).name

        return await self._start(
            user_id=user_id,
            pipeline_input=pipeline_input,
            save_input_file=lambda job_id: save_pipeline_file(
                storage=self.storage,
                job_id=job_id,
                filename=resolved_filename,
                source_path=source_path,
            ),
        )

    async def _start(
        self,
        *,
        user_id: int,
        pipeline_input: PipelineInput,
        save_input_file: Callable[[int], PipelineInputFile],
    ) -> PipelineStartResult:
        normalized_input = normalize_pipeline_input(pipeline_input)
        pipeline_type = get_pipeline_type(normalized_input)

        job = await create_pipeline_job(
            job_store=self.job_store,
            user_id=user_id,
            pipeline_input=normalized_input,
        )
        job_id = _job_id(job)

        try:
            input_file = save_input_file(job_id)
            uploaded_job = await mark_pipeline_job_uploaded(
                job_store=self.job_store,
                job_id=job_id,
                input_file=input_file,
            )
            await self.queue.enqueue(job_id)
        except Exception as error:
            await self._mark_failed_safely(job_id=job_id, error=error)
            raise

        return PipelineStartResult(
            job_id=job_id,
            run_id=_job_optional_str(uploaded_job, "run_id"),
            status=_job_required_str(uploaded_job, "status"),
            current_step=_job_optional_str(uploaded_job, "current_step"),
            pipeline_type=pipeline_type,
            storage_backend=input_file.storage_backend,
            input_file_key=input_file.input_file_key,
            input_file_uri=input_file.input_file_uri,
        )

    async def _mark_failed_safely(
        self,
        *,
        job_id: int,
        error: AppError | Exception,
    ) -> None:
        try:
            await mark_pipeline_job_failed(
                job_store=self.job_store,
                job_id=job_id,
                error=error,
            )
        except Exception:
            return


def _job_id(job: Any) -> int:
    value = _job_value(job, "id")

    if isinstance(value, bool):
        raise TypeError("Job id must be an integer.")

    return int(value)


def _job_required_str(job: Any, field: str) -> str:
    value = _job_value(job, field)

    if value is None or str(value).strip() == "":
        raise TypeError(f"Job field is required: {field}")

    return str(value)


def _job_optional_str(job: Any, field: str) -> str | None:
    value = _job_value(job, field)

    if value is None:
        return None

    normalized_value = str(value).strip()
    return normalized_value or None


def _job_value(job: Any, field: str) -> Any:
    if isinstance(job, dict):
        return job.get(field)

    return getattr(job, field)


def _direct_upload_metadata(job: Any) -> dict[str, Any]:
    input_json = _job_value(job, "input_json")

    if not isinstance(input_json, dict):
        raise InvalidInputError(
            technical_message="Job upload metadata is invalid.",
            step="confirming_upload",
            details={"field": "input_json"},
        )

    raw_metadata = input_json.get("_direct_upload")

    if not isinstance(raw_metadata, dict):
        raise InvalidInputError(
            technical_message="Job has no direct upload metadata.",
            step="confirming_upload",
            details={"field": "_direct_upload"},
        )

    filename = raw_metadata.get("filename")
    content_type = raw_metadata.get("content_type")
    size_bytes = raw_metadata.get("size_bytes")

    if (
        not isinstance(filename, str)
        or not filename.strip()
        or not isinstance(content_type, str)
        or not content_type.strip()
        or isinstance(size_bytes, bool)
        or not isinstance(size_bytes, int)
        or size_bytes <= 0
    ):
        raise InvalidInputError(
            technical_message="Job direct upload metadata is invalid.",
            step="confirming_upload",
            details={"field": "_direct_upload"},
        )

    return {
        "filename": filename,
        "content_type": content_type.partition(";")[0].strip().lower(),
        "size_bytes": size_bytes,
    }


def _direct_upload_fingerprint(
    pipeline_input: PipelineInput,
    *,
    filename: str,
    content_type: str,
    size_bytes: int,
) -> str:
    """Hash normalized pipeline and file metadata for idempotency checks."""

    payload = build_input_json(pipeline_input)
    payload["_direct_upload"] = {
        "filename": filename,
        "content_type": content_type,
        "size_bytes": size_bytes,
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(serialized).hexdigest()


def _ensure_matching_idempotent_request(
    job: Any,
    *,
    request_fingerprint: str,
) -> None:
    """Reject reuse of one key when the normalized request changed."""

    input_json = _job_value(job, "input_json")

    # Some lightweight service fakes do not model persisted input JSON. The
    # database-backed store always provides it, so this keeps those fakes
    # focused on orchestration rather than persistence details.
    if input_json is None:
        return

    if not isinstance(input_json, dict):
        raise IdempotencyConflictError(
            technical_message=(
                "Idempotency key is already associated with another request."
            ),
            details={"field": "Idempotency-Key"},
        )

    direct_upload = input_json.get("_direct_upload")
    persisted_fingerprint = (
        direct_upload.get("request_fingerprint")
        if isinstance(direct_upload, dict)
        else None
    )

    if persisted_fingerprint != request_fingerprint:
        raise IdempotencyConflictError(
            technical_message=(
                "Idempotency key is already associated with another request."
            ),
            details={"field": "Idempotency-Key"},
        )


def _pipeline_start_result(job: Any) -> PipelineStartResult:
    pipeline_type = _job_required_str(job, "pipeline_type")

    if pipeline_type not in {"copy_analysis", "copy_adaptation"}:
        raise InvalidInputError(
            technical_message="Job pipeline type is invalid.",
            step="confirming_upload",
            details={"field": "pipeline_type"},
        )

    return PipelineStartResult(
        job_id=_job_id(job),
        run_id=_job_optional_str(job, "run_id"),
        status=_job_required_str(job, "status"),
        current_step=_job_optional_str(job, "current_step"),
        pipeline_type=cast(PipelineType, pipeline_type),
        storage_backend=_job_required_str(job, "storage_backend"),
        input_file_key=_job_required_str(job, "input_file_key"),
        input_file_uri=_job_required_str(job, "input_file_uri"),
    )


__all__ = [
    "PipelineService",
    "PipelineStartResult",
    "PresignedUploadStartResult",
]


@dataclass(frozen=True)
class PresignedUploadStartResult:
    """Internal result produced while preparing a direct upload."""

    job_id: int
    object_key: str
    upload_url: str
    expires_in: int
