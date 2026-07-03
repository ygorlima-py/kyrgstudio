from __future__ import annotations

from pathlib import Path
from typing import Any, BinaryIO

from app.errors import StorageError
from app.storage.base import StorageBase, StoredFile


class GCPStorage(StorageBase):
    """Google Cloud Storage implementation."""

    backend = "gcp"

    def __init__(
        self,
        bucket: str,
        credentials_path: str | None = None,
        project: str | None = None,
        uri_scheme: str = "gs",
    ) -> None:
        if not bucket:
            raise StorageError(
                technical_message="GCP bucket is required.",
                details={"bucket": bucket},
            )

        if not uri_scheme:
            raise StorageError(
                technical_message="GCP URI scheme is required.",
                details={"uri_scheme": uri_scheme},
            )

        (
            storage,
            service_account,
            not_found_error,
            google_api_error,
        ) = self._load_google_storage()

        try:
            credentials = None

            if credentials_path is not None:
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path
                )

            self.client = storage.Client(
                project=project,
                credentials=credentials,
            )
            self.bucket = self.client.bucket(bucket)
        except (google_api_error, OSError, TypeError, ValueError) as error:
            raise StorageError(
                technical_message=f"Failed to create GCP storage client: {error}",
                details={"bucket": bucket, "project": project},
            ) from error

        self.bucket_name = bucket
        self.uri_scheme = uri_scheme
        self._not_found_error = not_found_error
        self._google_api_error = google_api_error

    def save_file(self, source_path: Path, destination_key: str) -> StoredFile:
        source = Path(source_path).expanduser()
        key = self._validate_key(destination_key)

        if not source.is_file():
            raise StorageError(
                technical_message=f"Source file does not exist: {source}",
                details={"source_path": str(source)},
            )

        try:
            self.bucket.blob(key).upload_from_filename(str(source))
        except self._google_api_error as error:
            raise StorageError(
                technical_message=f"Failed to upload file to GCP storage: {error}",
                details={
                    "bucket": self.bucket_name,
                    "source_path": str(source),
                    "destination_key": key,
                },
            ) from error

        return self._stored_file(key)

    def save_upload(self, file: BinaryIO, destination_key: str) -> StoredFile:
        key = self._validate_key(destination_key)

        try:
            self.bucket.blob(key).upload_from_file(file, rewind=False)
        except self._google_api_error as error:
            raise StorageError(
                technical_message=f"Failed to upload stream to GCP storage: {error}",
                details={
                    "bucket": self.bucket_name,
                    "destination_key": key,
                },
            ) from error

        return self._stored_file(key)

    def exists(self, key: str) -> bool:
        try:
            resolved_key = self._validate_key(key)
            return self.bucket.blob(resolved_key).exists()
        except StorageError:
            return False
        except self._not_found_error:
            return False
        except self._google_api_error as error:
            raise StorageError(
                technical_message=f"Failed to check GCP object existence: {error}",
                details={"bucket": self.bucket_name, "key": key},
            ) from error

    def delete(self, key: str) -> None:
        resolved_key = self._validate_key(key)

        try:
            self.bucket.blob(resolved_key).delete()
        except self._not_found_error:
            return
        except self._google_api_error as error:
            raise StorageError(
                technical_message=f"Failed to delete GCP object: {error}",
                details={"bucket": self.bucket_name, "key": resolved_key},
            ) from error

    def uri(self, key: str) -> str:
        resolved_key = self._validate_key(key)
        return f"{self.uri_scheme}://{self.bucket_name}/{resolved_key}"

    def delete_prefix(self, prefix: str) -> None:
        resolved_prefix = self._validate_key(prefix)

        if not resolved_prefix.endswith("/"):
            resolved_prefix = f"{resolved_prefix}/"

        try:
            with self.client.batch():
                for blob in self.bucket.list_blobs(prefix=resolved_prefix):
                    blob.delete()
        except self._not_found_error:
            return
        except self._google_api_error as error:
            raise StorageError(
                technical_message=f"Failed to delete GCP prefix: {error}",
                details={"bucket": self.bucket_name, "prefix": resolved_prefix},
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
                technical_message=f"Invalid GCP storage key: {key}",
                details={"key": key},
            )

        parts = Path(key).parts

        if any(part in {"", ".", ".."} for part in parts):
            raise StorageError(
                technical_message=f"Invalid GCP storage key: {key}",
                details={"key": key},
            )

        return key

    def _load_google_storage(self) -> tuple[
        Any,
        Any,
        type[Exception],
        type[Exception],
    ]:
        try:
            from google.api_core.exceptions import GoogleAPICallError, NotFound # type: ignore
            from google.cloud import storage # type: ignore
            from google.oauth2 import service_account
        except ImportError as error:
            raise StorageError(
                technical_message=(
                    "GCPStorage requires google-cloud-storage to be installed."
                ),
                details={"missing_dependency": "google-cloud-storage"},
            ) from error

        return storage, service_account, NotFound, GoogleAPICallError


__all__ = ["GCPStorage"]
