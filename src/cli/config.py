"""Local configuration and protected session storage for the CLI."""

from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .errors import CliConfigurationError

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/v1"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_REFRESH_COOKIE_NAME = "kyrg_refresh_token"
DEFAULT_CSRF_COOKIE_NAME = "kyrg_csrf_token"
APPLICATION_DIRECTORY_NAME = "kyrg"


@dataclass(frozen=True, slots=True)
class CliConfig:
    """Resolved settings needed by one CLI process."""

    api_base_url: str
    session_file: Path
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    refresh_cookie_name: str = DEFAULT_REFRESH_COOKIE_NAME
    csrf_cookie_name: str = DEFAULT_CSRF_COOKIE_NAME

    @property
    def api_origin(self) -> str:
        """Return the API origin used for the CSRF Origin header."""

        parsed = urlsplit(self.api_base_url)
        return f"{parsed.scheme}://{parsed.netloc}"


@dataclass(frozen=True, slots=True)
class CliSession:
    """Protected authentication values persisted for future CLI commands."""

    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    csrf_token: str = field(repr=False)
    access_token_expires_at: str | None = field(default=None, repr=False)

    def as_mapping(self) -> dict[str, str]:
        """Return the minimal serializable session representation."""

        values = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "csrf_token": self.csrf_token,
        }

        if self.access_token_expires_at is not None:
            values["access_token_expires_at"] = self.access_token_expires_at

        return values

    @classmethod
    def from_mapping(cls, value: object) -> CliSession:
        """Validate untrusted JSON loaded from the local session file."""

        if not isinstance(value, dict):
            raise CliConfigurationError("The local CLI session is invalid.")

        required_values: dict[str, str] = {}
        for field_name in ("access_token", "refresh_token", "csrf_token"):
            field_value = value.get(field_name)

            if not isinstance(field_value, str) or not field_value.strip():
                raise CliConfigurationError("The local CLI session is invalid.")

            required_values[field_name] = field_value

        expiration = value.get("access_token_expires_at")
        if expiration is not None and not isinstance(expiration, str):
            raise CliConfigurationError("The local CLI session is invalid.")

        return cls(
            **required_values,
            access_token_expires_at=expiration,
        )


class SessionStore:
    """Read, atomically write, and remove the CLI session file."""

    def __init__(self, path: Path) -> None:
        self.path = path.expanduser()

    def load(self) -> CliSession | None:
        """Load the session or return ``None`` when the user is logged out."""

        try:
            content = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError as error:
            raise CliConfigurationError(
                "The local CLI session could not be read."
            ) from error

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as error:
            raise CliConfigurationError(
                "The local CLI session contains invalid data."
            ) from error

        return CliSession.from_mapping(payload)

    def save(self, session: CliSession) -> None:
        """Persist a session with owner-only file permissions."""

        parent = self.path.parent
        temporary_path: Path | None = None

        try:
            parent.mkdir(parents=True, exist_ok=True)
            _restrict_directory_permissions(parent)

            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=parent,
                prefix=f".{self.path.name}.",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(
                    json.dumps(session.as_mapping(), ensure_ascii=False)
                )
                temporary_file.write("\n")
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            _restrict_file_permissions(temporary_path)
            os.replace(temporary_path, self.path)
            _restrict_file_permissions(self.path)
        except OSError as error:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise CliConfigurationError(
                "The local CLI session could not be saved."
            ) from error

    def clear(self) -> None:
        """Remove the local session without failing when it is absent."""

        try:
            self.path.unlink(missing_ok=True)
        except OSError as error:
            raise CliConfigurationError(
                "The local CLI session could not be removed."
            ) from error


def resolve_config(
    *,
    api_base_url: str | None = None,
    timeout_seconds: float | None = None,
    environ: Mapping[str, str] | None = None,
    home_directory: Path | None = None,
    platform_name: str | None = None,
) -> CliConfig:
    """Resolve CLI settings from explicit values, environment, and a file.

    Precedence is explicit command-line value, environment variable, local
    config file, and finally the development default.
    """

    environment: Mapping[str, str] = os.environ if environ is None else environ
    home = (Path.home() if home_directory is None else home_directory).expanduser()
    config_file = _config_file_path(
        environment=environment,
        home=home,
        platform_name=platform_name,
    )
    file_values = _read_optional_config_file(config_file)

    configured_url = _first_configured_value(
        explicit_value=api_base_url,
        environment_value=environment.get("KYRG_API_URL"),
        file_value=file_values.get("api_base_url"),
        default_value=DEFAULT_API_BASE_URL,
        field_name="API URL",
    )
    configured_timeout = _resolve_timeout(
        timeout_seconds=timeout_seconds,
        environment=environment,
        file_value=file_values.get("timeout_seconds"),
    )
    session_file_value = environment.get("KYRG_SESSION_FILE") or _string_value(
        file_values.get("session_file")
    )
    session_file = (
        Path(session_file_value).expanduser()
        if session_file_value
        else _default_session_file(
            environment=environment,
            home=home,
            platform_name=platform_name,
        )
    )

    return CliConfig(
        api_base_url=normalize_api_base_url(configured_url),
        session_file=session_file,
        timeout_seconds=configured_timeout,
        refresh_cookie_name=environment.get(
            "KYRG_REFRESH_COOKIE_NAME",
            DEFAULT_REFRESH_COOKIE_NAME,
        ),
        csrf_cookie_name=environment.get(
            "KYRG_CSRF_COOKIE_NAME",
            DEFAULT_CSRF_COOKIE_NAME,
        ),
    )


