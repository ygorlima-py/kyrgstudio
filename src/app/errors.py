"""Controlled application errors.

The backend returns stable error codes and safe metadata. The frontend is
responsible for translating each code into the final user-facing message.
"""

from __future__ import annotations

from typing import Any, ClassVar


class AppError(Exception):
    """Base error for controlled application failures."""

    code: ClassVar[str] = "app_error"
    default_step: ClassVar[str | None] = None

    def __init__(
        self,
        *,
        technical_message: str,
        step: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.technical_message = technical_message
        self.step = step or self.default_step
        self.details = details or {}

        super().__init__(technical_message)

    def to_dict(self) -> dict[str, Any]:
        """Return the API-safe error payload.

        No translated user message is returned here. Clients should translate
        `code` according to their own locale and presentation context.
        """

        return {
            "code": self.code,
            "step": self.step,
            "details": self.details,
        }


class InvalidInputError(AppError):
    code = "invalid_input"
    default_step = "validating_input"


class FileNotFoundAppError(AppError):
    code = "file_not_found"
    default_step = "validating_input"


class UnsupportedMediaTypeError(AppError):
    code = "unsupported_media_type"
    default_step = "validating_input"


class MediaTooLongError(AppError):
    code = "media_too_long"
    default_step = "validating_input"


class MediaProcessingError(AppError):
    code = "media_processing_failed"
    default_step = "processing_media"


class ProviderConfigError(AppError):
    code = "provider_config_error"
    default_step = "configuring_providers"


class TranscriptionError(AppError):
    code = "transcription_failed"
    default_step = "transcribing"


class LLMExecutionError(AppError):
    code = "llm_execution_failed"
    default_step = "calling_llm"


class StructuredOutputError(AppError):
    code = "structured_output_failed"
    default_step = "parsing_llm_output"


class PipelineExecutionError(AppError):
    code = "pipeline_execution_failed"
    default_step = "running_pipeline"


class WorkflowResultError(AppError):
    code = "workflow_result_error"
    default_step = "validating_workflow_result"


class StorageError(AppError):
    code = "storage_error"
    default_step = "storage"


class StoreError(AppError):
    code = "store_error"
    default_step = "store"


class JobStoreError(StoreError):
    code = "job_store_error"
    default_step = "job_store"


class UserStoreError(StoreError):
    code = "user_store_error"
    default_step = "user_store"


class BillingStoreError(StoreError):
    code = "billing_store_error"
    default_step = "billing_store"


class ExportError(AppError):
    code = "export_error"
    default_step = "exporting"


class TimeoutAppError(AppError):
    code = "timeout"
    default_step = "timeout"


__all__ = [
    "AppError",
    "BillingStoreError",
    "ExportError",
    "FileNotFoundAppError",
    "InvalidInputError",
    "JobStoreError",
    "LLMExecutionError",
    "MediaProcessingError",
    "MediaTooLongError",
    "PipelineExecutionError",
    "ProviderConfigError",
    "StorageError",
    "StoreError",
    "StructuredOutputError",
    "TimeoutAppError",
    "TranscriptionError",
    "UnsupportedMediaTypeError",
    "UserStoreError",
    "WorkflowResultError",
]
