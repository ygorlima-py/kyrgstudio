"""Public error contracts for the Kyrg Studio command-line client."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class CliError(Exception):
    """Base class for expected failures shown to the CLI user."""

    exit_code = 1

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


class CliUsageError(CliError):
    """Raised when local command arguments fail validation."""

    exit_code = 2


class CliConfigurationError(CliError):
    """Raised when local configuration or session data is invalid."""

    exit_code = 2


class CliAuthenticationError(CliError):
    """Raised when the API rejects the current authentication session."""

    exit_code = 3

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class CliNotFoundError(CliError):
    """Raised when a requested public resource does not exist."""

    exit_code = 4

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class CliConflictError(CliError):
    """Raised when an operation conflicts with the resource state."""

    exit_code = 5

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class CliApiError(CliError):
    """Raised for a public API validation or infrastructure failure."""

    exit_code = 7

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        code: str,
        step: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.step = step
        self.details = dict(details or {})


class CliNetworkError(CliError):
    """Raised when the CLI cannot reach the configured API."""

    exit_code = 6


class CliJobFailedError(CliError):
    """Raised when a requested job is in the public failed state."""

    exit_code = 8


__all__ = [
    "CliApiError",
    "CliAuthenticationError",
    "CliConfigurationError",
    "CliConflictError",
    "CliError",
    "CliJobFailedError",
    "CliNetworkError",
    "CliNotFoundError",
    "CliUsageError",
]
