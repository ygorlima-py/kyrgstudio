from __future__ import annotations

from pathlib import PurePosixPath

from app.errors import StorageError


JOBS_PREFIX = "jobs"
INPUT_BASENAME = "input"
AUDIO_FILENAME = "audio.wav"


def job_prefix(job_id: str) -> str:
    job_segment = _validate_segment(job_id, field_name="job_id")
    return f"{JOBS_PREFIX}/{job_segment}/"


def job_input_key(job_id: str, filename: str) -> str:
    suffix = _safe_suffix(filename)
    return f"{job_prefix(job_id)}{INPUT_BASENAME}{suffix}"


def job_audio_key(job_id: str) -> str:
    return f"{job_prefix(job_id)}{AUDIO_FILENAME}"


def _validate_segment(value: str, *, field_name: str) -> str:
    if not value or value != value.strip():
        raise StorageError(
            technical_message=f"Invalid storage {field_name}: {value}",
            details={field_name: value},
        )

    path = PurePosixPath(value.replace("\\", "/"))

    if path.is_absolute() or len(path.parts) != 1 or value in {".", ".."}:
        raise StorageError(
            technical_message=f"Invalid storage {field_name}: {value}",
            details={field_name: value},
        )

    return value


def _safe_suffix(filename: str) -> str:
    if not filename:
        return ""

    name = PurePosixPath(filename.replace("\\", "/")).name
    suffix = PurePosixPath(name).suffix

    if suffix in {".", ".."}:
        return ""

    return suffix


__all__ = [
    "job_audio_key",
    "job_input_key",
    "job_prefix",
]
