"""Unit tests for the CLI analyze and adapt submission commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pytest
import requests

from cli.api_client import KyrgApiClient
from cli.config import CliConfig, CliSession, SessionStore
from cli.errors import CliApiError, CliUsageError
from cli.main import (
    MAX_LOCAL_UPLOAD_BYTES,
    _submit_job,
    main,
)


class FakeResponse:
    """Minimal response double used by the injected HTTP transport."""

    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload
        self.cookies = requests.cookies.RequestsCookieJar()

    def json(self) -> object:
        if isinstance(self._payload, BaseException):
            raise json.JSONDecodeError("Invalid fake JSON.", "", 0) from self._payload
        return self._payload


class RecordingTransport:
    """Record requests and return a configured response or raise an error."""

    def __init__(
        self,
        response: FakeResponse | None = None,
        *,
        exception: BaseException | None = None,
    ) -> None:
        self.response = response
        self.exception = exception
        self.requests: list[dict[str, Any]] = []

    def request(self, **kwargs: Any) -> FakeResponse:
        self.requests.append(kwargs)
        if self.exception is not None:
            raise self.exception
        if self.response is None:
            raise AssertionError("A fake response must be configured.")
        return self.response


def _authenticated_client(
    tmp_path: Path,
    transport: RecordingTransport,
) -> KyrgApiClient:
    session_path = tmp_path / "session.json"
    session_store = SessionStore(session_path)
    session_store.save(CliSession("access", "refresh", "csrf"))
    config = CliConfig(
        api_base_url="http://api.example.test/v1",
        session_file=session_path,
        timeout_seconds=15,
    )
    return KyrgApiClient(
        config,
        session_store=session_store,
        transport=transport,
    )


def _command_arguments(
    command: str,
    file_path: Path,
    *,
    profile_path: Path | None = None,
    source_type: str | None = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        command=command,
        file=file_path,
        source_type=source_type,
        language="pt-BR",
        need_correction=True,
        profile=profile_path,
        idempotency_key="submission-test-key",
    )


def _successful_submission(pipeline_type: str) -> FakeResponse:
    return FakeResponse(
        202,
        {
            "job_id": 17,
            "run_id": None,
            "status": "uploaded",
            "current_step": "uploaded",
            "pipeline_type": pipeline_type,
            "storage_path": "/private/storage/input.mp4",
        },
    )


def _valid_user_profile() -> dict[str, Any]:
    return {
        "product_or_solution": "Ciclo Leve ebook",
        "target_audience": "Brazilian women with recurring menstrual cramps",
        "core_problem": "They improvise every month and lose control of their routine",
        "core_desire": "Prepare for the menstrual period with more confidence",
        "main_promise": "Create a personal preparation and self-care routine",
        "call_to_action": "Click the button to get the ebook",
        "desired_duration": 5.5,
        "benefits": ["Plan difficult days in advance"],
        "objections": ["I do not have time"],
        "proof_assets": ["Real reader testimonial"],
        "restrictions": ["Do not promise a cure"],
    }


def test_analyze_sends_expected_multipart_without_user_profile(tmp_path: Path) -> None:
    media_path = tmp_path / "reference.mp4"
    media_path.write_bytes(b"video-bytes")
    transport = RecordingTransport(_successful_submission("copy_analysis"))
    client = _authenticated_client(tmp_path, transport)

    result = _submit_job(
        _command_arguments("analyze", media_path),
        client,
    )

    request = transport.requests[0]
    request_metadata = json.loads(request["data"]["request"])

    assert result == {
        "job_id": 17,
        "run_id": None,
        "status": "uploaded",
        "current_step": "uploaded",
        "pipeline_type": "copy_analysis",
    }
    assert request["method"] == "POST"
    assert request["url"] == "http://api.example.test/v1/jobs"
    assert request["timeout"] == 15
    assert request_metadata == {
        "pipeline_type": "copy_analysis",
        "source_type": "video",
        "need_correction": True,
        "language": "pt-BR",
    }
    assert "user_profile" not in request_metadata
    assert request["files"]["file"][0] == "reference.mp4"
    assert request["files"]["file"][1].closed is True


def test_adapt_validates_profile_and_sends_it_in_multipart_request(
    tmp_path: Path,
) -> None:
    media_path = tmp_path / "reference.mp3"
    media_path.write_bytes(b"audio-bytes")
    profile_path = tmp_path / "profile.json"
    profile = _valid_user_profile()
    profile_path.write_text(json.dumps(profile), encoding="utf-8")
    transport = RecordingTransport(_successful_submission("copy_adaptation"))
    client = _authenticated_client(tmp_path, transport)

    result = _submit_job(
        _command_arguments("adapt", media_path, profile_path=profile_path),
        client,
    )

    request_metadata = json.loads(transport.requests[0]["data"]["request"])

    assert result["job_id"] == 17
    assert request_metadata["pipeline_type"] == "copy_adaptation"
    assert request_metadata["source_type"] == "audio"
    assert request_metadata["user_profile"] == profile
    assert transport.requests[0]["files"]["file"][1].closed is True


def test_adapt_requests_required_profile_fields_when_profile_file_is_omitted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    media_path = tmp_path / "reference.mp4"
    media_path.write_bytes(b"video-bytes")
    answers = iter(
        [
            "Ciclo Leve ebook",
            "Women with recurring cramps",
            "They improvise every month",
            "More preparation and confidence",
            "Build a personal preparation routine",
            "Click the button to get the ebook",
            "5",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    transport = RecordingTransport(_successful_submission("copy_adaptation"))
    client = _authenticated_client(tmp_path, transport)

    _submit_job(
        _command_arguments("adapt", media_path),
        client,
    )

    request_metadata = json.loads(transport.requests[0]["data"]["request"])
    assert request_metadata["user_profile"] == {
        "product_or_solution": "Ciclo Leve ebook",
        "target_audience": "Women with recurring cramps",
        "core_problem": "They improvise every month",
        "core_desire": "More preparation and confidence",
        "main_promise": "Build a personal preparation routine",
        "call_to_action": "Click the button to get the ebook",
        "desired_duration": 5.0,
    }


@pytest.mark.parametrize(
    ("suffix", "content", "message"),
    [
        (".mp4", b"", "empty"),
        (".txt", b"not media", "infer"),
    ],
)
def test_submission_rejects_invalid_local_media(
    tmp_path: Path,
    suffix: str,
    content: bytes,
    message: str,
) -> None:
    media_path = tmp_path / f"reference{suffix}"
    media_path.write_bytes(content)
    transport = RecordingTransport(_successful_submission("copy_analysis"))
    client = _authenticated_client(tmp_path, transport)

    with pytest.raises(CliUsageError) as error_info:
        _submit_job(_command_arguments("analyze", media_path), client)

    assert message in str(error_info.value)
    assert transport.requests == []


def test_submission_rejects_missing_media_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.mp4"
    transport = RecordingTransport(_successful_submission("copy_analysis"))
    client = _authenticated_client(tmp_path, transport)

    with pytest.raises(CliUsageError, match="does not exist"):
        _submit_job(_command_arguments("analyze", missing_path), client)

    assert transport.requests == []


def test_submission_rejects_source_type_that_conflicts_with_extension(
    tmp_path: Path,
) -> None:
    media_path = tmp_path / "reference.mp4"
    media_path.write_bytes(b"video")
    transport = RecordingTransport(_successful_submission("copy_analysis"))
    client = _authenticated_client(tmp_path, transport)

    with pytest.raises(CliUsageError, match="cannot be submitted as audio"):
        _submit_job(
            _command_arguments("analyze", media_path, source_type="audio"),
            client,
        )

    assert transport.requests == []


def test_submission_rejects_file_above_local_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    media_path = tmp_path / "reference.mp4"
    media_path.write_bytes(b"12345")
    monkeypatch.setattr("cli.main.MAX_LOCAL_UPLOAD_BYTES", 4)
    transport = RecordingTransport(_successful_submission("copy_analysis"))
    client = _authenticated_client(tmp_path, transport)

    with pytest.raises(CliUsageError, match="exceeds"):
        _submit_job(_command_arguments("analyze", media_path), client)

    assert MAX_LOCAL_UPLOAD_BYTES > 0
    assert transport.requests == []


def test_submission_rejects_filename_above_local_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    media_path = tmp_path / "reference.mp4"
    media_path.write_bytes(b"video")
    monkeypatch.setattr("cli.main.MAX_UPLOAD_FILENAME_LENGTH", 3)
    transport = RecordingTransport(_successful_submission("copy_analysis"))
    client = _authenticated_client(tmp_path, transport)

    with pytest.raises(CliUsageError, match="filename"):
        _submit_job(_command_arguments("analyze", media_path), client)

    assert transport.requests == []


def test_adapt_rejects_profile_without_required_fields(tmp_path: Path) -> None:
    media_path = tmp_path / "reference.mp4"
    media_path.write_bytes(b"video")
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps({"product_or_solution": "Only one"}), encoding="utf-8"
    )
    transport = RecordingTransport(_successful_submission("copy_adaptation"))
    client = _authenticated_client(tmp_path, transport)

    with pytest.raises(CliUsageError, match="missing required fields"):
        _submit_job(
            _command_arguments("adapt", media_path, profile_path=profile_path),
            client,
        )

    assert transport.requests == []


def test_adapt_rejects_invalid_profile_field_types(tmp_path: Path) -> None:
    media_path = tmp_path / "reference.mp4"
    media_path.write_bytes(b"video")
    profile_path = tmp_path / "profile.json"
    profile = _valid_user_profile()
    profile["desired_duration"] = 0
    profile["benefits"] = "not-a-list"
    profile_path.write_text(json.dumps(profile), encoding="utf-8")
    transport = RecordingTransport(_successful_submission("copy_adaptation"))
    client = _authenticated_client(tmp_path, transport)

    with pytest.raises(CliUsageError, match="desired_duration"):
        _submit_job(
            _command_arguments("adapt", media_path, profile_path=profile_path),
            client,
        )

    assert transport.requests == []


@pytest.mark.parametrize("status_code", [422, 503])
def test_submission_exposes_only_public_api_error(
    tmp_path: Path,
    status_code: int,
) -> None:
    media_path = tmp_path / "reference.mp4"
    media_path.write_bytes(b"video")
    transport = RecordingTransport(
        FakeResponse(
            status_code,
            {
                "code": "pipeline_execution_failed",
                "details": {
                    "field": "file",
                    "secret_token": "must-not-appear",
                },
            },
        )
    )
    client = _authenticated_client(tmp_path, transport)

    with pytest.raises(CliApiError) as error_info:
        _submit_job(_command_arguments("analyze", media_path), client)

    assert error_info.value.status_code == status_code
    assert "must-not-appear" not in str(error_info.value)
    assert error_info.value.details == {"field": "file"}


def test_cancelled_upload_closes_file_without_creating_temp_files(
    tmp_path: Path,
) -> None:
    media_path = tmp_path / "reference.mp4"
    media_path.write_bytes(b"video")
    transport = RecordingTransport(exception=KeyboardInterrupt())
    client = _authenticated_client(tmp_path, transport)

    with pytest.raises(KeyboardInterrupt):
        _submit_job(_command_arguments("analyze", media_path), client)

    assert transport.requests[0]["files"]["file"][1].closed is True
    assert {path.name for path in tmp_path.iterdir()} == {
        "reference.mp4",
        "session.json",
    }


def test_main_returns_cancelled_exit_code_without_sensitive_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    media_path = tmp_path / "reference.mp4"
    media_path.write_bytes(b"video")

    class CancelledClient:
        def __init__(self, _config: object) -> None:
            pass

        def submit_job(self, **_kwargs: Any) -> dict[str, Any]:
            raise KeyboardInterrupt

    monkeypatch.setattr("cli.main.KyrgApiClient", CancelledClient)

    exit_code = main(
        [
            "--api-url",
            "http://api.example.test",
            "--session-file",
            str(tmp_path / "session.json"),
            "analyze",
            str(media_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 130
    assert captured.out == "Operation cancelled.\n"
    assert captured.err == ""
