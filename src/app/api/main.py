"""FastAPI application composition for Kyrg Studio.

This module wires together configuration, lifecycle management, middleware,
exception handlers, and HTTP routers. Importing it builds the ASGI application
but does not open database connections, initialize storage, contact the broker,
or execute workflows.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import install_exception_handlers
from app.api.lifespan import api_lifespan
from app.api.middleware import (
    REQUEST_ID_HEADER,
    install_request_id_middleware,
)
from app.api.routers.auth import router as auth_router
from app.api.routers.health import router as health_router
from app.api.routers.jobs import router as jobs_router
from app.auth.dependencies import CSRF_HEADER_NAME
from app.settings import AppSettings, load_settings


_ALLOWED_CORS_METHODS = ("GET", "POST", "OPTIONS")
_ALLOWED_CORS_HEADERS = (
    "Authorization",
    "Content-Type",
    "Idempotency-Key",
    CSRF_HEADER_NAME,
    REQUEST_ID_HEADER,
)


def create_app(settings: AppSettings | None = None) -> FastAPI:
    """Build the HTTP API from one resolved settings instance.

    Args:
        settings: Optional preloaded configuration. Tests and embedding
            applications can inject it to avoid reading process environment
            variables. When omitted, configuration is loaded exactly once.

    Returns:
        A fully composed FastAPI application. Runtime infrastructure is created
        later by the application lifespan.
    """

    resolved_settings = _resolve_settings(settings)
    application = FastAPI(lifespan=api_lifespan)
    application.state.settings = resolved_settings

    _configure_cors(application, settings=resolved_settings)
    install_request_id_middleware(application)
    install_exception_handlers(application)

    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(jobs_router)

    return application


def _resolve_settings(settings: AppSettings | None) -> AppSettings:
    """Return injected settings or load configuration for this application."""

    if settings is not None:
        if not isinstance(settings, AppSettings):
            raise TypeError("settings must be an AppSettings instance.")

        return settings

    return load_settings()


def _configure_cors(
    application: FastAPI,
    *,
    settings: AppSettings,
) -> None:
    """Install credential-aware CORS for explicitly allowed browser origins."""

    allowed_origins = _validated_cors_origins(settings.api_cors_origins)

    if not allowed_origins:
        return

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(allowed_origins),
        allow_credentials=True,
        allow_methods=list(_ALLOWED_CORS_METHODS),
        allow_headers=list(_ALLOWED_CORS_HEADERS),
        expose_headers=[REQUEST_ID_HEADER],
    )


def _validated_cors_origins(origins: tuple[str, ...]) -> tuple[str, ...]:
    """Normalize an explicit CORS allowlist and reject wildcard access."""

    normalized_origins = tuple(
        dict.fromkeys(
            origin.strip()
            for origin in origins
            if origin.strip()
        )
    )

    if "*" in normalized_origins:
        raise ValueError(
            "api_cors_origins must contain explicit origins; "
            "wildcard is not allowed."
        )

    return normalized_origins


app = create_app()


__all__ = ["app", "create_app"]
