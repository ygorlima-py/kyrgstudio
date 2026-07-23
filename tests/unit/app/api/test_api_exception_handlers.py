"""Unit tests for the API's stable exception-to-HTTP contract."""

import asyncio
import json
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any, TypeVar, cast

import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import Response

from app.api.exception_handlers import install_exception_handlers
from app.errors import (
    AccountDisabledError,
    AccountLinkRequiredError,
    AppError,
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
    UnsupportedMediaTypeError,
    UploadTooLargeError,
)


ResultT = TypeVar("ResultT")
ExceptionHandler = Callable[[Request, Exception], Awaitable[Response]]


def _run(coroutine: Coroutine[Any, Any, ResultT]) -> ResultT:
    return asyncio.run(coroutine)


def _application() -> FastAPI:
    application = FastAPI()
    install_exception_handlers(application)
    return application


def _request() -> Request:
    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": "/v1/jobs",
        "raw_path": b"/v1/jobs",
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 50000),
        "server": ("api.example.com", 443),
        "app": _application(),
    }
    request = Request(scope)
    request.state.request_id = "request-123"
    return request


def _registered_handler(error_type: type[Exception]) -> ExceptionHandler:
    handler = _application().exception_handlers[error_type]
    return cast(ExceptionHandler, handler)


def _handle_controlled_error(error: AppError) -> Response:
    handler = _registered_handler(AppError)
    return _run(handler(_request(), error))


def _response_payload(response: Response) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(response.body))


def test_install_exception_handlers_registers_expected_handlers() -> None:
    """Register controlled, validation, and unexpected exception boundaries."""

    application = FastAPI()

    install_exception_handlers(application)

    assert AppError in application.exception_handlers
    assert RequestValidationError in application.exception_handlers
    assert Exception in application.exception_handlers


@pytest.mark.parametrize(
    "error",
    [
        AuthenticationRequiredError(technical_message="missing bearer"),
        InvalidCredentialsError(technical_message="invalid password"),
        InvalidTokenError(technical_message="invalid access token"),
        RefreshTokenInvalidError(technical_message="invalid refresh token"),
    ],
)
def test_authentication_errors_return_401_with_bearer_header(
    error: AppError,
) -> None:
    """Map every unauthenticated state to the standard Bearer challenge."""

    response = _handle_controlled_error(error)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert _response_payload(response)["code"] == error.code


@pytest.mark.parametrize(
    "error",
    [
        AccountDisabledError(technical_message="account disabled"),
        CsrfValidationError(technical_message="csrf mismatch"),
        EmailVerificationRequiredError(
            technical_message="email verification required"
        ),
    ],
)
def test_forbidden_auth_errors_return_403(error: AppError) -> None:
    """Map authenticated but forbidden operations to HTTP 403."""

    response = _handle_controlled_error(error)

    assert response.status_code == 403
    assert "www-authenticate" not in response.headers
    assert _response_payload(response)["code"] == error.code


def test_account_link_required_returns_409() -> None:
    """Represent an explicit account-linking conflict with HTTP 409."""

    response = _handle_controlled_error(
        AccountLinkRequiredError(
            technical_message="explicit linking required",
        )
    )

    assert response.status_code == 409
    assert _response_payload(response)["code"] == "account_link_required"


def test_upload_too_large_returns_413() -> None:
    """Map the controlled upload limit error to HTTP 413."""

    response = _handle_controlled_error(
        UploadTooLargeError(
            technical_message="upload exceeds limit",
            details={
                "size_bytes": 20,
                "max_upload_bytes": 10,
            },
        )
    )

    assert response.status_code == 413
    assert _response_payload(response) == {
        "code": "upload_too_large",
        "step": "validating_upload",
        "details": {
            "size_bytes": 20,
            "max_upload_bytes": 10,
        },
    }


def test_unsupported_media_type_returns_415() -> None:
    """Map an unsupported upload media type to HTTP 415."""

    response = _handle_controlled_error(
        UnsupportedMediaTypeError(
            technical_message="unsupported media type",
            details={
                "accepted_media_types": ["video/mp4"],
                "content_type": "text/plain",
            },
        )
    )

    assert response.status_code == 415
    assert _response_payload(response) == {
        "code": "unsupported_media_type",
        "step": "validating_input",
        "details": {
            "accepted_media_types": ["video/mp4"],
        },
    }


def test_invalid_input_returns_422() -> None:
    """Map controlled application input failures to HTTP 422."""

    response = _handle_controlled_error(
        InvalidInputError(
            technical_message="invalid source type",
            details={
                "field": "source_type",
                "supported_values": ["video", "audio"],
            },
        )
    )

    assert response.status_code == 422
    assert _response_payload(response)["code"] == "invalid_input"


def test_job_not_found_returns_404() -> None:
    """Hide absent and unauthorized jobs behind the same HTTP 404 response."""

    response = _handle_controlled_error(
        JobNotFoundError(
            technical_message="job was not found",
            details={"job_id": 41},
        )
    )

    assert response.status_code == 404
    assert _response_payload(response)["details"] == {"job_id": 41}


