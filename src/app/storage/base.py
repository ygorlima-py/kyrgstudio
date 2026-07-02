from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class StoredFile:
    key: str
    uri: str
    backend: str


class StorageBase(ABC):
    
    @abstractmethod
    def save_file(self, source_path: Path, destination_key: str) -> StoredFile:
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        ...

    @abstractmethod
    def uri(self, key: str) -> str:
        ...