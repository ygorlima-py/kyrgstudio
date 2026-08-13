from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import requests

from cli.api_client import KyrgApiClient
from cli.config import CliSession, SessionStore, normalize_api_base_url, resolve_config
from cli.errors import CliAuthenticationError, CliConfigurationError
from cli.main import create_argument_parser, main
from cli.output import ConsoleOutput, format_human


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: object,
        *,
        cookies: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.cookies = requests.cookies.RequestsCookieJar()
        for name, value in (cookies or {}).items():
            self.cookies.set(name, value)

    def json(self) -> object:
        if isinstance(self._payload, BaseException):
            raise json.JSONDecodeError("Invalid fake JSON.", "", 0) from self._payload
        return self._payload


class FakeHttpSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.requests: list[dict[str, Any]] = []

    def request(self, **kwargs: Any) -> FakeResponse:
        self.requests.append(kwargs)
        return self.responses.pop(0)


def test_normalize_api_base_url_adds_v1() -> None:
    assert normalize_api_base_url("http://localhost:8000") == "http://localhost:8000/v1"
    assert (
        normalize_api_base_url("http://localhost:8000/v1/")
        == "http://localhost:8000/v1"
    )


def test_resolve_config_uses_explicit_values_before_environment(tmp_path: Path) -> None:
    config = resolve_config(
        api_base_url="https://api.example.test",
        timeout_seconds=12,
        environ={"KYRG_API_URL": "https://wrong.example.test"},
        home_directory=tmp_path,
    )

    assert config.api_base_url == "https://api.example.test/v1"
    assert config.timeout_seconds == 12


def test_session_store_saves_and_clears_owner_only_session(tmp_path: Path) -> None:
    session_path = tmp_path / "data" / "session.json"
    store = SessionStore(session_path)
    session = CliSession("access", "refresh", "csrf")

    store.save(session)

    assert store.load() == session
    assert session_path.stat().st_mode & 0o777 == 0o600

    store.clear()
    assert store.load() is None


def test_session_store_rejects_invalid_session(tmp_path: Path) -> None:
    session_path = tmp_path / "session.json"
    session_path.write_text(json.dumps({"access_token": "only-one"}), encoding="utf-8")

    try:
        SessionStore(session_path).load()
    except CliConfigurationError:
        pass
    else:
        raise AssertionError("Invalid session data must be rejected.")


def test_parser_supports_help_version_and_job_commands() -> None:
    parser = create_argument_parser()

    arguments = parser.parse_args(["status", "12"])

    assert arguments.command == "status"
    assert arguments.job_id == 12


def test_login_persists_api_tokens_without_printing_them(tmp_path: Path) -> None:
    fake_http = FakeHttpSession(
        [
            FakeResponse(
                200,
                {
                    "access_token": "access-secret",
                    "access_token_expires_at": "2030-01-01T00:00:00Z",
                },
                cookies={
                    "kyrg_refresh_token": "refresh-secret",
                    "kyrg_csrf_token": "csrf-secret",
                },
            )
        ]
    )
    config = resolve_config(home_directory=tmp_path)
    client = KyrgApiClient(
        config,
        session_store=SessionStore(tmp_path / "session.json"),
        http_session=fake_http,  # type: ignore[arg-type]
    )

    client.login(email="user@example.com", password="password")

    stored = SessionStore(tmp_path / "session.json").load()
    assert stored is not None
    assert stored.access_token == "access-secret"
    assert fake_http.requests[0]["json"] == {
        "email": "user@example.com",
        "password": "password",
    }


def test_status_returns_only_public_fields(tmp_path: Path) -> None:
    fake_http = FakeHttpSession(
        [
            FakeResponse(
                200,
                {
                    "job_id": 9,
                    "status": "completed",
                    "pipeline_type": "copy_analysis",
                    "created_at": "2030-01-01T00:00:00Z",
                    "input_path": "/private/input.mp4",
                    "output_json": {"secret": True},
                },
            )
        ]
    )
    session = CliSession("access", "refresh", "csrf")
    client = KyrgApiClient(
        resolve_config(home_directory=tmp_path),
        session_store=SessionStore(tmp_path / "session.json"),
        http_session=fake_http,  # type: ignore[arg-type]
    )
    client.session_store.save(session)
    client._session = session

    status = client.get_job_status(9)

    assert status == {
        "job_id": 9,
        "status": "completed",
        "pipeline_type": "copy_analysis",
        "created_at": "2030-01-01T00:00:00Z",
    }
    assert "input_path" not in status
    assert fake_http.requests[0]["headers"]["Authorization"] == "Bearer access"


def test_authentication_error_is_classified_without_backend_details(
    tmp_path: Path,
) -> None:
    fake_http = FakeHttpSession(
        [FakeResponse(401, {"code": "invalid_credentials", "details": {"secret": "x"}})]
    )
    client = KyrgApiClient(
        resolve_config(home_directory=tmp_path),
        http_session=fake_http,  # type: ignore[arg-type]
    )

    try:
        client.login(email="user@example.com", password="wrong")
    except CliAuthenticationError as error:
        assert str(error) == "The email or password is incorrect."
        assert "secret" not in str(error)
    else:
        raise AssertionError("401 must become a CLI authentication error.")


def test_output_supports_human_and_json_formats() -> None:
    human_stdout = io.StringIO()
    human = ConsoleOutput(stdout=human_stdout, stderr=io.StringIO())
    human.write_data({"job_id": 4, "status": "running"})
    assert "Job id: 4" in human_stdout.getvalue()

    json_stdout = io.StringIO()
    structured = ConsoleOutput("json", stdout=json_stdout, stderr=io.StringIO())
    structured.write_data({"status": "running"})
    assert json.loads(json_stdout.getvalue()) == {"status": "running"}
    assert "Status: running" in format_human({"status": "running"})


def test_main_without_command_prints_help(capsys: Any) -> None:
    assert main([]) == 0
    assert "usage:" in capsys.readouterr().out.lower()
