from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from app.errors import StorageError
from app.storage.base import StorageBase, StoredFile


class LocalStorage(StorageBase):
    """Filesystem-backed storage implementation."""

    backend = "local"
    chunk_size = 1024 * 1024

    def __init__(self, root_dir: Path | str) -> None:
        self.root_dir = Path(root_dir).expanduser().resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, source_path: Path, destination_key: str) -> StoredFile:
        source = Path(source_path).expanduser()

        if not source.is_file():
            raise StorageError(
                technical_message=f"Source file does not exist: {source}",
                details={"source_path": str(source)},
            )

        destination = self._resolve_path(destination_key)
        destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy2(source, destination)
        except OSError as error:
            raise StorageError(
                technical_message=f"Failed to save file to local storage: {error}",
                details={
                    "source_path": str(source),
                    "destination_key": destination_key,
                },
            ) from error

        return StoredFile(
            key=destination_key,
            uri=str(destination),
            backend=self.backend,
        )

    def save_upload(self, file: BinaryIO, destination_key: str) -> StoredFile:
        destination = self._resolve_path(destination_key)
        temporary_destination = destination.with_name(
            f"{destination.name}.{uuid.uuid4().hex}.part"
        )
        destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            with temporary_destination.open("wb") as output:
                while chunk := file.read(self.chunk_size):
                    output.write(chunk)

            temporary_destination.replace(destination)
        except OSError as error:
            self._delete_partial_file(temporary_destination)
            raise StorageError(
                technical_message=f"Failed to save upload to local storage: {error}",
                details={"destination_key": destination_key},
            ) from error
        except Exception:
            self._delete_partial_file(temporary_destination)
            raise

        return StoredFile(
            key=destination_key,
            uri=str(destination),
            backend=self.backend,
        )

    def download_file(self, key: str, destination_path: Path) -> Path:
        """Copy a stored file atomically to an exact local destination."""

        source = self._resolve_path(key)
        destination = Path(destination_path).expanduser().resolve()

        if not source.is_file():
            raise StorageError(
                technical_message=f"Local storage file does not exist: {key}",
                details={"key": key},
            )

        if source == destination:
            return destination

        temporary_destination = self._temporary_path(destination)

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, temporary_destination)
            temporary_destination.replace(destination)
        except OSError as error:
            self._delete_partial_file(temporary_destination)
            raise StorageError(
                technical_message=(
                    f"Failed to download file from local storage: {error}"
                ),
                details={
                    "key": key,
                    "destination_path": str(destination),
                },
            ) from error
        except Exception:
            self._delete_partial_file(temporary_destination)
            raise

        return destination

    def exists(self, key: str) -> bool:
        try:
            return self._resolve_path(key).exists()
        except StorageError:
            return False

    def delete(self, key: str) -> None:
        path = self._resolve_path(key)

        if not path.exists():
            return

        if not path.is_file():
            raise StorageError(
                technical_message=f"Storage key is not a file: {key}",
                details={"key": key},
            )

        try:
            path.unlink()
        except OSError as error:
            raise StorageError(
                technical_message=f"Failed to delete local storage file: {error}",
                details={"key": key},
            ) from error

    def uri(self, key: str) -> str:
        return str(self._resolve_path(key))

    def delete_prefix(self, prefix: str) -> None:
        path = self._resolve_path(prefix)

        if not path.exists():
            return

        if path.is_file():
            self.delete(prefix)
            return

        if not path.is_dir():
            raise StorageError(
                technical_message=f"Storage prefix is not a directory: {prefix}",
                details={"prefix": prefix},
            )

        try:
            shutil.rmtree(path)
        except OSError as error:
            raise StorageError(
                technical_message=f"Failed to delete local storage prefix: {error}",
                details={"prefix": prefix},
            ) from error

    def _resolve_path(self, key: str) -> Path:
        if not key or Path(key).is_absolute():
            raise StorageError(
                technical_message=f"Invalid local storage key: {key}",
                details={"key": key},
            )

        path = (self.root_dir / key).resolve()

        if self.root_dir not in path.parents and path != self.root_dir:
            raise StorageError(
                technical_message=f"Local storage key escapes root directory: {key}",
                details={"key": key},
            )

        return path

    def _delete_partial_file(self, path: Path) -> None:
        try:
            if path.exists() and path.is_file():
                path.unlink()
        except OSError:
            pass

    @staticmethod
    def _temporary_path(destination: Path) -> Path:
        return destination.with_name(
            f"{destination.name}.{uuid.uuid4().hex}.part"
        )
