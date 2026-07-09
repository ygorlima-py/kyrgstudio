"""File handling helpers for pipeline job inputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from app.storage.base import StorageBase, StoredFile
from app.storage.paths import job_input_key
from app.schemas.pipeline import PipelineInputFile

def save_pipeline_upload(
    *,
    storage: StorageBase,
    job_id: int,
    filename: str,
    file: BinaryIO,
) -> PipelineInputFile:
    """Save an uploaded file stream as the original input for a job."""

    destination_key = build_pipeline_input_key(
        job_id=job_id,
        filename=filename,
    )
    stored_file = storage.save_upload(
        file=file,
        destination_key=destination_key,
    )

    return PipelineInputFile(stored_file=stored_file)


def save_pipeline_file(
    *,
    storage: StorageBase,
    job_id: int,
    filename: str,
    source_path: Path | str,
) -> PipelineInputFile:
    """Save an existing local file as the original input for a job."""

    destination_key = build_pipeline_input_key(
        job_id=job_id,
        filename=filename,
    )
    stored_file = storage.save_file(
        source_path=Path(source_path),
        destination_key=destination_key,
    )

    return PipelineInputFile(stored_file=stored_file)


def build_pipeline_input_key(*, job_id: int, filename: str) -> str:
    """Build the storage key for a job input file."""

    return job_input_key(str(job_id), filename)


def stored_file_to_job_payload(stored_file: StoredFile) -> dict[str, str]:
    """Convert a stored file reference into the job upload payload."""

    return PipelineInputFile(stored_file=stored_file).to_job_payload()


__all__ = [
    "PipelineInputFile",
    "build_pipeline_input_key",
    "save_pipeline_file",
    "save_pipeline_upload",
    "stored_file_to_job_payload",
]
