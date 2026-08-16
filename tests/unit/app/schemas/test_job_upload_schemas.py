from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.jobs import PresignedUploadRequest, PresignedUploadResponse


def test_presigned_upload_request_accepts_pipeline_and_metadata() -> None:
    request = PresignedUploadRequest(
        pipeline={
            "pipeline_type": "copy_analysis",
            "source_type": "video",
        },
        filename="source.mp4",
        content_type="video/mp4",
        size_bytes=1024,
    )

    assert request.pipeline.pipeline_type == "copy_analysis"
    assert request.filename == "source.mp4"
    assert request.content_type == "video/mp4"
    assert request.size_bytes == 1024


def test_presigned_upload_response_exposes_only_public_upload_fields() -> None:
    response = PresignedUploadResponse(
        job_id=42,
        object_key="jobs/42/input/source.mp4",
        upload_url="https://example.r2.cloudflarestorage.com/signed-upload",
        expires_in=900,
    )

    assert response.model_dump(mode="json") == {
        "job_id": 42,
        "object_key": "jobs/42/input/source.mp4",
        "upload_url": "https://example.r2.cloudflarestorage.com/signed-upload",
        "expires_in": 900,
    }


@pytest.mark.parametrize(
    "payload",
    [
        {
            "pipeline": {
                "pipeline_type": "copy_analysis",
                "source_type": "video",
            },
            "filename": "source.mp4",
            "content_type": "video/mp4",
            "size_bytes": 0,
        },
        {
            "pipeline": {
                "pipeline_type": "copy_analysis",
                "source_type": "video",
            },
            "filename": "source.mp4",
            "content_type": "video/mp4",
            "size_bytes": -1,
        },
    ],
)
def test_presigned_upload_request_rejects_invalid_size(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        PresignedUploadRequest.model_validate(payload)


def test_presigned_upload_response_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        PresignedUploadResponse(
            job_id=42,
            object_key="jobs/42/input/source.mp4",
            upload_url="https://example.r2.cloudflarestorage.com/signed-upload",
            expires_in=900,
            secret_access_key="must-not-be-public",
        )
