"""Unit tests for the CLI status and result commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, ClassVar

import pytest
import requests

from cli.api_client import KyrgApiClient
from cli.config import CliConfig, CliSession, SessionStore
from cli.errors import (
    CliApiError,
    CliConflictError,
    CliNotFoundError,
    CliUsageError,
)
from cli.main import main


class FakeResponse:
    """Minimal response double for public job endpoints."""

    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload
        self.cookies = requests.cookies.RequestsCookieJar()

    def json(self) -> object:
        if isinstance(self._payload, BaseException):
            raise json.JSONDecodeError("Invalid fake JSON.", "", 0) from self._payload
        return self._payload


class FakeTransport:
    """Transport double that records URL and authentication usage."""

    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.requests: list[dict[str, Any]] = []

    def request(self, **kwargs: Any) -> FakeResponse:
        self.requests.append(kwargs)
        return self.response


def _client(
    tmp_path: Path, response: FakeResponse
) -> tuple[KyrgApiClient, FakeTransport]:
    session_path = tmp_path / "session.json"
    session_store = SessionStore(session_path)
    session_store.save(CliSession("access", "refresh", "csrf"))
    transport = FakeTransport(response)
    client = KyrgApiClient(
        CliConfig(
            api_base_url="https://api.example.test/v1",
            session_file=session_path,
            timeout_seconds=10,
        ),
        session_store=session_store,
        transport=transport,
    )
    return client, transport


def _status_payload(status: str) -> dict[str, Any]:
    return {
        "job_id": 42,
        "run_id": "run-42",
        "pipeline_type": "copy_analysis",
        "status": status,
        "current_step": "running_pipeline" if status == "running" else status,
        "created_at": "2030-01-01T00:00:00Z",
        "input_path": "/private/input.mp4",
        "storage_path": "/private/storage",
    }


@pytest.mark.parametrize("status", ["uploaded", "running", "completed", "failed"])
def test_status_reads_each_public_state_without_private_fields(
    tmp_path: Path,
    status: str,
) -> None:
    client, transport = _client(tmp_path, FakeResponse(200, _status_payload(status)))

    result = client.get_job_status(42)

    assert result["status"] == status
    assert "input_path" not in result
    assert "storage_path" not in result
    assert transport.requests[0]["method"] == "GET"
    assert transport.requests[0]["url"] == "https://api.example.test/v1/jobs/42"
    assert transport.requests[0]["headers"] == {"Authorization": "Bearer access"}


def test_failed_status_hides_public_error_details_but_keeps_error_code(
    tmp_path: Path,
) -> None:
    payload = _status_payload("failed")
    payload["error"] = {
        "code": "pipeline_execution_failed",
        "step": "internal_worker_step",
        "details": {"traceback": "private traceback"},
    }
    client, _transport = _client(tmp_path, FakeResponse(200, payload))

    result = client.get_job_status(42)

    assert result["error"] == {"code": "pipeline_execution_failed"}
    assert "private traceback" not in json.dumps(result)
    assert "internal_worker_step" not in json.dumps(result)


@pytest.mark.parametrize("method_name", ["get_job_status", "get_job_result"])
def test_job_commands_reject_invalid_job_id_before_http_call(
    tmp_path: Path,
    method_name: str,
) -> None:
    client, transport = _client(tmp_path, FakeResponse(200, _status_payload("running")))
    operation = getattr(client, method_name)

    with pytest.raises(CliUsageError, match="positive integer"):
        operation(0)

    with pytest.raises(CliUsageError, match="positive integer"):
        operation(-4)

    assert transport.requests == []


def test_result_uses_real_endpoint_and_filters_internal_result_fields(
    tmp_path: Path,
) -> None:
    response_payload = {
        "job_id": 42,
        "run_id": "run-42",
        "pipeline_type": "copy_adaptation",
        "status": "completed",
        "output": {
            "copy_analysis": {"hook": "public"},
            "transcription": {
                "language": "pt-BR",
                "text": "Public transcription",
                "audio_path": "/tmp/private.wav",
                "segments": [{"secret": True}],
            },
            "adapted_script": {
                "script": "Public script",
                "sections": [],
                "raw_response": "private provider response",
                "audio_path": "/tmp/private.wav",
            },
            "input_json": {"private": True},
            "storage_path": "/private/storage",
        },
    }
    client, transport = _client(tmp_path, FakeResponse(200, response_payload))

    result = client.get_job_result(42)

    assert transport.requests[0]["method"] == "GET"
    assert transport.requests[0]["url"] == "https://api.example.test/v1/jobs/42/result"
    assert result == {
        "job_id": 42,
        "run_id": "run-42",
        "pipeline_type": "copy_adaptation",
        "status": "completed",
        "output": {
            "copy_analysis": {"hook": "public"},
            "transcription": {
                "language": "pt-BR",
                "text": "Public transcription",
            },
            "adapted_script": {
                "script": "Public script",
                "sections": [],
            },
        },
    }
    assert "private" not in json.dumps(result)


def test_result_rejects_non_completed_success_payload(tmp_path: Path) -> None:
    client, _transport = _client(
        tmp_path,
        FakeResponse(
            200,
            {
                "job_id": 42,
                "pipeline_type": "copy_analysis",
                "status": "running",
                "output": {"copy_analysis": {}},
            },
        ),
    )

    with pytest.raises(CliApiError) as error_info:
        client.get_job_result(42)

    assert error_info.value.code == "invalid_api_response"
    assert error_info.value.status_code == 502


@pytest.mark.parametrize("command", ["status", "result"])
def test_other_users_job_is_reported_as_not_found(
    tmp_path: Path,
    command: str,
) -> None:
    client, _transport = _client(
        tmp_path,
        FakeResponse(
            404,
            {
                "code": "job_not_found",
                "details": {"job_id": 42, "user_id": 999},
            },
        ),
    )

    operation = client.get_job_status if command == "status" else client.get_job_result
    with pytest.raises(CliNotFoundError) as error_info:
        operation(42)

    assert error_info.value.exit_code == 4
    assert error_info.value.code == "job_not_found"
    assert "999" not in str(error_info.value)


def test_result_pending_has_distinct_conflict_exit_code(tmp_path: Path) -> None:
    client, _transport = _client(
        tmp_path,
        FakeResponse(
            409,
            {
                "code": "job_result_not_ready",
                "details": {"job_id": 42, "status": "running"},
            },
        ),
    )

    with pytest.raises(CliConflictError) as error_info:
        client.get_job_result(42)

    assert error_info.value.exit_code == 5
    assert error_info.value.code == "job_result_not_ready"
    assert str(error_info.value) == "This job does not have a completed result yet."


class FakeCommandClient:
    """Command-level client double for output and process exit tests."""

    response: ClassVar[dict[str, Any]] = {}

    def __init__(self, _config: object) -> None:
        pass

    def get_job_status(self, _job_id: int) -> dict[str, Any]:
        return self.response

    def get_job_result(self, _job_id: int) -> dict[str, Any]:
        return self.response


class ErrorCommandClient:
    """Command double that raises one public CLI error."""

    error: Exception

    def __init__(self, _config: object) -> None:
        pass

    def get_job_status(self, _job_id: int) -> dict[str, Any]:
        raise self.error

    def get_job_result(self, _job_id: int) -> dict[str, Any]:
        raise self.error


@pytest.mark.parametrize(
    ("status", "label", "exit_code"),
    [
        ("uploaded", "Uploaded", 0),
        ("running", "Running", 0),
        ("completed", "Completed", 0),
        ("failed", "Failed", 8),
    ],
)
def test_status_command_displays_clear_state_and_exit_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    status: str,
    label: str,
    exit_code: int,
) -> None:
    FakeCommandClient.response = _status_payload(status)
    monkeypatch.setattr("cli.main.KyrgApiClient", FakeCommandClient)

    result = main(
        [
            "--api-url",
            "http://api.example.test",
            "--session-file",
            str(tmp_path / "session.json"),
            "status",
            "42",
        ]
    )

    captured = capsys.readouterr()
    assert result == exit_code
    assert f"Status: {label}" in captured.out
    assert "input_path" not in captured.out
    assert captured.err == ""


def test_result_command_displays_public_sections_without_raw_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    FakeCommandClient.response = {
        "job_id": 42,
        "pipeline_type": "copy_analysis",
        "status": "completed",
        "output": {
            "copy_analysis": {"hook": "A clear hook"},
            "transcription": {"language": "pt-BR", "text": "Text"},
        },
    }
    monkeypatch.setattr("cli.main.KyrgApiClient", FakeCommandClient)

    result = main(
        [
            "--api-url",
            "http://api.example.test",
            "--session-file",
            str(tmp_path / "session.json"),
            "result",
            "42",
        ]
    )

    captured = capsys.readouterr()
    assert result == 0
    assert "Status: Completed" in captured.out
    assert "Result:" in captured.out
    assert "Copy analysis:" in captured.out
    assert "A clear hook" in captured.out
    assert '"copy_analysis"' not in captured.out


@pytest.mark.parametrize(
    ("command", "error", "exit_code"),
    [
        ("status", CliNotFoundError("Job was not found."), 4),
        ("result", CliNotFoundError("Job was not found."), 4),
        (
            "result",
            CliConflictError("This job does not have a completed result yet."),
            5,
        ),
    ],
)
def test_command_errors_return_documented_exit_codes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
    error: Exception,
    exit_code: int,
) -> None:
    ErrorCommandClient.error = error
    monkeypatch.setattr("cli.main.KyrgApiClient", ErrorCommandClient)

    result = main(
        [
            "--api-url",
            "http://api.example.test",
            "--session-file",
            str(tmp_path / "session.json"),
            command,
            "42",
        ]
    )

    captured = capsys.readouterr()
    assert result == exit_code
    assert captured.out == ""
    assert "Job was not found" in captured.err or "completed result" in captured.err
