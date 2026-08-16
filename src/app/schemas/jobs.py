"""HTTP schemas and mappers for pipeline jobs.

This module owns the public job contract. It translates HTTP request data into
application pipeline inputs and converts persisted job data into responses that
do not expose storage paths or internal configuration.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import (
    Annotated,
    Any,
    Literal,
    NotRequired,
    TypeAlias,
    TypedDict,
    cast,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    TypeAdapter,
)

from app.pipeline.input import PipelineInput, normalize_pipeline_input
from app.schemas.pipeline import (
    CopyAdaptationPipelineInput,
    CopyAnalysisPipelineInput,
    PipelineStartResult,
    PipelineType,
)
from app.settings import AppSettings
from kyrg.workflows.copyadaptation import UserProfileOutput


NonBlankText: TypeAlias = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
RunId: TypeAlias = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
JobStatus: TypeAlias = Literal[
    "pending",
    "uploaded",
    "running",
    "completed",
    "failed",
]


class _CreateJobRequestBase(BaseModel):
    """Fields shared by all public pipeline submission requests."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    source_type: Literal["video", "audio"]
    run_id: RunId | None = None
    language: NonBlankText | None = None
    need_correction: bool = False
    transcriber_provider: NonBlankText | None = None
    transcriber_model: NonBlankText | None = None
    llm_provider: NonBlankText | None = None
    analysis_model: NonBlankText | None = None
    max_duration_seconds: int | None = Field(default=None, gt=0)
    output_formats: list[NonBlankText] = Field(
        default_factory=lambda: ["json"],
    )


class CreateCopyAnalysisJobRequest(_CreateJobRequestBase):
    """Public request for transcription and copy analysis."""

    pipeline_type: Literal["copy_analysis"]


class CreateCopyAdaptationJobRequest(_CreateJobRequestBase):
    """Public request for copy analysis followed by offer adaptation."""

    pipeline_type: Literal["copy_adaptation"]
    user_profile: UserProfileOutput
    adaptation_model: NonBlankText | None = None


CreateJobRequest: TypeAlias = Annotated[
    CreateCopyAnalysisJobRequest | CreateCopyAdaptationJobRequest,
    Field(discriminator="pipeline_type"),
]


class JobSubmissionResponse(BaseModel):
    """Safe response returned after a job is uploaded and queued."""

    model_config = ConfigDict(extra="forbid")

    job_id: int
    run_id: str | None = None
    status: str
    current_step: str | None = None
    pipeline_type: PipelineType


class PresignedUploadRequest(BaseModel):
    """Public metadata required to prepare a direct job upload."""

    model_config = ConfigDict(extra="forbid")

    pipeline: CreateJobRequest
    filename: NonBlankText
    content_type: NonBlankText
    size_bytes: int = Field(gt=0)


class PresignedUploadResponse(BaseModel):
    """Public data needed to upload one job file directly to storage."""

    model_config = ConfigDict(extra="forbid")

    job_id: int = Field(gt=0)
    object_key: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=1024),
    ]
    upload_url: HttpUrl
    expires_in: int = Field(gt=0)


class ApiErrorResponse(BaseModel):
    """Stable public error payload translated by the frontend."""

    model_config = ConfigDict(extra="forbid")

    code: str
    step: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class JobStatusResponse(BaseModel):
    """Safe persisted job status returned to its owner."""

    model_config = ConfigDict(extra="forbid")

    job_id: int
    run_id: str | None = None
    pipeline_type: PipelineType
    status: str
    current_step: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    execution_time_seconds: float | None = None
    error: ApiErrorResponse | None = None


class JobListResponse(BaseModel):
    """Paginated public statuses for jobs owned by one user."""

    model_config = ConfigDict(extra="forbid")

    items: list[JobStatusResponse]
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    has_more: bool


class PublicTranscriptionOutput(TypedDict):
    """User-facing transcription without provider or filesystem metadata."""

    language: str | None
    text: str


class PublicAdaptedScriptOutput(TypedDict, total=False):
    """Editable script data exposed without duplicated result diagnostics."""

    script: str
    sections: list[dict[str, Any]]
    hooks: list[str]
    cta: str | None
    estimated_duration_seconds: float | None
    word_count: int
    voice_ready_text: str
    adaptation_notes: str | None


class JobResultOutput(TypedDict):
    """Allowed fields inside a completed public pipeline result."""

    transcription: NotRequired[PublicTranscriptionOutput | None]
    copy_analysis: dict[str, Any]
    adapted_script: NotRequired[PublicAdaptedScriptOutput]
    validation: NotRequired[dict[str, Any] | None]
    missing_proofs: NotRequired[list[str]]
    token_usage: NotRequired[dict[str, Any]]
    execution_time_seconds: NotRequired[float]


class JobResultResponse(BaseModel):
    """Completed pipeline output returned without internal job metadata."""

    model_config = ConfigDict(extra="forbid")

    job_id: int
    run_id: str | None = None
    pipeline_type: PipelineType
    status: Literal["completed"]
    output: JobResultOutput


