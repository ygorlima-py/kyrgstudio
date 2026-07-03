from __future__ import annotations

from pathlib import Path
from typing import Any, BinaryIO

from app.errors import StorageError
from app.storage.base import StorageBase, StoredFile


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

    def _load_boto3(self) -> tuple[Any, type[Exception], type[Exception]]:
        try:
            import boto3
            from botocore.exceptions import BotoCoreError, ClientError
        except ImportError as error:
            raise StorageError(
                technical_message=(
                    "S3Storage requires boto3 and botocore to be installed."
                ),
                details={"missing_dependency": "boto3"},
            ) from error

        return boto3, ClientError, BotoCoreError


__all__ = ["S3Storage"]