def normalize_api_base_url(value: str) -> str:
    """Validate and normalize an API origin or an API ``/v1`` URL."""

    if not isinstance(value, str):
        raise CliConfigurationError("The API URL must be text.")

    candidate = value.strip().rstrip("/")

    if not candidate:
        raise CliConfigurationError("The API URL must not be empty.")

    parsed = urlsplit(candidate)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise CliConfigurationError(
            "The API URL must be an http(s) URL without credentials or query parameters."
        )

    path = parsed.path.rstrip("/")
    if not path or path == "/":
        path = "/v1"
    elif not path.endswith("/v1"):
        path = f"{path}/v1"

    return f"{parsed.scheme}://{parsed.netloc}{path}"


def _config_file_path(
    *,
    environment: Mapping[str, str],
    home: Path,
    platform_name: str | None,
) -> Path:
    configured_path = environment.get("KYRG_CONFIG_FILE")
    if configured_path:
        return Path(configured_path).expanduser()

    resolved_platform = _platform_name(platform_name)

    if resolved_platform == "windows":
        base_directory = Path(
            environment.get("APPDATA", str(home / "AppData" / "Roaming"))
        ).expanduser()
    elif resolved_platform == "macos":
        base_directory = home / "Library" / "Application Support"
    else:
        config_home = environment.get("XDG_CONFIG_HOME")
        base_directory = (
            Path(config_home).expanduser() if config_home else home / ".config"
        )

    return base_directory / APPLICATION_DIRECTORY_NAME / "config.json"


def _default_session_file(
    *,
    environment: Mapping[str, str],
    home: Path,
    platform_name: str | None,
) -> Path:
    resolved_platform = _platform_name(platform_name)

    if resolved_platform == "windows":
        base_directory = Path(
            environment.get(
                "LOCALAPPDATA",
                str(home / "AppData" / "Local"),
            )
        ).expanduser()
    elif resolved_platform == "macos":
        base_directory = home / "Library" / "Application Support"
    else:
        data_home = environment.get("XDG_DATA_HOME")
        base_directory = (
            Path(data_home).expanduser() if data_home else home / ".local" / "share"
        )

    return base_directory / APPLICATION_DIRECTORY_NAME / "session.json"


def _platform_name(value: str | None = None) -> str:
    if value is not None:
        normalized_value = value.strip().lower()
        if normalized_value in {"windows", "win32", "nt"}:
            return "windows"
        if normalized_value in {"macos", "mac", "darwin"}:
            return "macos"
        if normalized_value in {"linux", "unix", "posix"}:
            return "linux"
        raise CliConfigurationError("The CLI platform value is invalid.")

    if os.name == "nt":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def _read_optional_config_file(path: Path) -> dict[str, Any]:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as error:
        raise CliConfigurationError(
            "The local CLI configuration could not be read."
        ) from error

    try:
        payload = json.loads(content)
    except json.JSONDecodeError as error:
        raise CliConfigurationError(
            "The local CLI configuration contains invalid JSON."
        ) from error

    if not isinstance(payload, dict):
        raise CliConfigurationError(
            "The local CLI configuration must contain a JSON object."
        )

    return payload


def _resolve_timeout(
    *,
    timeout_seconds: float | None,
    environment: Mapping[str, str],
    file_value: object,
) -> float:
    environment_value = environment.get("KYRG_TIMEOUT_SECONDS")
    value: object = (
        timeout_seconds
        if timeout_seconds is not None
        else environment_value
        if environment_value is not None
        else file_value
    )

    if value is None:
        return DEFAULT_TIMEOUT_SECONDS

    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise CliConfigurationError(
            "The CLI timeout must be a positive number of seconds."
        )

    try:
        parsed_value = float(value)
    except (TypeError, ValueError) as error:
        raise CliConfigurationError(
            "The CLI timeout must be a positive number of seconds."
        ) from error

    if parsed_value <= 0:
        raise CliConfigurationError(
            "The CLI timeout must be a positive number of seconds."
        )

    return parsed_value


def _first_configured_value(
    *,
    explicit_value: object,
    environment_value: object,
    file_value: object,
    default_value: str,
    field_name: str,
) -> str:
    for value in (explicit_value, environment_value, file_value):
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            raise CliConfigurationError(f"The configured {field_name} is invalid.")
        return value

    return default_value


def _restrict_directory_permissions(path: Path) -> None:
    """Restrict a configuration directory to the current user where supported."""

    if os.name == "nt":
        # Windows user-data directories are already scoped to the current
        # profile. The mode keeps the directory writable without making it
        # world-writable on platforms that emulate POSIX permissions.
        os.chmod(path, stat.S_IRWXU)
        return

    os.chmod(path, stat.S_IRWXU)


def _restrict_file_permissions(path: Path) -> None:
    """Restrict a session file to the current user where supported."""

    if os.name == "nt":
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        return

    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def _string_value(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


__all__ = [
    "APPLICATION_DIRECTORY_NAME",
    "DEFAULT_API_BASE_URL",
    "CliConfig",
    "CliSession",
    "SessionStore",
    "normalize_api_base_url",
    "resolve_config",
]
