"""HTTP endpoints for application authentication.

This router translates validated HTTP payloads into ``AuthService`` use cases,
manages protected authentication cookies, and returns public response schemas.
Password hashing, Google verification, token signing, and persistence remain in
the authentication application layer.
"""

from __future__ import annotations

import secrets
from typing import Annotated, Final

from fastapi import APIRouter, Depends, Request, Response, status

from app.auth.dependencies import (
    RefreshCookieCredentials,
    get_auth_service,
    get_current_user,
    get_logout_credentials,
    get_refresh_credentials,
)
from app.auth.principal import (
    AuthenticatedPrincipal,
    IssuedAuthTokens,
)
from app.auth.service import AuthenticationResult, AuthService
from app.errors import AuthConfigurationError
from app.schemas.auth import (
    AccessTokenResponse,
    CurrentUserResponse,
    GoogleLoginRequest,
    PasswordLoginRequest,
    RegisterRequest,
)
from app.settings import AppSettings


AUTH_ROUTE_PREFIX: Final = "/v1/auth"
REFRESH_COOKIE_PATH: Final = AUTH_ROUTE_PREFIX
CSRF_COOKIE_PATH: Final = "/"
CSRF_TOKEN_BYTES: Final = 32

AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
CurrentUserDependency = Annotated[
    AuthenticatedPrincipal,
    Depends(get_current_user),
]
RefreshCredentialsDependency = Annotated[
    RefreshCookieCredentials,
    Depends(get_refresh_credentials),
]
LogoutCredentialsDependency = Annotated[
    RefreshCookieCredentials,
    Depends(get_logout_credentials),
]


router = APIRouter(
    prefix=AUTH_ROUTE_PREFIX,
    tags=["authentication"],
)


@router.post(
    "/register",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register with email and password",
)
async def register_with_password(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    auth_service: AuthServiceDependency,
) -> AccessTokenResponse:
    """Create a password account and establish its first session."""

    authentication = await auth_service.register_with_password(
        email=payload.email,
        password=payload.password,
        name=payload.name,
    )
    return _authentication_response(
        authentication,
        request=request,
        response=response,
    )


@router.post(
    "/login",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in with email and password",
)
async def login_with_password(
    payload: PasswordLoginRequest,
    request: Request,
    response: Response,
    auth_service: AuthServiceDependency,
) -> AccessTokenResponse:
    """Authenticate local credentials and establish a refresh session."""

    authentication = await auth_service.login_with_password(
        email=payload.email,
        password=payload.password,
    )
    return _authentication_response(
        authentication,
        request=request,
        response=response,
    )


@router.post(
    "/google",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in with Google",
)
async def login_with_google(
    payload: GoogleLoginRequest,
    request: Request,
    response: Response,
    auth_service: AuthServiceDependency,
) -> AccessTokenResponse:
    """Verify a Google ID token and establish an application session."""

    authentication = await auth_service.login_with_google(
        payload.google_id_token,
    )
    return _authentication_response(
        authentication,
        request=request,
        response=response,
    )


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh the authentication session",
)
async def refresh_authentication(
    request: Request,
    response: Response,
    credentials: RefreshCredentialsDependency,
    auth_service: AuthServiceDependency,
) -> AccessTokenResponse:
    """Rotate a protected refresh token and return a new access token."""

    authentication = await auth_service.refresh(credentials.refresh_token)
    return _authentication_response(
        authentication,
        request=request,
        response=response,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out of the current session",
)
async def logout(
    request: Request,
    response: Response,
    credentials: LogoutCredentialsDependency,
    auth_service: AuthServiceDependency,
) -> None:
    """Revoke the refresh-token family and remove browser credentials."""

    await auth_service.logout(credentials.refresh_token)
    settings = _application_settings(request)
    _delete_authentication_cookies(response, settings=settings)
    _set_no_store_headers(response)


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the current authenticated user",
)
async def get_current_authenticated_user(
    response: Response,
    principal: CurrentUserDependency,
) -> CurrentUserResponse:
    """Return the safe public identity represented by a valid access token."""

    _set_no_store_headers(response)
    return CurrentUserResponse.from_principal(principal)


def _authentication_response(
    authentication: AuthenticationResult,
    *,
    request: Request,
    response: Response,
) -> AccessTokenResponse:
    """Set rotated browser credentials and build the public token response."""

    settings = _application_settings(request)
    _set_authentication_cookies(
        response,
        settings=settings,
        tokens=authentication.tokens,
    )
    _set_no_store_headers(response)
    return AccessTokenResponse.from_issued_tokens(authentication.tokens)


def _set_authentication_cookies(
    response: Response,
    *,
    settings: AppSettings,
    tokens: IssuedAuthTokens,
) -> None:
    """Store the refresh credential and a newly rotated CSRF token."""

    cookie_max_age = settings.auth_refresh_token_ttl_seconds
    cookie_expires_at = tokens.refresh_token_expires_at
    cookie_same_site = settings.auth_refresh_cookie_samesite
    cookie_secure = settings.auth_refresh_cookie_secure

    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=tokens.refresh_token,
        max_age=cookie_max_age,
        expires=cookie_expires_at,
        path=REFRESH_COOKIE_PATH,
        secure=cookie_secure,
        httponly=True,
        samesite=cookie_same_site,
    )
    response.set_cookie(
        key=settings.auth_csrf_cookie_name,
        value=secrets.token_urlsafe(CSRF_TOKEN_BYTES),
        max_age=cookie_max_age,
        expires=cookie_expires_at,
        path=CSRF_COOKIE_PATH,
        secure=cookie_secure,
        httponly=False,
        samesite=cookie_same_site,
    )


def _delete_authentication_cookies(
    response: Response,
    *,
    settings: AppSettings,
) -> None:
    """Expire both authentication cookies using their original attributes."""

    response.delete_cookie(
        key=settings.auth_refresh_cookie_name,
        path=REFRESH_COOKIE_PATH,
        secure=settings.auth_refresh_cookie_secure,
        httponly=True,
        samesite=settings.auth_refresh_cookie_samesite,
    )
    response.delete_cookie(
        key=settings.auth_csrf_cookie_name,
        path=CSRF_COOKIE_PATH,
        secure=settings.auth_refresh_cookie_secure,
        httponly=False,
        samesite=settings.auth_refresh_cookie_samesite,
    )


def _application_settings(request: Request) -> AppSettings:
    settings = getattr(request.app.state, "settings", None)

    if not isinstance(settings, AppSettings):
        raise AuthConfigurationError(
            technical_message=(
                "Application settings are not configured in API state."
            ),
        )

    return settings


def _set_no_store_headers(response: Response) -> None:
    """Prevent browsers and intermediaries from caching auth responses."""

    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


__all__ = ["router"]
