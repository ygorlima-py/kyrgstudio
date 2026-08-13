"""Unit tests for the CLI HTTP boundary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import requests

from cli.api_client import KyrgApiClient
from cli.config import CliConfig, CliSession, SessionStore
from cli.errors import (
    CliApiError,
    CliAuthenticationError,
    CliConflictError,
    CliNetworkError,
    CliNotFoundError,
)


class FakeResponse:
    """Small response double exposing only what the client consumes."""

    def __init__(
        self,
        status_code: int,
        payload: object,
        *,
        cookies: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.payload = payload
        self.cookies = requests.cookies.RequestsCookieJar()

        for name, value in (cookies or {}).items():
            self.cookies.set(name, value)

    def json(self) -> object:
        if isinstance(self.payload, BaseException):
            raise json.JSONDecodeError("Invalid fake JSON.", "", 0) from self.payload
        return self.payload


class FakeTransport:
    """Injectable transport that records requests and returns queued results."""

    def __init__(
        self,
        responses: list[FakeResponse] | None = None,
        *,
        exception: requests.RequestException | None = None,
    ) -> None:
        self.responses = list(responses or [])
        self.exception = exception
        self.requests: list[dict[str, Any]] = []

    def request(self, **kwargs: Any) -> FakeResponse:
        self.requests.append(kwargs)

        if self.exception is not None:
            raise self.exception

        return self.responses.pop(0)


def _client(
    tmp_path: Path,
    transport: FakeTransport,
    *,
    authenticated: bool = True,
) -> KyrgApiClient:
    session_path = tmp_path / "session.json"
    store = SessionStore(session_path)

    if authenticated:
        store.save(CliSession("access-token", "refresh-token", "csrf-token"))

    config = CliConfig(
        api_base_url="https://api.example.test/v1",
        session_file=session_path,
        timeout_seconds=12.5,
    )
    return KyrgApiClient(config, session_store=store, transport=transport)


def test_successful_status_uses_injected_transport_and_public_fields(
    tmp_path: Path,
) -> None:
    transport = FakeTransport(
        [
            FakeResponse(
                200,
                {
                    "job_id": 42,
                    "status": "running",
                    "pipeline_type": "copy_analysis",
                    "current_step": "transcribing",
                    "created_at": "2030-01-01T00:00:00Z",
                    "private_input_path": "/storage/private.mp4",
                    "secret_output": {"token": "never-return"},
                },
            )
        ]
    )
    client = _client(tmp_path, transport)

    result = client.get_job_status(42)

    assert result == {
        "job_id": 42,
        "status": "running",
        "pipeline_type": "copy_analysis",
        "current_step": "transcribing",
        "created_at": "2030-01-01T00:00:00Z",
    }
    assert transport.requests[0]["method"] == "GET"
    assert transport.requests[0]["url"] == "https://api.example.test/v1/jobs/42"
    assert transport.requests[0]["timeout"] == 12.5
    assert transport.requests[0]["headers"] == {"Authorization": "Bearer access-token"}


def test_successful_result_keeps_only_public_result_envelope(tmp_path: Path) -> None:
    transport = FakeTransport(
        [
            FakeResponse(
                200,
                {
                    "job_id": 42,
                    "run_id": "run-42",
                    "pipeline_type": "copy_analysis",
                    "status": "completed",
                    "output": {"copy_analysis": {"hook": "public"}},
                    "input_json": {"internal": True},
                },
            )
        ]
    )
    client = _client(tmp_path, transport)

    result = client.get_job_result(42)

    assert result == {
        "job_id": 42,
        "run_id": "run-42",
        "pipeline_type": "copy_analysis",
        "status": "completed",
        "output": {"copy_analysis": {"hook": "public"}},
    }


def test_submit_job_sends_real_multipart_contract(tmp_path: Path) -> None:
    file_path = tmp_path / "reference.mp4"
    file_path.write_bytes(b"media")
    transport = FakeTransport(
        [
            FakeResponse(
                202,
                {
                    "job_id": 7,
                    "run_id": None,
                    "status": "uploaded",
                    "current_step": "uploaded",
                    "pipeline_type": "copy_analysis",
                    "storage_path": "/private/path",
                },
            )
        ]
    )
    client = _client(tmp_path, transport)

    result = client.submit_job(
        file_path=file_path,
        request_metadata={
            "pipeline_type": "copy_analysis",
            "source_type": "video",
            "need_correction": False,
        },
        idempotency_key="run-unique-7",
    )

    request = transport.requests[0]
    assert result == {
        "job_id": 7,
        "run_id": None,
        "status": "uploaded",
        "current_step": "uploaded",
        "pipeline_type": "copy_analysis",
    }
    assert request["url"] == "https://api.example.test/v1/jobs"
    assert request["headers"] == {
        "Authorization": "Bearer access-token",
        "Idempotency-Key": "run-unique-7",
    }
    assert json.loads(request["data"]["request"]) == {
        "pipeline_type": "copy_analysis",
        "source_type": "video",
        "need_correction": False,
    }
    assert request["files"]["file"][0] == "reference.mp4"


def test_refresh_sends_cookie_csrf_origin_and_timeout(tmp_path: Path) -> None:
    transport = FakeTransport(
        [
            FakeResponse(
                200,
                {"access_token": "new-access-token"},
            )
        ]
    )
    client = _client(tmp_path, transport)

    client.refresh_session()

    request = transport.requests[0]
    assert request["method"] == "POST"
    assert request["url"] == "https://api.example.test/v1/auth/refresh"
    assert request["timeout"] == 12.5
    assert request["headers"] == {
        "Cookie": ("kyrg_refresh_token=refresh-token; kyrg_csrf_token=csrf-token"),
        "X-CSRF-Token": "csrf-token",
        "Origin": "https://api.example.test",
        "Referer": "https://api.example.test/",
    }


def test_timeout_becomes_cli_network_error_without_exposing_credentials(
    tmp_path: Path,
) -> None:
    transport = FakeTransport(exception=requests.Timeout("access-token-secret"))
    client = _client(tmp_path, transport)

    with pytest.raises(CliNetworkError) as error_info:
        client.get_job_status(42)

    assert "access-token-secret" not in str(error_info.value)


def test_invalid_success_json_becomes_cli_api_error(tmp_path: Path) -> None:
    transport = FakeTransport([FakeResponse(200, ValueError("invalid json"))])
    client = _client(tmp_path, transport)

    with pytest.raises(CliApiError) as error_info:
        client.get_job_status(42)

    assert error_info.value.code == "invalid_api_response"
    assert error_info.value.status_code == 200


@pytest.mark.parametrize("status_code", [401, 403])
def test_authentication_statuses_become_cli_authentication_errors(
    status_code: int,
    tmp_path: Path,
) -> None:
    transport = FakeTransport(
        [
            FakeResponse(
                status_code,
                {
                    "code": "invalid_credentials",
                    "details": {"password": "never expose"},
                },
            )
        ]
    )
    client = _client(tmp_path, transport, authenticated=False)

    with pytest.raises(CliAuthenticationError) as error_info:
        client.login(email="user@example.com", password="password-secret")

    assert error_info.value.status_code == status_code
    assert "password-secret" not in str(error_info.value)
    assert "never expose" not in str(error_info.value)


@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (404, CliNotFoundError),
        (409, CliConflictError),
        (422, CliApiError),
        (500, CliApiError),
        (503, CliApiError),
    ],
)
def test_public_api_errors_are_classified(
    status_code: int,
    expected_error: type[Exception],
    tmp_path: Path,
) -> None:
    transport = FakeTransport(
        [
            FakeResponse(
                status_code,
                {
                    "code": "public_error",
                    "step": "internal_step_should_not_be_printed",
                    "details": {
                        "field": "file",
                        "message": "public detail",
                        "secret_token": "never expose",
                    },
                },
            )
        ]
    )
    client = _client(tmp_path, transport)

    with pytest.raises(expected_error) as error_info:
        client.get_job_status(42)

    error = error_info.value
    assert "secret_token" not in str(error)
    assert "never expose" not in str(error)
    if isinstance(error, CliApiError):
        assert error.status_code == status_code
        assert error.details == {
            "field": "file",
            "message": "public detail",
        }


def test_nested_error_details_are_filtered_by_public_allowlist(
    tmp_path: Path,
) -> None:
    transport = FakeTransport(
        [
            FakeResponse(
                422,
                {
                    "code": "invalid_input",
                    "details": {
                        "errors": [
                            {
                                "path": "request.email",
                                "message": "invalid email",
                                "password": "do-not-keep",
                            }
                        ],
                        "private_context": "do-not-keep",
                    },
                },
            )
        ]
    )
    client = _client(tmp_path, transport)

    with pytest.raises(CliApiError) as error_info:
        client.get_job_status(42)

    assert error_info.value.details == {
        "errors": [
            {
                "path": "request.email",
                "message": "invalid email",
            }
        ]
    }
