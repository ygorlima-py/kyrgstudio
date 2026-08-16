from __future__ import annotations

from app.storage.base import MAX_PRESIGNED_UPLOAD_TTL_SECONDS
from app.storage.r2 import R2Storage


class PresignedUrlClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_presigned_url(self, **kwargs: object) -> str:
        self.calls.append(kwargs)
        return "https://r2.example.test/signed-upload"


def test_r2_storage_uses_s3_presigned_put_contract() -> None:
    """R2 inherits the signed PUT behavior without exposing credentials."""

    client = PresignedUrlClient()
    storage = object.__new__(R2Storage)
    storage.bucket = "kyrgstudio-media"
    storage.uri_scheme = "r2"
    storage.client = client

    result = storage.create_presigned_upload_url(
        destination_key="jobs/10/input.mp4",
        content_type="video/mp4",
        expires_in=MAX_PRESIGNED_UPLOAD_TTL_SECONDS,
    )

    assert storage.backend == "r2"
    assert result == "https://r2.example.test/signed-upload"
    assert client.calls == [
        {
            "ClientMethod": "put_object",
            "Params": {
                "Bucket": "kyrgstudio-media",
                "Key": "jobs/10/input.mp4",
                "ContentType": "video/mp4",
            },
            "ExpiresIn": MAX_PRESIGNED_UPLOAD_TTL_SECONDS,
            "HttpMethod": "PUT",
        }
    ]
