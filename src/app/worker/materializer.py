"""Resolve stored worker inputs into safe local filesystem paths.

Local storage files are returned in place because they are already accessible
to FFmpeg and the workflow layer. Remote objects are downloaded into an
isolated workspace owned by this materializer and removed explicitly through
``cleanup`` after worker execution.
"""

from __future__ import annotations

import shutil
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from tempfile import mkdtemp
from typing import Any

from app.errors import StorageError
from app.schemas.workflow import ResolvedInputFile
from app.storage.base import StorageBase


LOCAL_STORAGE_BACKEND = "local"
WORKSPACE_PREFIX = "kyrg-job-"
DEFAULT_INPUT_FILENAME = "input"
MAX_SUFFIX_LENGTH = 16


class StorageFileMaterializer:
    """Materialize one storage input as a local file for worker execution.

    The class structurally implements ``WorkerFileResolver`` from
    ``app.worker.runner``. It intentionally does not import or inherit from the
    protocol, which keeps the runner and materializer modules independent and
    avoids an import cycle when the runner adopts this implementation.
    """

    def __init__(
        self,
        storage: StorageBase,
        *,
        workspace_root: Path | str | None = None,
    ) -> None:
        self.storage = storage
        self.storage_backend = _storage_backend(storage)
        self.workspace_root = _prepare_workspace_root(workspace_root)
        self._owned_workspaces: set[Path] = set()

    def resolve(self, job: Any) -> ResolvedInputFile:
        """Return the job input as a validated local file reference.

        Local inputs are used directly. Remote inputs are downloaded into a
        unique workspace and marked for cleanup.
        """

        job_id = _job_id(job)
        storage_backend = _required_job_text(job, "storage_backend")
        input_file_key = _required_job_text(job, "input_file_key")
        input_file_uri = _required_job_text(job, "input_file_uri")

        self._ensure_backend_matches_job(
            job_id=job_id,
            storage_backend=storage_backend,
        )

        if not self.storage.exists(input_file_key):
            raise StorageError(
                technical_message="Stored worker input file does not exist.",
                step="materializing_input",
                details={
                    "job_id": job_id,
                    "storage_backend": storage_backend,
                    "input_file_key": input_file_key,
                    "input_file_uri": input_file_uri,
                },
            )

        if storage_backend == LOCAL_STORAGE_BACKEND:
            return self._resolve_local_file(
                job_id=job_id,
                input_file_key=input_file_key,
                input_file_uri=input_file_uri,
            )

        return self._download_remote_file(
            job_id=job_id,
            storage_backend=storage_backend,
            input_file_key=input_file_key,
            input_file_uri=input_file_uri,
        )

    def cleanup(self, resolved_file: ResolvedInputFile) -> None:
        """Remove only a temporary workspace created by this materializer.

        Cleanup is a no-op for local storage files. For remote inputs, both the
        ownership registry and path containment are checked before recursive
        deletion, preventing an arbitrary path from being removed.
        """

        if not resolved_file.should_cleanup:
            return

        cleanup_root = resolved_file.cleanup_root

        if cleanup_root is None:
            raise StorageError(
                technical_message="Temporary input is missing its cleanup root.",
                step="cleaning_materialized_input",
                details={
                    "input_file_key": resolved_file.input_file_key,
                    "local_path": str(resolved_file.local_path),
                },
            )

        workspace = cleanup_root.expanduser().resolve()
        local_path = resolved_file.local_path.expanduser().resolve()

        if workspace not in local_path.parents:
            raise StorageError(
                technical_message=(
                    "Materialized input is outside its cleanup workspace."
                ),
                step="cleaning_materialized_input",
                details={
                    "cleanup_root": str(workspace),
                    "local_path": str(local_path),
                },
            )

        if workspace not in self._owned_workspaces:
            if not workspace.exists():
                return

            raise StorageError(
                technical_message=(
                    "Refusing to remove a workspace not owned by this "
                    "materializer."
                ),
                step="cleaning_materialized_input",
                details={"cleanup_root": str(workspace)},
            )

        self._delete_workspace(workspace)

    def _resolve_local_file(
        self,
        *,
        job_id: int,
        input_file_key: str,
        input_file_uri: str,
    ) -> ResolvedInputFile:
        local_path = Path(self.storage.uri(input_file_key)).expanduser().resolve()

        if not local_path.is_file():
            raise StorageError(
                technical_message="Resolved local worker input is not a file.",
                step="materializing_input",
                details={
                    "job_id": job_id,
                    "input_file_key": input_file_key,
                    "local_path": str(local_path),
                },
            )

        return ResolvedInputFile(
            storage_backend=LOCAL_STORAGE_BACKEND,
            input_file_key=input_file_key,
            input_file_uri=input_file_uri,
            local_path=local_path,
            should_cleanup=False,
            cleanup_root=None,
        )

    def _download_remote_file(
        self,
        *,
        job_id: int,
        storage_backend: str,
        input_file_key: str,
        input_file_uri: str,
    ) -> ResolvedInputFile:
        workspace = self._create_workspace(job_id)
        destination = workspace / _materialized_filename(input_file_key)

        try:
            downloaded_path = self.storage.download_file(
                input_file_key,
                destination,
            ).expanduser().resolve()

            if downloaded_path != destination:
                raise StorageError(
                    technical_message=(
                        "Storage downloaded the input to an unexpected path."
                    ),
                    step="materializing_input",
                    details={
                        "job_id": job_id,
                        "expected_path": str(destination),
                        "downloaded_path": str(downloaded_path),
                    },
                )

            if not downloaded_path.is_file():
                raise StorageError(
                    technical_message=(
                        "Downloaded worker input is not a complete local file."
                    ),
                    step="materializing_input",
                    details={
                        "job_id": job_id,
                        "input_file_key": input_file_key,
                        "local_path": str(downloaded_path),
                    },
                )
        except Exception:
            self._delete_workspace(workspace, suppress_errors=True)
            raise

        return ResolvedInputFile(
            storage_backend=storage_backend,
            input_file_key=input_file_key,
            input_file_uri=input_file_uri,
            local_path=downloaded_path,
            should_cleanup=True,
            cleanup_root=workspace,
        )

    def _ensure_backend_matches_job(
        self,
        *,
        job_id: int,
        storage_backend: str,
    ) -> None:
        if storage_backend == self.storage_backend:
            return

        raise StorageError(
            technical_message=(
                "Configured storage backend does not match the job input."
            ),
            step="materializing_input",
            details={
                "job_id": job_id,
                "job_storage_backend": storage_backend,
                "configured_storage_backend": self.storage_backend,
            },
        )

    def _create_workspace(self, job_id: int) -> Path:
        try:
            workspace = Path(
                mkdtemp(
                    prefix=f"{WORKSPACE_PREFIX}{job_id}-",
                    dir=(
                        str(self.workspace_root)
                        if self.workspace_root is not None
                        else None
                    ),
                )
            ).resolve()
        except OSError as error:
            raise StorageError(
                technical_message=f"Failed to create worker workspace: {error}",
                step="materializing_input",
                details={
                    "job_id": job_id,
                    "workspace_root": (
                        str(self.workspace_root)
                        if self.workspace_root is not None
                        else None
                    ),
                },
            ) from error

        self._owned_workspaces.add(workspace)
        return workspace

    def _delete_workspace(
        self,
        workspace: Path,
        *,
        suppress_errors: bool = False,
    ) -> None:
        try:
            if workspace.exists():
                shutil.rmtree(workspace)
        except OSError as error:
            if suppress_errors:
                return

            raise StorageError(
                technical_message=f"Failed to clean worker workspace: {error}",
                step="cleaning_materialized_input",
                details={"cleanup_root": str(workspace)},
            ) from error

        self._owned_workspaces.discard(workspace)


