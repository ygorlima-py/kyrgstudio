"""Unit tests for streaming media upload validation."""

import asyncio
from collections.abc import Coroutine
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from typing import Any, TypeVar

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

import app.api.uploads as uploads_module
from app.api.uploads import (
    ValidatedUpload,
    ValidatedUploadMetadata,
    validate_upload,
    validate_upload_metadata,
)
from app.errors import (
    InvalidInputError,
    ProviderConfigError,
    UnsupportedMediaTypeError,
    UploadTooLargeError,
)
from app.settings import AppSettings

ResultT = TypeVar("ResultT")


@pytest.fixture(autouse=True)
def execute_threadpool_work_inline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep unit tests independent from the host threadpool implementation."""

    async def run_inline(function: Any, *args: Any) -> Any:
        return function(*args)

    monkeypatch.setattr(
        uploads_module,
        "run_in_threadpool",
        run_inline,
    )


def _run(coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    return asyncio.run(coroutine)


def _settings() -> AppSettings:
    """Build deterministic upload settings without external dependencies."""

    return AppSettings(
        environment="test",
        storage_dir=Path("/tmp/kyrg-api-upload-storage"),
        sqlite_path=Path("/tmp/kyrg-api-upload.sqlite"),
        database_url="sqlite+aiosqlite:////tmp/kyrg-api-upload.sqlite",
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
        request_timeout_seconds=60,
        celery_broker_url="amqp://guest:guest@localhost:5672//",
        celery_queue_name="pipeline",
        celery_task_soft_time_limit_seconds=60,
        celery_task_time_limit_seconds=90,
        storage_backend="local",
        r2_account_id=None,
        r2_bucket=None,
        r2_access_key=None,
        r2_secret_key=None,
        max_upload_bytes=1024,
        accepted_input_media_types=("video/mp4", "audio/mpeg"),
    )


def _upload(
    content: bytes,
    *,
    filename: str | None = "input.mp4",
    content_type: str | None = "video/mp4",
    content_length: int | None = None,
    stream: BytesIO | None = None,
) -> UploadFile:
    header_values: dict[str, str] = {}

    if content_type is not None:
        header_values["content-type"] = content_type

    if content_length is not None:
        header_values["content-length"] = str(content_length)

    return UploadFile(
        file=stream if stream is not None else BytesIO(content),
        filename=filename,
        headers=Headers(header_values),
    )


class UnreadableStream(BytesIO):
    """Binary stream that fails when upload validation attempts to seek."""

    def seek(self, offset: int, whence: int = 0) -> int:
        del offset, whence
        raise OSError("stream is not seekable")


def test_validate_upload_returns_filename_content_type_size_and_stream() -> None:
    """Return validated metadata and the original stream instance."""

    stream = BytesIO(b"video-bytes")
    upload = _upload(
        b"",
        filename="  campaign.mp4  ",
        stream=stream,
    )

    result = _run(validate_upload(upload, settings=_settings()))

    assert isinstance(result, ValidatedUpload)
    assert result.filename == "campaign.mp4"
    assert result.content_type == "video/mp4"
    assert result.size_bytes == len(b"video-bytes")
    assert result.file is stream


def test_validate_upload_normalizes_content_type() -> None:
    """Normalize media type case and discard optional MIME parameters."""

    upload = _upload(
        b"video",
        content_type=" Video/MP4; charset=binary ",
    )

    result = _run(validate_upload(upload, settings=_settings()))

    assert result.content_type == "video/mp4"


def test_validate_upload_metadata_accepts_direct_upload_metadata() -> None:
    """Validate the client metadata before issuing a presigned URL."""

    result = validate_upload_metadata(
        filename="  campaign.mp4  ",
        content_type=" Video/MP4; charset=binary ",
        size_bytes=42,
        settings=_settings(),
    )

    assert isinstance(result, ValidatedUploadMetadata)
    assert result.filename == "campaign.mp4"
    assert result.content_type == "video/mp4"
    assert result.size_bytes == 42


@pytest.mark.parametrize("filename", [None, "", "campaign"])
def test_validate_upload_metadata_rejects_missing_or_extensionless_filename(
    filename: str | None,
) -> None:
    """Direct uploads require a filename with an extension."""

    with pytest.raises(InvalidInputError):
        validate_upload_metadata(
            filename=filename,
            content_type="video/mp4",
            size_bytes=42,
            settings=_settings(),
        )


def test_validate_upload_metadata_rejects_size_above_limit() -> None:
    """Reject a direct upload before creating a pending job."""

    settings = replace(_settings(), max_upload_bytes=10)

    with pytest.raises(UploadTooLargeError) as captured:
        validate_upload_metadata(
            filename="campaign.mp4",
            content_type="video/mp4",
            size_bytes=11,
            settings=settings,
        )

    assert captured.value.details == {
        "size_bytes": 11,
        "max_upload_bytes": 10,
    }


def test_validate_upload_rewinds_stream() -> None:
    """Leave the validated stream positioned for storage to read from byte zero."""

    content = b"complete-video-content"
    stream = BytesIO(content)
    stream.seek(8)
    upload = _upload(b"", stream=stream)

    result = _run(validate_upload(upload, settings=_settings()))

    assert result.file.tell() == 0
    assert result.file.read() == content


@pytest.mark.parametrize("filename", [None, "", "   "])
def test_validate_upload_rejects_missing_filename(
    filename: str | None,
) -> None:
    """Reject uploads without a meaningful client filename."""

    upload = _upload(b"video", filename=filename)

    with pytest.raises(InvalidInputError) as captured:
        _run(validate_upload(upload, settings=_settings()))

    assert captured.value.step == "validating_upload"
    assert captured.value.details == {"field": "filename"}


@pytest.mark.parametrize(
    "content_type",
    [None, "", "application/octet-stream", "text/plain"],
)
def test_validate_upload_rejects_unsupported_media_type(
    content_type: str | None,
) -> None:
    """Reject media types outside the configured application allowlist."""

    upload = _upload(b"video", content_type=content_type)

    with pytest.raises(UnsupportedMediaTypeError) as captured:
        _run(validate_upload(upload, settings=_settings()))

    assert captured.value.step == "validating_upload"
    assert captured.value.details["accepted_media_types"] == [
        "audio/mpeg",
        "video/mp4",
    ]


def test_validate_upload_rejects_empty_file() -> None:
    """Reject a zero-byte stream after measuring its actual size."""

    upload = _upload(b"")

    with pytest.raises(InvalidInputError) as captured:
        _run(validate_upload(upload, settings=_settings()))

    assert captured.value.details == {"field": "file"}


def test_validate_upload_rejects_file_above_actual_size_limit() -> None:
    """Enforce the configured limit using bytes present in the stream."""

    upload = _upload(
        b"123456",
        content_length=1,
    )
    settings = replace(_settings(), max_upload_bytes=5)

    with pytest.raises(UploadTooLargeError) as captured:
        _run(validate_upload(upload, settings=settings))

    assert captured.value.details == {
        "size_bytes": 6,
        "max_upload_bytes": 5,
    }


def test_validate_upload_does_not_trust_content_length() -> None:
    """Accept a small stream even when the client claims a much larger body."""

    upload = _upload(
        b"123456",
        content_length=999_999,
    )
    settings = replace(_settings(), max_upload_bytes=10)

    result = _run(validate_upload(upload, settings=settings))

    assert result.size_bytes == 6


def test_validate_upload_rejects_empty_media_type_configuration() -> None:
    """Fail safely when the server has no configured media allowlist."""

    upload = _upload(b"video")
    settings = replace(
        _settings(),
        accepted_input_media_types=("", "   "),
    )

    with pytest.raises(ProviderConfigError) as captured:
        _run(validate_upload(upload, settings=settings))

    assert captured.value.step == "configuring_api"
    assert captured.value.details == {
        "field": "accepted_input_media_types",
    }


def test_validate_upload_wraps_unreadable_stream_error() -> None:
    """Translate stream inspection failures into a controlled input error."""

    upload = _upload(
        b"",
        stream=UnreadableStream(b"video"),
    )

    with pytest.raises(InvalidInputError) as captured:
        _run(validate_upload(upload, settings=_settings()))

    assert captured.value.step == "validating_upload"
    assert captured.value.details == {"field": "file"}
    assert isinstance(captured.value.__cause__, OSError)