_CREATE_JOB_REQUEST_ADAPTER = TypeAdapter(CreateJobRequest)
_RUN_ID_ADAPTER = TypeAdapter(RunId)


def parse_create_job_request(raw_request: str) -> CreateJobRequest:
    """Parse the JSON string carried by the multipart ``request`` field."""

    return _CREATE_JOB_REQUEST_ADAPTER.validate_json(raw_request)


def build_pipeline_input(
    request: CreateJobRequest,
    *,
    settings: AppSettings,
    idempotency_key: str | None = None,
) -> PipelineInput:
    """Map a public request to a validated application pipeline input."""

    common_fields = {
        "source_type": request.source_type,
        "run_id": _resolve_run_id(
            request.run_id,
            idempotency_key=idempotency_key,
        ),
        "language": request.language,
        "need_correction": request.need_correction,
        "transcriber_provider": (
            request.transcriber_provider
            or settings.default_transcriber_provider
        ),
        "transcriber_model": (
            request.transcriber_model
            or settings.default_transcriber_model
        ),
        "llm_provider": request.llm_provider or settings.default_llm_provider,
        "analysis_model": (
            request.analysis_model or settings.default_analysis_model
        ),
        "max_duration_seconds": (
            request.max_duration_seconds
            if request.max_duration_seconds is not None
            else settings.max_duration_seconds
        ),
        "output_formats": list(request.output_formats),
    }

    if isinstance(request, CreateCopyAdaptationJobRequest):
        pipeline_input: PipelineInput = CopyAdaptationPipelineInput(
            **common_fields,
            user_profile=request.user_profile,
            adaptation_model=(
                request.adaptation_model
                or settings.default_adaptation_model
            ),
        )
    else:
        pipeline_input = CopyAnalysisPipelineInput(**common_fields)

    return normalize_pipeline_input(pipeline_input)


def build_job_submission_response(
    result: PipelineStartResult,
) -> JobSubmissionResponse:
    """Remove storage references from the pipeline submission result."""

    return JobSubmissionResponse(
        job_id=result.job_id,
        run_id=result.run_id,
        status=result.status,
        current_step=result.current_step,
        pipeline_type=result.pipeline_type,
    )


def build_job_status_response(job: object) -> JobStatusResponse:
    """Map a persisted job object or mapping to its public status response."""

    status = _required_text(job, "status")
    error = (
        _build_api_error(_job_value(job, "error_json"))
        if status == "failed"
        else None
    )

    return JobStatusResponse(
        job_id=_required_int(job, "id"),
        run_id=_optional_text(_job_value(job, "run_id")),
        pipeline_type=_required_pipeline_type(job),
        status=status,
        current_step=_optional_text(_job_value(job, "current_step")),
        created_at=_required_datetime(job, "created_at"),
        started_at=_optional_datetime(_job_value(job, "started_at")),
        finished_at=_optional_datetime(_job_value(job, "finished_at")),
        execution_time_seconds=_optional_float(
            _job_value(job, "execution_time_seconds")
        ),
        error=error,
    )


