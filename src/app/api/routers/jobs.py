"""Authenticated HTTP endpoints for pipeline job submission and retrieval.

The router owns multipart parsing, upload validation, authentication, and
ownership checks. It delegates persistence, storage, queueing, and pipeline
orchestration to application services and never exposes internal file paths or
provider configuration.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    Path,
    Query,
    UploadFile,
    status,
)
from pydantic import ValidationError

from app.api.dependencies import (
    get_current_user,
    get_job_store,
    get_pipeline_service,
    get_settings,
    get_storage,
)
from app.api.uploads import validate_upload, validate_upload_metadata
from app.auth.principal import AuthenticatedPrincipal
from app.errors import (
    InvalidInputError,
    JobNotFoundError,
    JobResultNotReadyError,
    ProviderConfigError,
)
from app.pipeline.input import PipelineInput
from app.pipeline.service import PipelineService
from app.schemas.jobs import (
    CreateJobRequest,
    JobListResponse,
    JobResultResponse,
    JobStatus,
    JobStatusResponse,
    JobSubmissionResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
    build_job_list_response,
    build_job_result_response,
    build_job_status_response,
    build_job_submission_response,
    build_pipeline_input,
    parse_create_job_request,
)
from app.schemas.pipeline import PipelineType
from app.settings import AppSettings
from app.storage.base import (
    MAX_PRESIGNED_UPLOAD_TTL_SECONDS,
    PresignedUploadStorage,
    StorageBase,
)
from app.store.base import JobStoreBase

CurrentUserDependency = Annotated[
    AuthenticatedPrincipal,
    Depends(get_current_user),
]
JobStoreDependency = Annotated[JobStoreBase, Depends(get_job_store)]
PipelineServiceDependency = Annotated[
    PipelineService,
    Depends(get_pipeline_service),
]
StorageDependency = Annotated[
    StorageBase,
    Depends(get_storage),
]
SettingsDependency = Annotated[AppSettings, Depends(get_settings)]
JobIdPath = Annotated[int, Path(gt=0, description="Internal job identifier.")]
JobListLimitQuery = Annotated[
    int,
    Query(
        ge=1,
        le=100,
        description="Maximum number of jobs returned.",
    ),
]
JobListOffsetQuery = Annotated[
    int,
    Query(
        ge=0,
        description="Number of newer jobs to skip.",
    ),
]
JobListIdQuery = Annotated[
    int | None,
    Query(
        gt=0,
        description="Return only the job with this identifier.",
    ),
]
JobListStatusQuery = Annotated[
    JobStatus | None,
    Query(
        alias="status",
        description="Return only jobs with this lifecycle status.",
    ),
]
JobListPipelineTypeQuery = Annotated[
    PipelineType | None,
    Query(description="Return only jobs from this pipeline type."),
]


router = APIRouter(
    prefix="/v1/jobs",
    tags=["jobs"],
)

PRESIGNED_UPLOAD_URL_TTL_SECONDS = MAX_PRESIGNED_UPLOAD_TTL_SECONDS


@router.post(
    "/upload-url",
    response_model=PresignedUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Prepare a direct job upload",
)
async def prepare_upload(
    upload_request: PresignedUploadRequest,
    current_user: CurrentUserDependency,
    pipeline_service: PipelineServiceDependency,
    settings: SettingsDependency,
    storage: StorageDependency,
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=1, max_length=255),
    ] = None,
) -> PresignedUploadResponse:
    """Create a pending owned job and return a temporary upload URL."""

    if not isinstance(storage, PresignedUploadStorage):
        raise ProviderConfigError(
            technical_message=(
                "Direct uploads require an S3-compatible storage backend."
            ),
            step="configuring_storage",
            details={"storage_backend": storage.backend},
        )

    metadata = validate_upload_metadata(
        filename=upload_request.filename,
        content_type=upload_request.content_type,
        size_bytes=upload_request.size_bytes,
        settings=settings,
    )
    pipeline_input = _build_pipeline_input(
        upload_request.pipeline,
        settings=settings,
        idempotency_key=idempotency_key,
    )
    result = await pipeline_service.prepare_presigned_upload(
        user_id=current_user.user_id,
        pipeline_input=pipeline_input,
        filename=metadata.filename,
        content_type=metadata.content_type,
        size_bytes=metadata.size_bytes,
        expires_in=PRESIGNED_UPLOAD_URL_TTL_SECONDS,
    )

    return PresignedUploadResponse.model_validate(
        {
            "job_id": result.job_id,
            "object_key": result.object_key,
            "upload_url": result.upload_url,
            "expires_in": result.expires_in,
        }
    )


@router.post(
    "/{job_id}/upload/complete",
    response_model=JobSubmissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm a direct job upload",
)
async def confirm_upload(
    job_id: JobIdPath,
    current_user: CurrentUserDependency,
    pipeline_service: PipelineServiceDependency,
) -> JobSubmissionResponse:
    """Verify the stored object and move the owned job to uploaded."""

    result = await pipeline_service.confirm_presigned_upload(
        user_id=current_user.user_id,
        job_id=job_id,
    )
    return build_job_submission_response(result)


@router.post(
    "",
    response_model=JobSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a pipeline job",
)
async def submit_job(
    file: Annotated[UploadFile, File(description="Input video or audio file.")],
    raw_request: Annotated[
        str,
        Form(
            alias="request",
            description="JSON metadata describing the requested pipeline.",
        ),
    ],
    current_user: CurrentUserDependency,
    pipeline_service: PipelineServiceDependency,
    settings: SettingsDependency,
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key"),
    ] = None,
) -> JobSubmissionResponse:
    """Validate, persist, upload, and enqueue a job owned by the caller."""

    request_payload = _parse_job_request(raw_request)
    pipeline_input = _build_pipeline_input(
        request_payload,
        settings=settings,
        idempotency_key=idempotency_key,
    )
    validated_upload = await validate_upload(file, settings=settings)
    result = await pipeline_service.start_from_upload(
        user_id=current_user.user_id,
        pipeline_input=pipeline_input,
        filename=validated_upload.filename,
        file=validated_upload.file,
    )
    return build_job_submission_response(result)


@router.get(
    "",
    response_model=JobListResponse,
    status_code=status.HTTP_200_OK,
    summary="List the current user's jobs",
)
async def list_jobs(
    current_user: CurrentUserDependency,
    job_store: JobStoreDependency,
    job_id: JobListIdQuery = None,
    job_status: JobListStatusQuery = None,
    pipeline_type: JobListPipelineTypeQuery = None,
    limit: JobListLimitQuery = 20,
    offset: JobListOffsetQuery = 0,
) -> JobListResponse:
    """Return an ordered page containing only the caller's public job data."""

    page = await job_store.list_user_jobs(
        current_user.user_id,
        job_id=job_id,
        status=job_status,
        pipeline_type=pipeline_type,
        limit=limit,
        offset=offset,
    )
    return build_job_list_response(
        page.items,
        limit=limit,
        offset=offset,
        has_more=page.has_more,
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a job status",
)
async def get_job_status(
    job_id: JobIdPath,
    current_user: CurrentUserDependency,
    job_store: JobStoreDependency,
) -> JobStatusResponse:
    """Return status only when the job belongs to the authenticated user."""

    job = await _load_owned_job(
        job_id=job_id,
        user_id=current_user.user_id,
        job_store=job_store,
    )
    return build_job_status_response(job)


