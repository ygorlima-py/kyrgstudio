from __future__ import annotations

from app.errors import StorageError
from app.storage.s3 import S3Storage


class R2Storage(S3Storage):
    """Cloudflare R2 storage implementation using the S3-compatible API."""

    backend = "r2"

    def __init__(
        self,
        account_id: str,
        bucket: str,
        access_key: str,
        secret_key: str,
    ) -> None:
        if not account_id:
            raise StorageError(
                technical_message="Cloudflare R2 account_id is required.",
                details={"account_id": account_id},
            )

        super().__init__(
            bucket=bucket,
            region_name="auto",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            access_key=access_key,
            secret_key=secret_key,
            uri_scheme="r2",
        )


__all__ = ["R2Storage"]
