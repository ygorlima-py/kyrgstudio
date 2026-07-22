"""Exception-to-HTTP translation for the FastAPI application."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette import status

from app.errors import (
    AccountDisabledError,
    AccountLinkRequiredError,
    AppError,
    AuthConfigurationError,
    AuthenticationRequiredError,
    CsrfValidationError,
    EmailVerificationRequiredError,
    InvalidCredentialsError,
    InvalidInputError,
    InvalidTokenError,
    JobNotFoundError,
    JobResultNotReadyError,
    PipelineExecutionError,
    RefreshTokenInvalidError,
    StorageError,
    StoreError,
    TimeoutAppError,
    UnsupportedMediaTypeError,
    UploadTooLargeError,
)


_UNAUTHORIZED_ERRORS = (
    AuthenticationRequiredError,
    InvalidCredentialsError,
    InvalidTokenError,
    RefreshTokenInvalidError,
)

_FORBIDDEN_ERRORS = (
    AccountDisabledError,
    CsrfValidationError,
    EmailVerificationRequiredError,
)

_AUTH_ERRORS = (
    *_UNAUTHORIZED_ERRORS,
    *_FORBIDDEN_ERRORS,
    AccountLinkRequiredError,
    AuthConfigurationError,
)

_PUBLIC_DETAIL_KEYS = frozenset(
    {
        "accepted_media_types",
        "allowed",
        "backend",
        "code",
        "driver",
        "error_type",
        "errors",
        "field",
        "input_type",
        "job_id",
        "max_upload_bytes",
        "message",
        "minimum",
        "operation",
        "path",
        "pipeline_type",
        "size_bytes",
        "status",
        "supported_values",
        "type",
    }
)

_INTERNAL_ERROR_PAYLOAD = {
    "code": "internal_error",
    "step": "handling_request",
    "details": {},
}


def install_exception_handlers(app: FastAPI) -> None:
    """Install the application's stable HTTP exception contract."""

    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(
        RequestValidationError,
        _handle_request_validation_error,
    )
    app.add_exception_handler(Exception, _handle_unexpected_error)


async def _handle_app_error(
    request: Request,
    error: Exception,
) -> JSONResponse:
    app_error = _require_error_type(error, AppError)
    payload = app_error.to_dict()
    payload["details"] = _public_error_details(app_error, payload)
    status_code = _status_for_app_error(app_error)

    _log_controlled_error(
        request=request,
        error=app_error,
        status_code=status_code,
    )

    return JSONResponse(
        status_code=status_code,
        content=payload,
        headers=_response_headers(status_code),
    )


async def _handle_request_validation_error(
    request: Request,
    error: Exception,
) -> JSONResponse:
    validation_error = _require_error_type(error, RequestValidationError)
    public_error = InvalidInputError(
        technical_message="HTTP request validation failed.",
        step="validating_request",
        details={
            "errors": [
                {
                    "path": ".".join(map(str, item["loc"])),
                    "type": item["type"],
                    "message": item["msg"],
                }
                for item in validation_error.errors()
            ]
        },
    )
    payload = public_error.to_dict()
    payload["details"] = _sanitize_details(payload.get("details"))

    _log_controlled_error(
        request=request,
        error=public_error,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=payload,
    )


async def _handle_unexpected_error(
    request: Request,
    error: Exception,
) -> JSONResponse:
    context = _request_context(request)

    logger.opt(exception=error).error(
        "Unhandled API exception request_id={} method={} path={}",
        context["request_id"],
        context["method"],
        context["path"],
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_INTERNAL_ERROR_PAYLOAD,
    )


def _status_for_app_error(error: AppError) -> int:
    if isinstance(error, _UNAUTHORIZED_ERRORS):
        return status.HTTP_401_UNAUTHORIZED

    if isinstance(error, _FORBIDDEN_ERRORS):
        return status.HTTP_403_FORBIDDEN

    if isinstance(error, AccountLinkRequiredError):
        return status.HTTP_409_CONFLICT

    if isinstance(error, AuthConfigurationError):
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    if isinstance(error, UploadTooLargeError):
        return status.HTTP_413_CONTENT_TOO_LARGE

    if isinstance(error, UnsupportedMediaTypeError):
        return status.HTTP_415_UNSUPPORTED_MEDIA_TYPE

    if isinstance(error, InvalidInputError):
        return status.HTTP_422_UNPROCESSABLE_CONTENT

    if isinstance(error, JobNotFoundError):
        return status.HTTP_404_NOT_FOUND

    if isinstance(error, JobResultNotReadyError):
        return status.HTTP_409_CONFLICT

    if isinstance(error, TimeoutAppError):
        return status.HTTP_503_SERVICE_UNAVAILABLE

    if _is_retryable_infrastructure_error(error):
        return status.HTTP_503_SERVICE_UNAVAILABLE

    return status.HTTP_500_INTERNAL_SERVER_ERROR


def _public_error_details(
    error: AppError,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(error, _AUTH_ERRORS):
        return {}

    return _sanitize_details(payload.get("details"))


def _response_headers(status_code: int) -> dict[str, str] | None:
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return {"WWW-Authenticate": "Bearer"}

    return None


def _is_retryable_infrastructure_error(error: AppError) -> bool:
    if isinstance(error, PipelineExecutionError):
        if error.step == "enqueue_job":
            return True

    if not isinstance(
        error,
        (PipelineExecutionError, StorageError, StoreError),
    ):
        return False

    return error.details.get("retryable") is True


def _sanitize_details(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}

    sanitized: dict[str, Any] = {}

    for raw_key, raw_value in value.items():
        key = str(raw_key)

        if key not in _PUBLIC_DETAIL_KEYS:
            continue

        sanitized[key] = _sanitize_value(raw_value)

    return sanitized


def _sanitize_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, Mapping):
        return _sanitize_details(value)

    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return [_sanitize_value(item) for item in value]

    return None


def _log_controlled_error(
    *,
    request: Request,
    error: AppError,
    status_code: int,
) -> None:
    context = _request_context(request)

    logger.warning(
        (
            "Controlled API error request_id={} method={} path={} "
            "status_code={} code={} step={}"
        ),
        context["request_id"],
        context["method"],
        context["path"],
        status_code,
        error.code,
        error.step,
    )


def _request_context(request: Request) -> dict[str, str]:
    request_id = str(
        getattr(request.state, "request_id", "unavailable")
    ).strip()

    return {
        "request_id": request_id or "unavailable",
        "method": request.method,
        "path": request.url.path,
    }


def _require_error_type[ErrorT: Exception](
    error: Exception,
    expected_type: type[ErrorT],
) -> ErrorT:
    if not isinstance(error, expected_type):
        raise TypeError(
            f"Expected {expected_type.__name__}, "
            f"received {type(error).__name__}."
        )

    return error


__all__ = ["install_exception_handlers"]
