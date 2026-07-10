from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


@dataclass(frozen=True)
class StoredFile:
    """Reference to a file stored by a storage backend."""

    key: str
    uri: str
    backend: str


class StorageBase(ABC):
    """Base contract for application file storage.

    Implementations should keep observable behavior consistent across backends:
    missing keys are treated as absent, delete operations on missing keys are
    no-ops, and invalid keys may raise a storage-level error.
    """

    @abstractmethod
    def save_file(self, source_path: Path, destination_key: str) -> StoredFile:
        ...

    @abstractmethod
    def save_upload(self, file: BinaryIO, destination_key: str) -> StoredFile:
        ...

    @abstractmethod
    def download_file(self, key: str, destination_path: Path) -> Path:
        """Download a complete stored file to an exact local destination.

        Implementations must avoid exposing partial downloads at
        ``destination_path`` and return the path only after the file is fully
        available locally.
        """

        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return whether a complete stored file exists for the given key."""

        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete one stored file; missing keys should be treated as no-op."""

        ...

    @abstractmethod
    def uri(self, key: str) -> str:
        ...

    @abstractmethod
    def delete_prefix(self, prefix: str) -> None:
        """Delete every stored file under a prefix; missing prefixes are no-op."""

        ...
