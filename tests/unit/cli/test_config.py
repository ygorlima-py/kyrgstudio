"""Unit tests for CLI configuration and local session persistence."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from cli.config import (
    DEFAULT_API_BASE_URL,
    CliSession,
    SessionStore,
    normalize_api_base_url,
    resolve_config,
)
from cli.errors import CliConfigurationError


def test_explicit_api_url_wins_over_environment_and_local_file(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps({"api_base_url": "https://file.example.test"}),
        encoding="utf-8",
    )

    config = resolve_config(
        api_base_url="https://explicit.example.test",
        environ={
            "KYRG_API_URL": "https://environment.example.test",
            "KYRG_CONFIG_FILE": str(config_file),
        },
        home_directory=tmp_path,
    )

    assert config.api_base_url == "https://explicit.example.test/v1"


def test_environment_api_url_wins_over_local_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps({"api_base_url": "https://file.example.test"}),
        encoding="utf-8",
    )

    config = resolve_config(
        environ={
            "KYRG_API_URL": "https://environment.example.test",
            "KYRG_CONFIG_FILE": str(config_file),
        },
        home_directory=tmp_path,
    )

    assert config.api_base_url == "https://environment.example.test/v1"


def test_local_file_api_url_wins_over_default(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps({"api_base_url": "https://file.example.test/v1/"}),
        encoding="utf-8",
    )

    config = resolve_config(
        environ={"KYRG_CONFIG_FILE": str(config_file)},
        home_directory=tmp_path,
    )

    assert config.api_base_url == "https://file.example.test/v1"
    assert config.api_base_url != DEFAULT_API_BASE_URL


def test_default_api_url_is_used_when_no_configuration_exists(
    tmp_path: Path,
) -> None:
    config = resolve_config(environ={}, home_directory=tmp_path)

    assert config.api_base_url == DEFAULT_API_BASE_URL


@pytest.mark.parametrize(
    "value",
    [
        "",
        "ftp://api.example.test",
        "https://user:password@api.example.test",
        "https://api.example.test?secret=value",
        "not a url",
    ],
)
def test_invalid_api_url_is_rejected(value: str, tmp_path: Path) -> None:
    with pytest.raises(CliConfigurationError):
        resolve_config(
            api_base_url=value,
            environ={},
            home_directory=tmp_path,
        )


def test_invalid_local_configuration_json_is_rejected(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json"
    config_file.write_text("{invalid", encoding="utf-8")

    with pytest.raises(CliConfigurationError):
        resolve_config(
            environ={"KYRG_CONFIG_FILE": str(config_file)},
            home_directory=tmp_path,
        )


def test_invalid_local_api_url_type_is_rejected(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps({"api_base_url": 123}),
        encoding="utf-8",
    )

    with pytest.raises(CliConfigurationError):
        resolve_config(
            environ={"KYRG_CONFIG_FILE": str(config_file)},
            home_directory=tmp_path,
        )


@pytest.mark.parametrize(
    ("platform_name", "expected_config", "expected_session"),
    [
        (
            "linux",
            Path(".config") / "kyrg" / "config.json",
            Path(".local") / "share" / "kyrg" / "session.json",
        ),
        (
            "macos",
            Path("Library") / "Application Support" / "kyrg" / "config.json",
            Path("Library") / "Application Support" / "kyrg" / "session.json",
        ),
        (
            "windows",
            Path("AppData") / "Roaming" / "kyrg" / "config.json",
            Path("AppData") / "Local" / "kyrg" / "session.json",
        ),
    ],
)
def test_default_paths_are_platform_appropriate(
    platform_name: str,
    expected_config: Path,
    expected_session: Path,
    tmp_path: Path,
) -> None:
    config = resolve_config(
        environ={},
        home_directory=tmp_path,
        platform_name=platform_name,
    )

    assert config.session_file == tmp_path / expected_session

    config_file = tmp_path / expected_config
    config_file.parent.mkdir(parents=True)
    config_file.write_text(
        json.dumps({"api_base_url": "https://platform.example.test"}),
        encoding="utf-8",
    )

    configured = resolve_config(
        environ={},
        home_directory=tmp_path,
        platform_name=platform_name,
    )
    assert configured.api_base_url == "https://platform.example.test/v1"


def test_session_is_absent_before_first_login(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "session.json")

    assert store.load() is None


def test_session_is_saved_with_restricted_permissions_and_loaded(
    tmp_path: Path,
) -> None:
    session_path = tmp_path / "nested" / "session.json"
    session = CliSession(
        access_token="access-secret",
        refresh_token="refresh-secret",
        csrf_token="csrf-secret",
        access_token_expires_at="2030-01-01T00:00:00Z",
    )

    SessionStore(session_path).save(session)

    assert SessionStore(session_path).load() == session
    assert stat.S_IMODE(session_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(session_path.parent.stat().st_mode) == 0o700


def test_session_repr_does_not_expose_credentials() -> None:
    session = CliSession("access-secret", "refresh-secret", "csrf-secret")

    representation = repr(session)

    assert "access-secret" not in representation
    assert "refresh-secret" not in representation
    assert "csrf-secret" not in representation


def test_session_is_cleared_and_missing_after_cleanup(tmp_path: Path) -> None:
    session_path = tmp_path / "session.json"
    store = SessionStore(session_path)
    store.save(CliSession("access", "refresh", "csrf"))

    store.clear()

    assert not session_path.exists()
    assert store.load() is None
    store.clear()


def test_invalid_session_file_is_rejected(tmp_path: Path) -> None:
    session_path = tmp_path / "session.json"
    session_path.write_text(
        json.dumps({"access_token": "only-access-token"}),
        encoding="utf-8",
    )

    with pytest.raises(CliConfigurationError):
        SessionStore(session_path).load()


def test_normalize_api_base_url_rejects_missing_value() -> None:
    with pytest.raises(CliConfigurationError):
        normalize_api_base_url("   ")
