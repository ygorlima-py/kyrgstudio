from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, BinaryIO

from app.errors import StorageError
from app.storage.base import (
    MAX_PRESIGNED_UPLOAD_TTL_SECONDS,
    StorageBase,
    StoredFile,
    StoredObjectMetadata,
)


class S3Storage(StorageBase):
    """S3-backed storage implementation."""

    backend = "s3"
    max_delete_objects = 1000

    def __init__(
        self,
        bucket: str,
        region_name: str | None = None,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        uri_scheme: str = "s3",
    ) -> None:
        if not bucket:
            raise StorageError(
                technical_message="S3 bucket is required.",
                details={"bucket": bucket},
            )

        if not uri_scheme:
            raise StorageError(
                technical_message="S3 URI scheme is required.",
                details={"uri_scheme": uri_scheme},
            )

        if (access_key is None) != (secret_key is None):
            raise StorageError(
                technical_message=(
                    "S3 access_key and secret_key must be provided together."
                ),
                details={
                    "has_access_key": access_key is not None,
                    "has_secret_key": secret_key is not None,
                },
            )

        boto3, client_error, boto_core_error = self._load_boto3()

        client_kwargs: dict[str, Any] = {}

        if region_name is not None:
            client_kwargs["region_name"] = region_name

        if endpoint_url is not None:
            client_kwargs["endpoint_url"] = endpoint_url

        if access_key is not None and secret_key is not None:
            client_kwargs["aws_access_key_id"] = access_key
            client_kwargs["aws_secret_access_key"] = secret_key

        self.bucket = bucket
        self.uri_scheme = uri_scheme
        self.client = boto3.client("s3", **client_kwargs)
        self._client_error = client_error
        self._boto_core_error = boto_core_error

    def save_file(self, source_path: Path, destination_key: str) -> StoredFile:
        source = Path(source_path).expanduser()
        key = self._validate_key(destination_key)

        if not source.is_file():
            raise StorageError(
                technical_message=f"Source file does not exist: {source}",
                details={"source_path": str(source)},
            )

        try:
            self.client.upload_file(str(source), self.bucket, key)
        except self._storage_errors() as error:
            raise StorageError(
                technical_message=f"Failed to upload file to S3 storage: {error}",
                details={
                    "bucket": self.bucket,
                    "source_path": str(source),
                    "destination_key": key,
                },
            ) from error

        return self._stored_file(key)

    def save_upload(self, file: BinaryIO, destination_key: str) -> StoredFile:
        key = self._validate_key(destination_key)

        try:
            self.client.upload_fileobj(file, self.bucket, key)
        except self._storage_errors() as error:
            raise StorageError(
                technical_message=f"Failed to upload stream to S3 storage: {error}",
                details={
                    "bucket": self.bucket,
                    "destination_key": key,
                },
            ) from error

        return self._stored_file(key)

    def create_presigned_upload_url(
        self,
        *,
        destination_key: str,
        content_type: str,
        expires_in: int,
    ) -> str:
        """Create a temporary URL for a direct browser upload.

        The signed request includes the content type, so the browser must send
        the same value with its ``PUT`` request. Credentials never leave the
        server; only the short-lived signed URL is returned to the caller.
        """

        key = self._validate_key(destination_key)

        if not content_type.strip():
            raise StorageError(
                technical_message="Presigned upload content type is required.",
                details={"destination_key": key},
            )

        if (
            isinstance(expires_in, bool)
            or not isinstance(expires_in, int)
            or expires_in <= 0
            or expires_in > MAX_PRESIGNED_UPLOAD_TTL_SECONDS
        ):
            raise StorageError(
                technical_message=(
                    "Presigned upload expiry must be between one second and "
                    f"{MAX_PRESIGNED_UPLOAD_TTL_SECONDS} seconds."
                ),
                details={
                    "expires_in": expires_in,
                    "max_expires_in": MAX_PRESIGNED_UPLOAD_TTL_SECONDS,
                },
            )

        try:
            return self.client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
                HttpMethod="PUT",
            )
        except self._storage_errors() as error:
            raise StorageError(
                technical_message=(
                    "Failed to create presigned S3 upload URL."
                ),
                details={
                    "backend": self.backend,
                    "bucket": self.bucket,
                    "destination_key": key,
                },
            ) from error

    def download_file(self, key: str, destination_path: Path) -> Path:
        """Download an S3-compatible object atomically to local storage."""

        resolved_key = self._validate_key(key)
        destination = Path(destination_path).expanduser().resolve()
        temporary_destination = self._temporary_path(destination)

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            self.client.download_file(
                self.bucket,
                resolved_key,
                str(temporary_destination),
            )
            temporary_destination.replace(destination)
        except self._storage_errors() as error:
            self._delete_partial_file(temporary_destination)
            raise StorageError(
                technical_message=(
                    "Failed to download file from S3-compatible storage: "
                    f"{error}"
                ),
                details={
                    "backend": self.backend,
                    "bucket": self.bucket,
                    "key": resolved_key,
                    "destination_path": str(destination),
                },
            ) from error
        except OSError as error:
            self._delete_partial_file(temporary_destination)
            raise StorageError(
                technical_message=f"Failed to finalize downloaded file: {error}",
                details={
                    "backend": self.backend,
                    "bucket": self.bucket,
                    "key": resolved_key,
                    "destination_path": str(destination),
                },
            ) from error
        except Exception:
            self._delete_partial_file(temporary_destination)
            raise

        return destination

    def exists(self, key: str) -> bool:
        try:
            resolved_key = self._validate_key(key)
            self.client.head_object(Bucket=self.bucket, Key=resolved_key)
        except StorageError:
            return False
        except self._client_error as error:
            if self._is_not_found_error(error):
                return False

            raise StorageError(
                technical_message=f"Failed to check S3 object existence: {error}",
                details={"bucket": self.bucket, "key": key},
            ) from error
        except self._boto_core_error as error:
            raise StorageError(
                technical_message=f"Failed to check S3 object existence: {error}",
                details={"bucket": self.bucket, "key": key},
            ) from error

        return True

    def get_object_metadata(self, key: str) -> StoredObjectMetadata | None:
        """Inspect one object without downloading its contents."""

        resolved_key = self._validate_key(key)

        try:
            response = self.client.head_object(
                Bucket=self.bucket,
                Key=resolved_key,
            )
        except self._client_error as error:
            if self._is_not_found_error(error):
                return None

            raise StorageError(
                technical_message="Failed to inspect S3 object metadata.",
                details={"bucket": self.bucket, "key": resolved_key},
            ) from error
        except self._boto_core_error as error:
            raise StorageError(
                technical_message="Failed to inspect S3 object metadata.",
                details={"bucket": self.bucket, "key": resolved_key},
            ) from error

        size_bytes = response.get("ContentLength")

        if isinstance(size_bytes, bool) or not isinstance(size_bytes, int):
            raise StorageError(
                technical_message="Stored object metadata has no valid size.",
                details={"bucket": self.bucket, "key": resolved_key},
            )

        content_type = response.get("ContentType")
        normalized_content_type = (
            str(content_type).partition(";")[0].strip().lower()
            if content_type is not None
            else None
        )

        return StoredObjectMetadata(
            key=resolved_key,
            size_bytes=size_bytes,
            content_type=normalized_content_type or None,
        )

    def delete(self, key: str) -> None:
        resolved_key = self._validate_key(key)

        try:
            self.client.delete_object(Bucket=self.bucket, Key=resolved_key)
        except self._storage_errors() as error:
            raise StorageError(
                technical_message=f"Failed to delete S3 object: {error}",
                details={"bucket": self.bucket, "key": resolved_key},
            ) from error

    def uri(self, key: str) -> str:
        resolved_key = self._validate_key(key)
        return f"{self.uri_scheme}://{self.bucket}/{resolved_key}"

    def delete_prefix(self, prefix: str) -> None:
        resolved_prefix = self._validate_key(prefix)

        if not resolved_prefix.endswith("/"):
            resolved_prefix = f"{resolved_prefix}/"

        try:
            paginator = self.client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket, Prefix=resolved_prefix)

            for page in pages:
                objects = [
                    {"Key": item["Key"]}
                    for item in page.get("Contents", [])
                ]

                for batch in self._chunk_objects(objects):
                    response = self.client.delete_objects(
                        Bucket=self.bucket,
                        Delete={
                            "Objects": batch,
                            "Quiet": True,
                        },
                    )
                    errors = response.get("Errors") or []

                    if errors:
                        raise StorageError(
                            technical_message=(
                                "Failed to delete one or more S3 objects."
                            ),
                            details={
                                "bucket": self.bucket,
                                "prefix": resolved_prefix,
                                "errors": errors,
                            },
                        )
        except self._storage_errors() as error:
            raise StorageError(
                technical_message=f"Failed to delete S3 prefix: {error}",
                details={"bucket": self.bucket, "prefix": resolved_prefix},
            ) from error

    def _stored_file(self, key: str) -> StoredFile:
        return StoredFile(
            key=key,
            uri=self.uri(key),
            backend=self.backend,
        )

    def _validate_key(self, key: str) -> str:
        if not key or Path(key).is_absolute():
            raise StorageError(
                technical_message=f"Invalid S3 storage key: {key}",
                details={"key": key},
            )

        parts = Path(key).parts

        if any(part in {"", ".", ".."} for part in parts):
            raise StorageError(
                technical_message=f"Invalid S3 storage key: {key}",
                details={"key": key},
            )

        return key

    def _storage_errors(self) -> tuple[type[Exception], type[Exception]]:
        return (self._client_error, self._boto_core_error)

    def _is_not_found_error(self, error: Exception) -> bool:
        response = getattr(error, "response", {})
        code = response.get("Error", {}).get("Code")
        return code in {"404", "NoSuchKey", "NotFound"}

    def _chunk_objects(
        self,
        objects: list[dict[str, str]],
    ) -> list[list[dict[str, str]]]:
        return [
            objects[index:index + self.max_delete_objects]
            for index in range(0, len(objects), self.max_delete_objects)
        ]

    @staticmethod
    def _temporary_path(destination: Path) -> Path:
        return destination.with_name(
            f"{destination.name}.{uuid.uuid4().hex}.part"
        )

    @staticmethod
    def _delete_partial_file(path: Path) -> None:
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass

    def _load_boto3(self) -> tuple[Any, type[Exception], type[Exception]]:
        try:
            import boto3  # type: ignore
            from botocore.exceptions import (  # type: ignore
                BotoCoreError,
                ClientError,
            )
        except ImportError as error:
            raise StorageError(
                technical_message=(
                    "S3Storage requires boto3 and botocore to be installed."
                ),
                details={"missing_dependency": "boto3"},
            ) from error

        return boto3, ClientError, BotoCoreError


__all__ = ["S3Storage"]