def build_job_list_response(
    jobs: Sequence[object],
    *,
    limit: int,
    offset: int,
    has_more: bool,
) -> JobListResponse:
    """Map an ordered page of persisted jobs to public status records."""

    return JobListResponse(
        items=[build_job_status_response(job) for job in jobs],
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


def build_job_result_response(job: object) -> JobResultResponse:
    """Map a completed persisted job to its public result response."""

    status = _required_text(job, "status")

    if status != "completed":
        raise ValueError("Job result can only be built for a completed job.")

    pipeline_type = _required_pipeline_type(job)

    return JobResultResponse(
        job_id=_required_int(job, "id"),
        run_id=_optional_text(_job_value(job, "run_id")),
        pipeline_type=pipeline_type,
        status="completed",
        output=_build_public_job_output(
            _required_mapping(job, "output_json"),
            pipeline_type=pipeline_type,
        ),
    )


def _build_public_job_output(
    persisted_output: Mapping[str, Any],
    *,
    pipeline_type: PipelineType,
) -> JobResultOutput:
    """Whitelist product data from current and legacy persisted outputs."""

    copy_analysis = persisted_output.get("copy_analysis")

    if not isinstance(copy_analysis, Mapping):
        raise ValueError("Completed job copy analysis is invalid.")

    public_output: dict[str, Any] = {
        "copy_analysis": dict(copy_analysis),
    }
    transcription = persisted_output.get("transcription")

    if transcription is not None:
        if not isinstance(transcription, Mapping):
            raise ValueError("Completed job transcription is invalid.")

        transcription_text = transcription.get("text")

        if not isinstance(transcription_text, str):
            raise ValueError("Completed job transcription text is invalid.")

        public_output["transcription"] = {
            "language": _optional_text(transcription.get("language")),
            "text": transcription_text,
        }

    _copy_optional_public_field(
        persisted_output,
        public_output,
        field="token_usage",
        expected_type=Mapping,
    )
    execution_time = _optional_float(
        persisted_output.get("execution_time_seconds")
    )

    if execution_time is not None:
        public_output["execution_time_seconds"] = execution_time

    if pipeline_type == "copy_adaptation":
        adapted_script = persisted_output.get("adapted_script")

        if adapted_script is not None:
            public_output["adapted_script"] = _build_public_adapted_script(
                adapted_script
            )

        _copy_optional_public_field(
            persisted_output,
            public_output,
            field="validation",
            expected_type=Mapping,
            allow_none=True,
        )
        _copy_optional_public_field(
            persisted_output,
            public_output,
            field="missing_proofs",
            expected_type=list,
        )

    return cast(JobResultOutput, public_output)


def _build_public_adapted_script(value: Any) -> PublicAdaptedScriptOutput:
    """Whitelist editable script fields from current and legacy job results.

    Older records may contain validation and proof diagnostics nested inside
    ``adapted_script``. Those fields are intentionally omitted because their
    canonical public locations are ``output.validation`` and
    ``output.missing_proofs``.
    """

    if not isinstance(value, Mapping):
        raise ValueError("Completed job adapted script is invalid.")

    public_fields = (
        "script",
        "sections",
        "hooks",
        "cta",
        "estimated_duration_seconds",
        "word_count",
        "voice_ready_text",
        "adaptation_notes",
    )
    public_script = {
        field: value[field]
        for field in public_fields
        if field in value
    }

    return cast(PublicAdaptedScriptOutput, public_script)


def _copy_optional_public_field(
    source: Mapping[str, Any],
    destination: dict[str, Any],
    *,
    field: str,
    expected_type: type,
    allow_none: bool = False,
) -> None:
    """Copy one optional product field after validating its container type."""

    if field not in source:
        return

    value = source[field]

    if value is None and allow_none:
        destination[field] = None
        return

    if not isinstance(value, expected_type):
        raise ValueError(f"Completed job field is invalid: {field}")

    if isinstance(value, Mapping):
        destination[field] = dict(value)
        return

    if isinstance(value, list):
        destination[field] = list(value)
        return

    raise ValueError(f"Completed job field is invalid: {field}")


def _resolve_run_id(
    request_run_id: str | None,
    *,
    idempotency_key: str | None,
) -> str | None:
    if request_run_id is not None:
        return request_run_id

    if idempotency_key is None:
        return None

    return _RUN_ID_ADAPTER.validate_python(idempotency_key)


def _build_api_error(value: Any) -> ApiErrorResponse | None:
    if not isinstance(value, Mapping):
        return None

    code = _optional_text(value.get("code"))

    if code is None:
        return None

    return ApiErrorResponse(
        code=code,
        step=_optional_text(value.get("step")),
        # Persisted error metadata is internal by default. Public handlers may
        # add explicitly approved details for specific error codes later.
        details={},
    )


def _job_value(job: object, field: str) -> Any:
    if isinstance(job, Mapping):
        return job.get(field)

    return getattr(job, field, None)


def _required_int(job: object, field: str) -> int:
    value = _job_value(job, field)

    if isinstance(value, bool):
        raise ValueError(f"Job field must be an integer: {field}")

    try:
        normalized_value = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Job field must be an integer: {field}") from error

    if normalized_value <= 0:
        raise ValueError(f"Job field must be positive: {field}")

    return normalized_value


def _required_text(job: object, field: str) -> str:
    value = _optional_text(_job_value(job, field))

    if value is None:
        raise ValueError(f"Job field is required: {field}")

    return value


def _required_pipeline_type(job: object) -> PipelineType:
    value = _required_text(job, "pipeline_type")

    if value not in {"copy_analysis", "copy_adaptation"}:
        raise ValueError(f"Unsupported persisted pipeline type: {value}")

    return cast(PipelineType, value)


def _required_datetime(job: object, field: str) -> datetime:
    value = _job_value(job, field)

    if not isinstance(value, datetime):
        raise ValueError(f"Job field must be a datetime: {field}")

    return value


def _required_mapping(job: object, field: str) -> dict[str, Any]:
    value = _job_value(job, field)

    if not isinstance(value, Mapping):
        raise ValueError(f"Job field must be an object: {field}")

    return dict(value)


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None

    normalized_value = str(value).strip()
    return normalized_value or None


def _optional_datetime(value: Any) -> datetime | None:
    if value is None:
        return None

    if not isinstance(value, datetime):
        raise ValueError("Optional job datetime field is invalid.")

    return value


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool):
        raise ValueError("Optional job numeric field is invalid.")

    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("Optional job numeric field is invalid.") from error


__all__ = [
    "ApiErrorResponse",
    "CreateCopyAdaptationJobRequest",
    "CreateCopyAnalysisJobRequest",
    "CreateJobRequest",
    "JobListResponse",
    "JobStatus",
    "JobResultOutput",
    "JobResultResponse",
    "JobStatusResponse",
    "JobSubmissionResponse",
    "PresignedUploadRequest",
    "PresignedUploadResponse",
    "PublicAdaptedScriptOutput",
    "PublicTranscriptionOutput",
    "build_job_list_response",
    "build_job_result_response",
    "build_job_status_response",
    "build_job_submission_response",
    "build_pipeline_input",
    "parse_create_job_request",
]