def _prepare_workspace_root(value: Path | str | None) -> Path | None:
    if value is None:
        return None

    root = Path(value).expanduser().resolve()

    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise StorageError(
            technical_message=f"Failed to prepare worker workspace root: {error}",
            step="configuring_worker_storage",
            details={"workspace_root": str(root)},
        ) from error

    if not root.is_dir():
        raise StorageError(
            technical_message="Worker workspace root is not a directory.",
            step="configuring_worker_storage",
            details={"workspace_root": str(root)},
        )

    return root


def _storage_backend(storage: StorageBase) -> str:
    value = getattr(storage, "backend", None)

    if not isinstance(value, str) or not value.strip():
        raise StorageError(
            technical_message="Storage backend identifier is required.",
            step="configuring_worker_storage",
            details={"storage_type": type(storage).__name__},
        )

    return value.strip().lower()


def _materialized_filename(key: str) -> str:
    filename = PurePosixPath(key.replace("\\", "/")).name
    suffix = PurePosixPath(filename).suffix

    if not suffix or len(suffix) > MAX_SUFFIX_LENGTH:
        return DEFAULT_INPUT_FILENAME

    return f"{DEFAULT_INPUT_FILENAME}{suffix.lower()}"


def _job_id(job: Any) -> int:
    value = _job_value(job, "id")

    if isinstance(value, bool) or not isinstance(value, int):
        raise StorageError(
            technical_message="Worker job id must be a positive integer.",
            step="materializing_input",
            details={"job_id": value},
        )

    if value <= 0:
        raise StorageError(
            technical_message="Worker job id must be a positive integer.",
            step="materializing_input",
            details={"job_id": value},
        )

    return value


def _required_job_text(job: Any, field: str) -> str:
    value = _job_value(job, field)

    if not isinstance(value, str) or not value.strip():
        raise StorageError(
            technical_message=f"Worker job field is required: {field}",
            step="materializing_input",
            details={"field": field, "job_id": _safe_job_id(job)},
        )

    return value.strip()


def _job_value(job: Any, field: str) -> Any:
    if isinstance(job, Mapping):
        return job.get(field)

    return getattr(job, field, None)


def _safe_job_id(job: Any) -> int | None:
    try:
        return _job_id(job)
    except StorageError:
        return None


__all__ = [
    "LOCAL_STORAGE_BACKEND",
    "StorageFileMaterializer",
]
