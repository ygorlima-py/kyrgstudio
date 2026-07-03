from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from app.errors import StorageError
from app.storage.base import StorageBase
from app.storage.local import LocalStorage


StorageBackend = Literal["local", "s3", "r2", "gcp"]

_BACKEND_ALIASES: dict[str, StorageBackend] = {
    "local": "local",
    "filesystem": "local",
    "fs": "local",
    "s3": "s3",
    "aws": "s3",
    "aws_s3": "s3",
    "r2": "r2",
    "cloudflare": "r2",
    "cloudflare_r2": "r2",
    "gcp": "gcp",
    "gcs": "gcp",
    "google_cloud_storage": "gcp",
}


def create_storage(settings: object | None = None) -> StorageBase:
    """Build the configured storage backend.

    The factory accepts any settings object with the expected attributes. This
    keeps the storage layer independent from one concrete settings class while
    still validating required configuration at the boundary.
    """

    resolved_settings = settings or _load_default_settings()
    backend = _normalize_backend(
        _optional_setting(resolved_settings, "storage_backend", "local")
    )

    if backend == "local":
        return _create_local_storage(resolved_settings)

    if backend == "s3":
        return _create_s3_storage(resolved_settings)

    if backend == "r2":
        return _create_r2_storage(resolved_settings)

    if backend == "gcp":
        return _create_gcp_storage(resolved_settings)

    raise StorageError(
        technical_message=f"Unsupported storage backend: {backend}",
        details={"storage_backend": backend},
    )


def _create_local_storage(settings: object) -> LocalStorage:
    storage_dir = _required_setting(settings, "storage_dir", backend="local")
    return LocalStorage(_validate_local_storage_dir(storage_dir))


def _create_s3_storage(settings: object) -> StorageBase:
    from app.storage.s3 import S3Storage

    return S3Storage(
        bucket=_required_setting(settings, "s3_bucket", backend="s3"),
        region_name=_optional_setting(
            settings,
            "s3_region_name",
            _optional_setting(settings, "s3_region"),
        ),
        endpoint_url=_optional_setting(settings, "s3_endpoint_url"),
        access_key=_optional_setting(settings, "s3_access_key"),
        secret_key=_optional_setting(settings, "s3_secret_key"),
    )


def _create_r2_storage(settings: object) -> StorageBase:
    from app.storage.r2 import R2Storage

    return R2Storage(
        account_id=_required_setting(settings, "r2_account_id", backend="r2"),
        bucket=_required_setting(settings, "r2_bucket", backend="r2"),
        access_key=_required_setting(settings, "r2_access_key", backend="r2"),
        secret_key=_required_setting(settings, "r2_secret_key", backend="r2"),
    )


def _create_gcp_storage(settings: object) -> StorageBase:
    from app.storage.gcp import GCPStorage

    return GCPStorage(
        bucket=_required_setting(settings, "gcp_bucket", backend="gcp"),
        credentials_path=_optional_setting(settings, "gcp_credentials_path"),
        project=_optional_setting(settings, "gcp_project"),
    )


def _load_default_settings() -> object:
    from app.settings import load_settings

    return load_settings()


def _validate_local_storage_dir(value: str) -> Path:
    path = Path(value).expanduser().resolve()

    if path == path.parent:
        raise StorageError(
            technical_message="Local storage directory cannot be filesystem root.",
            details={"storage_dir": str(path)},
        )

    if path == Path.home().resolve():
        raise StorageError(
            technical_message="Local storage directory cannot be the home directory.",
            details={"storage_dir": str(path)},
        )

    return path


def _normalize_backend(value: Any) -> StorageBackend:
    if value is None:
        return "local"

    backend = str(value).strip().lower().replace("-", "_")

    if not backend:
        return "local"

    if backend not in _BACKEND_ALIASES:
        raise StorageError(
            technical_message=f"Unsupported storage backend: {value}",
            details={
                "storage_backend": value,
                "supported_backends": sorted(set(_BACKEND_ALIASES.values())),
            },
        )

    return _BACKEND_ALIASES[backend]


def _required_setting(settings: object, name: str, *, backend: str) -> str:
    value = _optional_setting(settings, name)

    if value is None or str(value).strip() == "":
        raise StorageError(
            technical_message=(
                f"Storage backend '{backend}' requires setting '{name}'."
            ),
            details={
                "storage_backend": backend,
                "missing_setting": name,
            },
        )

    return str(value)


def _optional_setting(
    settings: object,
    name: str,
    default: Any | None = None,
) -> Any | None:
    return getattr(settings, name, default)


__all__ = [
    "StorageBackend",
    "create_storage",
]