def test_job_result_not_ready_returns_409() -> None:
    """Report a requested non-terminal result as an HTTP conflict."""

    response = _handle_controlled_error(
        JobResultNotReadyError(
            technical_message="job is still running",
            details={
                "job_id": 41,
                "status": "running",
            },
        )
    )

    assert response.status_code == 409
    assert _response_payload(response)["code"] == "job_result_not_ready"


@pytest.mark.parametrize(
    "error",
    [
        StorageError(
            technical_message="temporary storage outage",
            details={"retryable": True},
        ),
        StoreError(
            technical_message="temporary database outage",
            details={"retryable": True},
        ),
        PipelineExecutionError(
            technical_message="broker unavailable",
            step="enqueue_job",
        ),
    ],
)
def test_retryable_infrastructure_error_returns_503(
    error: AppError,
) -> None:
    """Map explicitly retryable infrastructure failures to HTTP 503."""

    response = _handle_controlled_error(error)

    assert response.status_code == 503
    assert _response_payload(response)["code"] == error.code


@pytest.mark.parametrize(
    "error",
    [
        StorageError(technical_message="permanent storage failure"),
        StoreError(technical_message="non-retryable database failure"),
        PipelineExecutionError(
            technical_message="pipeline failed",
            step="running_pipeline",
        ),
    ],
)
def test_non_retryable_infrastructure_error_returns_500(
    error: AppError,
) -> None:
    """Keep non-retryable infrastructure failures as internal errors."""

    response = _handle_controlled_error(error)

    assert response.status_code == 500
    assert _response_payload(response)["code"] == error.code


@pytest.mark.parametrize(
    "error",
    [
        InvalidCredentialsError(
            technical_message="password hash mismatch",
            details={
                "field": "password",
                "api_key": "private-key",
            },
        ),
        CsrfValidationError(
            technical_message="csrf tokens differ",
            details={
                "field": "csrf",
                "message": "private comparison detail",
            },
        ),
        AccountLinkRequiredError(
            technical_message="matching private account found",
            details={
                "field": "email",
                "path": "/private/database/path",
            },
        ),
    ],
)
def test_auth_errors_hide_internal_details(error: AppError) -> None:
    """Remove all details from authentication errors regardless of key."""

    response = _handle_controlled_error(error)
    payload = _response_payload(response)

    assert payload["details"] == {}
    assert error.technical_message not in response.body.decode()
    assert "private" not in response.body.decode()


def test_public_error_details_are_allowlisted() -> None:
    """Expose approved metadata while recursively removing private values."""

    error = InvalidInputError(
        technical_message="request validation failed internally",
        details={
            "field": "source_type",
            "supported_values": ["video", "audio"],
            "api_key": "secret-key",
            "errors": [
                {
                    "path": "body.source_type",
                    "type": "literal_error",
                    "message": "Unsupported value",
                    "input": "private-input",
                }
            ],
        },
    )

    response = _handle_controlled_error(error)

    assert _response_payload(response)["details"] == {
        "field": "source_type",
        "supported_values": ["video", "audio"],
        "errors": [
            {
                "path": "body.source_type",
                "type": "literal_error",
                "message": "Unsupported value",
            }
        ],
    }
    assert "secret-key" not in response.body.decode()
    assert "private-input" not in response.body.decode()


def test_request_validation_error_uses_public_error_shape() -> None:
    """Translate FastAPI validation failures into the shared public schema."""

    validation_error = RequestValidationError(
        [
            {
                "type": "missing",
                "loc": ("body", "email"),
                "msg": "Field required",
                "input": {
                    "email": None,
                    "password": "secret-password",
                },
            }
        ]
    )
    handler = _registered_handler(RequestValidationError)

    response = _run(handler(_request(), validation_error))

    assert response.status_code == 422
    assert _response_payload(response) == {
        "code": "invalid_input",
        "step": "validating_request",
        "details": {
            "errors": [
                {
                    "path": "body.email",
                    "type": "missing",
                    "message": "Field required",
                }
            ]
        },
    }
    assert "secret-password" not in response.body.decode()


def test_unexpected_error_returns_generic_500_without_internal_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prevent unhandled exceptions from exposing stack traces or secrets."""

    class SilentLogger:
        def opt(self, **kwargs: object) -> "SilentLogger":
            del kwargs
            return self

        def error(self, message: str, *args: object) -> None:
            del message, args

    monkeypatch.setattr(
        "app.api.exception_handlers.logger",
        SilentLogger(),
    )
    handler = _registered_handler(Exception)
    internal_error = RuntimeError(
        "database password=secret local_path=/private/app.sqlite"
    )

    response = _run(handler(_request(), internal_error))

    assert response.status_code == 500
    assert _response_payload(response) == {
        "code": "internal_error",
        "step": "handling_request",
        "details": {},
    }
    assert "secret" not in response.body.decode()
    assert "private" not in response.body.decode()
    assert "RuntimeError" not in response.body.decode()
