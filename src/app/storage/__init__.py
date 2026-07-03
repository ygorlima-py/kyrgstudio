"""Application storage public API.

Cloud providers are intentionally not imported here. They depend on optional
SDKs, and importing this package should not require boto3 or google-cloud-storage
when the active backend is local.
"""

from app.storage.base import StorageBase, StoredFile
from app.storage.factory import StorageBackend, create_storage
from app.storage.local import LocalStorage
from app.storage.paths import job_audio_key, job_input_key, job_prefix


__all__ = [
    "LocalStorage",
    "StorageBackend",
    "StorageBase",
    "StoredFile",
    "create_storage",
    "job_audio_key",
    "job_input_key",
    "job_prefix",
]
