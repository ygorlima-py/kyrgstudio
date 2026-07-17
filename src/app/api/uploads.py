"""Validation helpers for media files received by the HTTP API."""

from __future__ import annotations

from dataclasses import dataclass
from io import SEEK_END
from typing import BinaryIO

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.errors import (
    InvalidInputError,
    ProviderConfigError,
    UnsupportedMediaTypeError,
    UploadTooLargeError,
)
from app.settings import AppSettings


@dataclass(frozen=True)
class ValidatedUpload:
    """Validated upload data ready to be passed to ``PipelineService``."""

    filename: str
    content_type: str
    size_bytes: int
    file: BinaryIO


async def validate_upload(
    upload: UploadFile,
    *,
    settings: AppSettings,
) -> ValidatedUpload:
    """Validate an uploaded media file without loading it into memory.

    FastAPI has already parsed the multipart request when this function runs.
    The underlying spooled file is measured with ``seek`` and ``tell``, then
    rewound so storage can consume it from the beginning.
    """

    filename = _validate_filename(upload.filename)
    accepted_media_types = _normalize_accepted_media_types(
        settings.accepted_input_media_types
    )
    content_type = _validate_content_type(
        upload.content_type,
        accepted_media_types=accepted_media_types,
    )
    size_bytes = await run_in_threadpool(
        _measure_and_rewind,
        upload.file,
    )

    if size_bytes == 0:
        raise InvalidInputError(
            technical_message="Uploaded media file is empty.",
            step="validating_upload",
            details={"field": "file"},
        )

    if size_bytes > settings.max_upload_bytes:
        raise UploadTooLargeError(
            technical_message=(
                "Uploaded media file exceeds the configured size limit."
            ),
            details={
                "size_bytes": size_bytes,
                "max_upload_bytes": settings.max_upload_bytes,
            },
        )

    return ValidatedUpload(
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        file=upload.file,
    )


def _validate_filename(value: str | None) -> str:
    filename = str(value or "").strip()

    if not filename:
        raise InvalidInputError(
            technical_message="Uploaded media filename is required.",
            step="validating_upload",
            details={"field": "filename"},
        )

    return filename


def _normalize_accepted_media_types(
    values: tuple[str, ...],
) -> frozenset[str]:
    accepted_media_types = frozenset(
        normalized_value
        for value in values
        if (normalized_value := _normalize_content_type(value))
    )

    if not accepted_media_types:
        raise ProviderConfigError(
            technical_message=(
                "At least one accepted input media type must be configured."
            ),
            step="configuring_api",
            details={"field": "accepted_input_media_types"},
        )

    return accepted_media_types


def _validate_content_type(
    value: str | None,
    *,
    accepted_media_types: frozenset[str],
) -> str:
    content_type = _normalize_content_type(value)

    if content_type not in accepted_media_types:
        raise UnsupportedMediaTypeError(
            technical_message=f"Unsupported upload media type: {value}",
            step="validating_upload",
            details={
                "content_type": content_type or None,
                "accepted_media_types": sorted(accepted_media_types),
            },
        )

    return content_type


def _normalize_content_type(value: str | None) -> str:
    return str(value or "").partition(";")[0].strip().lower()


def _measure_and_rewind(file: BinaryIO) -> int:
    try:
        file.seek(0, SEEK_END)
        size_bytes = file.tell()
        file.seek(0)
    except (OSError, ValueError) as error:
        raise InvalidInputError(
            technical_message=f"Unable to inspect uploaded media file: {error}",
            step="validating_upload",
            details={"field": "file"},
        ) from error

    if isinstance(size_bytes, bool) or size_bytes < 0:
        raise InvalidInputError(
            technical_message="Uploaded media file has an invalid size.",
            step="validating_upload",
            details={"field": "file"},
        )

    return size_bytes


__all__ = [
    "ValidatedUpload",
    "validate_upload",
]
