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


class AuthenticationRequiredError(AppError):
    """Raised when a protected operation has no authenticated principal."""

    code = "authentication_required"
    default_step = "authenticating_request"


class InvalidCredentialsError(AppError):
    """Raised when supplied login credentials cannot be accepted."""

    code = "invalid_credentials"
    default_step = "authenticating_user"


class InvalidTokenError(AppError):
    """Raised when an access token cannot be safely accepted."""

    code = "invalid_token"
    default_step = "validating_access_token"


class RefreshTokenInvalidError(AppError):
    """Raised when a refresh token is invalid, expired, or revoked."""

    code = "refresh_token_invalid"
    default_step = "validating_refresh_token"


class AccountDisabledError(AppError):
    """Raised when authentication is attempted for a disabled account."""

    code = "account_disabled"
    default_step = "authorizing_user"


class EmailVerificationRequiredError(AppError):
    """Raised when an operation requires a verified email address."""

    code = "email_verification_required"
    default_step = "authorizing_user"


class CsrfValidationError(AppError):
    """Raised when a cookie-authenticated mutation fails CSRF validation."""

    code = "csrf_validation_failed"
    default_step = "validating_csrf"


class AccountLinkRequiredError(AppError):
    """Raised when an identity must be explicitly linked to an account."""

    code = "account_link_required"
    default_step = "linking_account"


class AuthConfigurationError(AppError):
    """Raised when authentication cannot start from server configuration."""

    code = "auth_configuration_error"
    default_step = "configuring_auth"


class FileNotFoundAppError(AppError):
    code = "file_not_found"
    default_step = "validating_input"


class UnsupportedMediaTypeError(AppError):
    code = "unsupported_media_type"
    default_step = "validating_input"


class MediaTooLongError(AppError):
    code = "media_too_long"
    default_step = "validating_input"


class UploadTooLargeError(AppError):
    code = "upload_too_large"
    default_step = "validating_upload"


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


class IdempotencyConflictError(JobStoreError):
    """Raised when one idempotency key is reused for another request."""

    code = "idempotency_conflict"
    default_step = "validating_idempotency"


class JobNotFoundError(AppError):
    code = "job_not_found"
    default_step = "loading_job"


class JobResultNotReadyError(AppError):
    code = "job_result_not_ready"
    default_step = "loading_job_result"


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
    "AccountDisabledError",
    "AccountLinkRequiredError",
    "AppError",
    "AuthConfigurationError",
    "AuthenticationRequiredError",
    "BillingStoreError",
    "CsrfValidationError",
    "EmailVerificationRequiredError",
    "ExportError",
    "FileNotFoundAppError",
    "IdempotencyConflictError",
    "InvalidCredentialsError",
    "InvalidInputError",
    "InvalidTokenError",
    "JobNotFoundError",
    "JobResultNotReadyError",
    "JobStoreError",
    "LLMExecutionError",
    "MediaProcessingError",
    "MediaTooLongError",
    "PipelineExecutionError",
    "ProviderConfigError",
    "RefreshTokenInvalidError",
    "StorageError",
    "StoreError",
    "StructuredOutputError",
    "TimeoutAppError",
    "TranscriptionError",
    "UnsupportedMediaTypeError",
    "UploadTooLargeError",
    "UserStoreError",
    "WorkflowResultError",
]
