"""Unit tests for the CLI login and logout flow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import requests

from cli.api_client import KyrgApiClient
from cli.config import CliConfig, CliSession, SessionStore
from cli.errors import CliAuthenticationError
from cli.main import main


class FakeResponse:
    """Response double for authentication endpoint tests."""

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
    """Transport double that records the requested endpoint."""

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


def _config(tmp_path: Path) -> CliConfig:
    return CliConfig(
        api_base_url="https://api.example.test/v1",
        session_file=tmp_path / "session.json",
        timeout_seconds=10,
    )


def test_login_calls_only_real_login_endpoint_and_saves_session(
    tmp_path: Path,
) -> None:
    transport = FakeTransport(
        [
            FakeResponse(
                200,
                {
                    "access_token": "access-token",
                    "access_token_expires_at": "2030-01-01T00:00:00Z",
                },
                cookies={
                    "kyrg_refresh_token": "refresh-token",
                    "kyrg_csrf_token": "csrf-token",
                },
            )
        ]
    )
    store = SessionStore(tmp_path / "session.json")
    client = KyrgApiClient(
        _config(tmp_path),
        session_store=store,
        transport=transport,
    )

    client.login(email="user@example.com", password="password-secret")

    assert len(transport.requests) == 1
    assert transport.requests[0]["method"] == "POST"
    assert transport.requests[0]["url"] == "https://api.example.test/v1/auth/login"
    assert transport.requests[0]["json"] == {
        "email": "user@example.com",
        "password": "password-secret",
    }

    saved_session = store.load()
    assert saved_session == CliSession(
        access_token="access-token",
        refresh_token="refresh-token",
        csrf_token="csrf-token",
        access_token_expires_at="2030-01-01T00:00:00Z",
    )
    assert "password-secret" not in (tmp_path / "session.json").read_text()


def test_login_invalid_credentials_returns_public_auth_error(
    tmp_path: Path,
) -> None:
    transport = FakeTransport(
        [
            FakeResponse(
                401,
                {
                    "code": "invalid_credentials",
                    "details": {"password": "must not be exposed"},
                },
            )
        ]
    )
    client = KyrgApiClient(
        _config(tmp_path),
        session_store=SessionStore(tmp_path / "session.json"),
        transport=transport,
    )

    with pytest.raises(CliAuthenticationError) as error_info:
        client.login(email="user@example.com", password="password-secret")

    assert str(error_info.value) == "The email or password is incorrect."
    assert error_info.value.status_code == 401
    assert "password-secret" not in str(error_info.value)
    assert "must not be exposed" not in str(error_info.value)


def test_logout_revokes_remote_session_and_clears_local_session(
    tmp_path: Path,
) -> None:
    store = SessionStore(tmp_path / "session.json")
    store.save(CliSession("access-token", "refresh-token", "csrf-token"))
    transport = FakeTransport([FakeResponse(204, None)])
    client = KyrgApiClient(
        _config(tmp_path),
        session_store=store,
        transport=transport,
    )

    assert client.logout() is True

    assert not (tmp_path / "session.json").exists()
    assert transport.requests[0]["url"] == "https://api.example.test/v1/auth/logout"
    assert transport.requests[0]["headers"]["X-CSRF-Token"] == "csrf-token"


def test_logout_clears_local_session_when_api_is_unavailable(
    tmp_path: Path,
) -> None:
    store = SessionStore(tmp_path / "session.json")
    store.save(CliSession("access-token", "refresh-token", "csrf-token"))
    transport = FakeTransport(exception=requests.ConnectionError("refresh-token"))
    client = KyrgApiClient(
        _config(tmp_path),
        session_store=store,
        transport=transport,
    )

    assert client.logout() is False

    assert not (tmp_path / "session.json").exists()
    assert client._session is None


class FakeCommandClient:
    """Client double used to test public command output and exit codes."""

    last_instance: FakeCommandClient | None = None

    def __init__(self, _config: CliConfig) -> None:
        self.login_arguments: tuple[str, str] | None = None
        self.logout_result = True
        FakeCommandClient.last_instance = self

    def login(self, *, email: str, password: str) -> None:
        self.login_arguments = (email, password)

    def logout(self) -> bool:
        return self.logout_result


def test_login_command_hides_password_and_returns_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("cli.main.KyrgApiClient", FakeCommandClient)
    monkeypatch.setattr("cli.main.getpass.getpass", lambda _prompt: "password-secret")
    monkeypatch.setattr("builtins.input", lambda _prompt: "user@example.com")

    exit_code = main(
        [
            "--output",
            "json",
            "--session-file",
            str(tmp_path / "session.json"),
            "login",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == {
        "status": "logged_in",
        "message": "Login successful.",
    }
    assert "password-secret" not in captured.out
    assert "password-secret" not in captured.err
    assert FakeCommandClient.last_instance is not None
    assert FakeCommandClient.last_instance.login_arguments == (
        "user@example.com",
        "password-secret",
    )


def test_login_command_returns_predictable_auth_failure_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class FailingCommandClient(FakeCommandClient):
        def login(self, *, email: str, password: str) -> None:
            raise CliAuthenticationError(
                "The email or password is incorrect.",
                status_code=401,
                code="invalid_credentials",
            )

    monkeypatch.setattr("cli.main.KyrgApiClient", FailingCommandClient)
    monkeypatch.setattr("cli.main.getpass.getpass", lambda _prompt: "password-secret")

    exit_code = main(
        [
            "--session-file",
            str(tmp_path / "session.json"),
            "login",
            "--email",
            "user@example.com",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 3
    assert "email or password is incorrect" in captured.err
    assert "password-secret" not in captured.err


def test_logout_command_reports_local_cleanup_without_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class LocallyClearedCommandClient(FakeCommandClient):
        def logout(self) -> bool:
            return False

    monkeypatch.setattr("cli.main.KyrgApiClient", LocallyClearedCommandClient)

    exit_code = main(
        [
            "--output",
            "json",
            "--session-file",
            str(tmp_path / "session.json"),
            "logout",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload == {
        "status": "logged_out",
        "message": "Local session cleared; the API could not be reached.",
        "remote_logout": False,
    }
    assert "token" not in captured.out.lower()
    assert captured.err == ""