@router.get(
    "/{job_id}/result",
    response_model=JobResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a completed job result",
)
async def get_job_result(
    job_id: JobIdPath,
    current_user: CurrentUserDependency,
    job_store: JobStoreDependency,
) -> JobResultResponse:
    """Return persisted output only for an owned, completed job."""

    job = await _load_owned_job(
        job_id=job_id,
        user_id=current_user.user_id,
        job_store=job_store,
    )
    job_status = _required_job_text(job, "status")

    if job_status != "completed":
        raise _job_result_not_ready(job_id=job_id, job=job)

    return build_job_result_response(job)


def _parse_job_request(raw_request: str) -> CreateJobRequest:
    try:
        return parse_create_job_request(raw_request)
    except ValidationError as error:
        raise InvalidInputError(
            technical_message="Job request metadata is invalid.",
            step="validating_request",
            details={
                "errors": [
                    {
                        "path": ".".join(map(str, item["loc"])),
                        "type": item["type"],
                        "message": item["msg"],
                    }
                    for item in error.errors()
                ]
            },
        ) from error


def _build_pipeline_input(
    request_payload: CreateJobRequest,
    *,
    settings: AppSettings,
    idempotency_key: str | None,
) -> PipelineInput:
    try:
        return build_pipeline_input(
            request_payload,
            settings=settings,
            idempotency_key=idempotency_key,
        )
    except ValidationError as error:
        raise InvalidInputError(
            technical_message="Pipeline request fields are invalid.",
            step="validating_request",
            details={
                "errors": [
                    {
                        "path": ".".join(map(str, item["loc"])),
                        "type": item["type"],
                        "message": item["msg"],
                    }
                    for item in error.errors()
                ]
            },
        ) from error


async def _load_owned_job(
    *,
    job_id: int,
    user_id: int,
    job_store: JobStoreBase,
) -> Any:
    job = await job_store.get_job(job_id)

    if job is None or _job_user_id(job) != user_id:
        raise JobNotFoundError(
            technical_message="Job was not found for the authenticated user.",
            details={"job_id": job_id},
        )

    return job


def _job_result_not_ready(*, job_id: int, job: object) -> JobResultNotReadyError:
    job_status = _required_job_text(job, "status")
    details: dict[str, Any] = {
        "job_id": job_id,
        "status": job_status,
    }

    if job_status == "failed":
        persisted_error = _job_value(job, "error_json")

        if isinstance(persisted_error, Mapping):
            error_code = persisted_error.get("code")

            if isinstance(error_code, str) and error_code.strip():
                details["code"] = error_code.strip()

    return JobResultNotReadyError(
        technical_message="Job result is not available.",
        details=details,
    )


def _job_user_id(job: object) -> int:
    value = _job_value(job, "user_id")

    if isinstance(value, bool):
        raise ValueError("Persisted job user_id must be an integer.")

    try:
        user_id = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "Persisted job user_id must be an integer."
        ) from error

    if user_id <= 0:
        raise ValueError("Persisted job user_id must be positive.")

    return user_id


def _required_job_text(job: object, field: str) -> str:
    value = _job_value(job, field)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Persisted job field is required: {field}")

    return value.strip()


def _job_value(job: object, field: str) -> Any:
    if isinstance(job, Mapping):
        return job.get(field)

    return getattr(job, field, None)


__all__ = ["router"]
