"""FastAPI dependencies for application authentication boundaries.

Bearer authentication is accepted exclusively from the ``Authorization``
header. Refresh and logout credentials are accepted exclusively from the
configured refresh cookie and are protected with double-submit CSRF validation
plus an Origin or Referer check.

This module adapts HTTP input to ``AuthService``. It does not implement login,
token issuance, Google verification, persistence, or account policy.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Annotated, Final, TypeGuard
from urllib.parse import urlsplit

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.principal import AuthenticatedPrincipal
from app.auth.service import AuthService
from app.errors import (
    AuthenticationRequiredError,
    AuthConfigurationError,
    CsrfValidationError,
    RefreshTokenInvalidError,
)
from app.settings import AppSettings


CSRF_HEADER_NAME: Final = "X-CSRF-Token"
MAXIMUM_HTTP_CREDENTIAL_LENGTH: Final = 16_384

_bearer_authentication = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True, kw_only=True)
class RefreshCookieCredentials:
    """Validated refresh credential extracted from a protected cookie request."""

    refresh_token: str = field(repr=False)


def get_auth_service(request: Request) -> AuthService:
    """Return the API-scoped authentication service created by the lifespan."""

    auth_service = getattr(request.app.state, "auth_service", None)

    if not isinstance(auth_service, AuthService):
        raise AuthConfigurationError(
            technical_message=(
                "AuthService is not configured in the API application state."
            ),
        )

    return auth_service


async def get_current_user(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    authorization: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_authentication),
    ],
) -> AuthenticatedPrincipal:
    """Authenticate one Bearer access token and return the current principal.

    ``AuthService`` loads the user through its short-lived transactional
    adapter. Consequently, no database session remains open while the protected
    route uploads media, schedules work, or performs another slow operation.
    """

    access_token = _required_bearer_access_token(authorization)
    return await auth_service.authenticate_access_token(access_token)


async def get_refresh_credentials(
    request: Request,
) -> RefreshCookieCredentials:
    """Validate cookie, CSRF, and request origin for token refresh."""

    return _protected_refresh_cookie_credentials(request)


async def get_logout_credentials(
    request: Request,
) -> RefreshCookieCredentials:
    """Validate cookie, CSRF, and request origin for logout."""

    return _protected_refresh_cookie_credentials(request)


def _protected_refresh_cookie_credentials(
    request: Request,
) -> RefreshCookieCredentials:
    settings = _application_settings(request)
    _require_trusted_request_origin(request, settings=settings)
    _require_matching_csrf_tokens(request, settings=settings)
    refresh_token = _required_refresh_cookie(request, settings=settings)
    return RefreshCookieCredentials(refresh_token=refresh_token)


def _required_bearer_access_token(
    authorization: HTTPAuthorizationCredentials | None,
) -> str:
    if authorization is None or authorization.scheme.lower() != "bearer":
        raise _authentication_required()

    access_token = authorization.credentials

    if (
        not access_token
        or access_token != access_token.strip()
        or len(access_token) > MAXIMUM_HTTP_CREDENTIAL_LENGTH
    ):
        raise _authentication_required()

    return access_token


def _required_refresh_cookie(
    request: Request,
    *,
    settings: AppSettings,
) -> str:
    refresh_token = request.cookies.get(settings.auth_refresh_cookie_name)

    if (
        refresh_token is None
        or not refresh_token
        or refresh_token != refresh_token.strip()
        or len(refresh_token) > MAXIMUM_HTTP_CREDENTIAL_LENGTH
    ):
        raise RefreshTokenInvalidError(
            technical_message="Refresh token cookie is missing or invalid.",
        )

    return refresh_token


def _require_matching_csrf_tokens(
    request: Request,
    *,
    settings: AppSettings,
) -> None:
    csrf_cookie = request.cookies.get(settings.auth_csrf_cookie_name)
    csrf_header = request.headers.get(CSRF_HEADER_NAME)

    if not _valid_csrf_value(csrf_cookie) or not _valid_csrf_value(csrf_header):
        raise _csrf_validation_failed()

    if not secrets.compare_digest(csrf_cookie, csrf_header):
        raise _csrf_validation_failed()


def _valid_csrf_value(value: str | None) -> TypeGuard[str]:
    return (
        value is not None
        and bool(value)
        and value == value.strip()
        and len(value) <= MAXIMUM_HTTP_CREDENTIAL_LENGTH
    )


def _require_trusted_request_origin(
    request: Request,
    *,
    settings: AppSettings,
) -> None:
    supplied_origin = request.headers.get("Origin")

    if supplied_origin is not None:
        request_origin = _normalized_origin(supplied_origin)
    else:
        referer = request.headers.get("Referer")
        request_origin = _normalized_origin(referer) if referer else None

    if request_origin is None:
        raise _csrf_validation_failed()

    accepted_origins = _accepted_request_origins(request, settings=settings)

    if request_origin not in accepted_origins:
        raise _csrf_validation_failed()


def _accepted_request_origins(
    request: Request,
    *,
    settings: AppSettings,
) -> frozenset[str]:
    configured_origins: set[str] = set()

    for configured_origin in settings.api_cors_origins:
        normalized_origin = _normalized_origin(configured_origin)

        if normalized_origin is None:
            raise AuthConfigurationError(
                technical_message="Configured API CORS origin is invalid.",
            )

        configured_origins.add(normalized_origin)

    application_origin = _normalized_origin(str(request.base_url))

    if application_origin is not None:
        configured_origins.add(application_origin)

    return frozenset(configured_origins)


def _normalized_origin(value: str) -> str | None:
    candidate = value.strip()

    if not candidate or candidate.lower() == "null":
        return None

    try:
        parsed = urlsplit(candidate)
        port = parsed.port
    except ValueError:
        return None

    scheme = parsed.scheme.lower()
    hostname = parsed.hostname

    if (
        scheme not in {"http", "https"}
        or hostname is None
        or parsed.username is not None
        or parsed.password is not None
    ):
        return None

    normalized_hostname = hostname.lower()

    if ":" in normalized_hostname:
        normalized_hostname = f"[{normalized_hostname}]"

    default_port = 80 if scheme == "http" else 443
    port_suffix = "" if port in {None, default_port} else f":{port}"
    return f"{scheme}://{normalized_hostname}{port_suffix}"


def _application_settings(request: Request) -> AppSettings:
    settings = getattr(request.app.state, "settings", None)

    if not isinstance(settings, AppSettings):
        raise AuthConfigurationError(
            technical_message=(
                "Application settings are not configured in API state."
            ),
        )

    return settings


def _authentication_required() -> AuthenticationRequiredError:
    return AuthenticationRequiredError(
        technical_message="Bearer authentication is required.",
    )


def _csrf_validation_failed() -> CsrfValidationError:
    return CsrfValidationError(
        technical_message="CSRF validation failed for cookie authentication.",
    )


__all__ = [
    "CSRF_HEADER_NAME",
    "RefreshCookieCredentials",
    "get_auth_service",
    "get_current_user",
    "get_logout_credentials",
    "get_refresh_credentials",
]
