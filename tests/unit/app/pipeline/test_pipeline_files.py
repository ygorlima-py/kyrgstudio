"""Unit tests for pipeline file storage helpers.

These tests protect the boundary between the pipeline service and the storage
contract. They use a fake storage backend and do not touch the filesystem.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from app.pipeline.files import (
    build_pipeline_input_key,
    save_pipeline_file,
    save_pipeline_upload,
    stored_file_to_job_payload,
)
from app.schemas.pipeline import PipelineInputFile
from app.storage.base import StorageBase, StoredFile


def test_build_pipeline_input_key_uses_job_input_key() -> None:
    """Input keys should follow the app storage job path convention."""

    assert (
        build_pipeline_input_key(job_id=123, filename="campaign.video.mp4")
        == "jobs/123/input.mp4"
    )


def test_save_pipeline_upload_calls_storage_save_upload() -> None:
    """Uploaded streams should be stored through StorageBase.save_upload."""

    storage = StorageFake()
    upload = BytesIO(b"video-bytes")

    input_file = save_pipeline_upload(
        storage=storage,
        job_id=10,
        filename="video.mp4",
        file=upload,
    )

    assert isinstance(input_file, PipelineInputFile)
    assert input_file.input_file_key == "jobs/10/input.mp4"
    assert input_file.input_file_uri == "fake://jobs/10/input.mp4"
    assert input_file.storage_backend == "fake"
    assert storage.upload_calls == [
        {
            "content": b"video-bytes",
            "destination_key": "jobs/10/input.mp4",
        }
    ]
    assert storage.file_calls == []


def test_save_pipeline_file_calls_storage_save_file() -> None:
    """Existing local files should be stored through StorageBase.save_file."""

    storage = StorageFake()

    input_file = save_pipeline_file(
        storage=storage,
        job_id=11,
        filename="audio.wav",
        source_path="/tmp/audio.wav",
    )

    assert isinstance(input_file, PipelineInputFile)
    assert input_file.input_file_key == "jobs/11/input.wav"
    assert input_file.input_file_uri == "fake://jobs/11/input.wav"
    assert input_file.storage_backend == "fake"
    assert storage.file_calls == [
        {
            "source_path": Path("/tmp/audio.wav"),
            "destination_key": "jobs/11/input.wav",
        }
    ]
    assert storage.upload_calls == []


def test_pipeline_input_file_returns_job_payload() -> None:
    """PipelineInputFile should expose the payload expected by mark_uploaded."""

    input_file = PipelineInputFile(
        stored_file=StoredFile(
            key="jobs/12/input.mov",
            uri="fake://jobs/12/input.mov",
            backend="fake",
        )
    )

    assert input_file.to_job_payload() == {
        "storage_backend": "fake",
        "input_file_key": "jobs/12/input.mov",
        "input_file_uri": "fake://jobs/12/input.mov",
    }


def test_stored_file_to_job_payload_returns_expected_fields() -> None:
    """StoredFile conversion should preserve backend, key, and uri fields."""

    stored_file = StoredFile(
        key="jobs/13/input.m4a",
        uri="fake://jobs/13/input.m4a",
        backend="fake",
    )

    assert stored_file_to_job_payload(stored_file) == {
        "storage_backend": "fake",
        "input_file_key": "jobs/13/input.m4a",
        "input_file_uri": "fake://jobs/13/input.m4a",
    }


class StorageFake(StorageBase):
    """Storage fake that records calls without touching external resources."""

    backend = "fake"

    def __init__(self) -> None:
        self.file_calls: list[dict[str, object]] = []
        self.upload_calls: list[dict[str, object]] = []

    def save_file(self, source_path: Path, destination_key: str) -> StoredFile:
        self.file_calls.append(
            {
                "source_path": source_path,
                "destination_key": destination_key,
            }
        )
        return self._stored_file(destination_key)

    def save_upload(
        self,
        file: BinaryIO,
        destination_key: str,
    ) -> StoredFile:
        self.upload_calls.append(
            {
                "content": file.read(),
                "destination_key": destination_key,
            }
        )
        return self._stored_file(destination_key)

    def exists(self, key: str) -> bool:
        return False

    def delete(self, key: str) -> None:
        return None

    def uri(self, key: str) -> str:
        return f"fake://{key}"

    def delete_prefix(self, prefix: str) -> None:
        return None

    def _stored_file(self, key: str) -> StoredFile:
        return StoredFile(
            key=key,
            uri=self.uri(key),
            backend=self.backend,
        )
