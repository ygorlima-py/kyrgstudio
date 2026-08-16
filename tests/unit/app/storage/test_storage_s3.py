from __future__ import annotations

import pytest

from app.errors import StorageError
from app.storage.s3 import S3Storage


class PresignedUrlClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_presigned_url(self, **kwargs: object) -> str:
        self.calls.append(kwargs)
        return "https://r2.example.test/signed-upload"


def _storage(client: PresignedUrlClient) -> S3Storage:
    storage = object.__new__(S3Storage)
    storage.bucket = "kyrgstudio-media"
    storage.uri_scheme = "r2"
    storage.client = client
    return storage


def test_create_presigned_upload_url_signs_put_request() -> None:
    client = PresignedUrlClient()
    storage = _storage(client)

    result = storage.create_presigned_upload_url(
        destination_key="jobs/10/input.mp4",
        content_type="video/mp4",
        expires_in=900,
    )

    assert result == "https://r2.example.test/signed-upload"
    assert client.calls == [
        {
            "ClientMethod": "put_object",
            "Params": {
                "Bucket": "kyrgstudio-media",
                "Key": "jobs/10/input.mp4",
                "ContentType": "video/mp4",
            },
            "ExpiresIn": 900,
            "HttpMethod": "PUT",
        }
    ]


@pytest.mark.parametrize(
    ("content_type", "expires_in"),
    [("", 900), ("video/mp4", 0), ("video/mp4", -1), ("video/mp4", 901)],
)
def test_create_presigned_upload_url_rejects_invalid_options(
    content_type: str,
    expires_in: int,
) -> None:
    storage = _storage(PresignedUrlClient())

    with pytest.raises(StorageError):
        storage.create_presigned_upload_url(
            destination_key="jobs/10/input.mp4",
            content_type=content_type,
            expires_in=expires_in,
        )
