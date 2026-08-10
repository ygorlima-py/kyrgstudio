from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, cast

from dotenv import load_dotenv


load_dotenv()

AuthJWTAlgorithm = Literal["HS256"]
AuthCookieSameSite = Literal["lax", "strict", "none"]

SUPPORTED_AUTH_JWT_ALGORITHMS = ("HS256",)
SUPPORTED_AUTH_COOKIE_SAME_SITE_VALUES = ("lax", "strict", "none")
MINIMUM_AUTH_JWT_SECRET_BYTES = 32
COOKIE_NAME_PATTERN = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")


DEFAULT_ACCEPTED_INPUT_MEDIA_TYPES = (
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-msvideo",
    "audio/mpeg",
    "audio/mp4",
    "audio/ogg",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
)


@dataclass(frozen=True)
class AppSettings:
    """Validated application configuration loaded from environment variables."""

    environment: str
    storage_dir: Path
    sqlite_path: Path

    database_url: str
    database_echo: bool
    database_pool_size: int
    database_max_overflow: int
    database_pool_pre_ping: bool

    openrouter_api_key: str | None
    openai_api_key: str | None
    gemini_api_key: str | None

    default_llm_provider: str
    default_analysis_model: str
    default_adaptation_model: str

    default_transcriber_provider: str
    default_transcriber_model: str

    max_duration_seconds: int
    request_timeout_seconds: int

    celery_broker_url: str
    celery_queue_name: str
    celery_task_soft_time_limit_seconds: int
    celery_task_time_limit_seconds: int

    # HTTP API configuration.
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_cors_origins: tuple[str, ...] = ()
    public_web_url: str = "http://localhost:8080"
    max_upload_bytes: int = 2 * 1024 * 1024 * 1024
    api_upload_timeout_seconds: int = 1800
    accepted_input_media_types: tuple[str, ...] = (
        DEFAULT_ACCEPTED_INPUT_MEDIA_TYPES
    )

    # Authentication configuration.
    auth_jwt_secret: str | None = field(default=None, repr=False)
    auth_jwt_algorithm: AuthJWTAlgorithm = "HS256"
    auth_issuer: str = "kyrgstudio"
    auth_audience: str = "kyrgstudio-api"
    auth_access_token_ttl_seconds: int = 900
    auth_refresh_token_ttl_seconds: int = 30 * 24 * 60 * 60
    auth_refresh_cookie_name: str = "kyrg_refresh_token"
    auth_refresh_cookie_secure: bool = False
    auth_refresh_cookie_samesite: AuthCookieSameSite = "lax"
    auth_csrf_cookie_name: str = "kyrg_csrf_token"
    auth_allowed_clock_skew_seconds: int = 30
    google_client_ids: tuple[str, ...] = ()
    
    #Email Auth
    email_host: str = "smtp.gmail.com"
    email_port: int = 465
    email_username: str | None = None
    email_password: str | None = field(default=None, repr=False)
    email_from: str | None = None
    email_from_name: str = "Kyrg Studio"

    def require_auth_jwt_secret(self) -> str:
        """Return the configured JWT secret or reject incomplete auth setup.

        Authentication calls this boundary while being constructed. Keeping
        the check here avoids an insecure development fallback without making
        unrelated worker and storage processes depend on auth configuration.
        """

        if self.auth_jwt_secret is None:
            raise ValueError(
                "AUTH_JWT_SECRET is required when authentication is enabled."
            )

        return _validate_auth_jwt_secret(self.auth_jwt_secret)


def load_settings() -> AppSettings:
    """Load application settings once from environment variables."""

    environment = _environment_text(
        "APP_ENV",
        default="development",
    ).lower()
    storage_dir = Path(os.getenv("APP_STORAGE_DIR", ".storage"))
    sqlite_path = Path(
        os.getenv("APP_SQLITE_PATH", str(storage_dir / "app.sqlite"))
    )
    auth_access_token_ttl_seconds = _positive_environment_int(
        "AUTH_ACCESS_TOKEN_TTL_SECONDS",
        default=900,
    )
    auth_refresh_token_ttl_seconds = _positive_environment_int(
        "AUTH_REFRESH_TOKEN_TTL_SECONDS",
        default=30 * 24 * 60 * 60,
    )
    auth_refresh_cookie_secure = _environment_bool(
        "AUTH_REFRESH_COOKIE_SECURE",
        default=_requires_secure_cookies(environment),
    )
    auth_refresh_cookie_samesite = _auth_cookie_same_site()
    auth_refresh_cookie_name = _environment_cookie_name(
        "AUTH_REFRESH_COOKIE_NAME",
        default="kyrg_refresh_token",
    )
    auth_csrf_cookie_name = _environment_cookie_name(
        "AUTH_CSRF_COOKIE_NAME",
        default="kyrg_csrf_token",
    )
    auth_allowed_clock_skew_seconds = _non_negative_environment_int(
        "AUTH_ALLOWED_CLOCK_SKEW_SECONDS",
        default=30,
    )

    _validate_auth_ttls(
        access_token_ttl_seconds=auth_access_token_ttl_seconds,
        refresh_token_ttl_seconds=auth_refresh_token_ttl_seconds,
        allowed_clock_skew_seconds=auth_allowed_clock_skew_seconds,
    )
    _validate_auth_cookie_security(
        environment=environment,
        secure=auth_refresh_cookie_secure,
        same_site=auth_refresh_cookie_samesite,
        cookie_names=(
            auth_refresh_cookie_name,
            auth_csrf_cookie_name,
        ),
    )
    _validate_auth_cookie_names(
        refresh_cookie_name=auth_refresh_cookie_name,
        csrf_cookie_name=auth_csrf_cookie_name,
    )

    return AppSettings(
        environment=environment,
        storage_dir=storage_dir,
        sqlite_path=sqlite_path,
        database_url=os.getenv(
            "DATABASE_URL",
            f"sqlite+aiosqlite:///{sqlite_path.as_posix()}",
        ),
        database_echo=_environment_bool("DATABASE_ECHO", default=False),
        database_pool_size=int(os.getenv("DATABASE_POOL_SIZE", "5")),
        database_max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "10")),
        database_pool_pre_ping=_environment_bool(
            "DATABASE_POOL_PRE_PING",
            default=True,
        ),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        default_llm_provider=os.getenv(
            "APP_DEFAULT_LLM_PROVIDER",
            "openrouter",
        ),
        default_analysis_model=os.getenv(
            "APP_DEFAULT_ANALYSIS_MODEL",
            "deepseek/deepseek-v4-flash",
        ),
        default_adaptation_model=os.getenv(
            "APP_DEFAULT_ADAPTATION_MODEL",
            "deepseek/deepseek-v4-flash",
        ),
        default_transcriber_provider=os.getenv(
            "APP_DEFAULT_TRANSCRIBER_PROVIDER",
            "whisper_local",
        ),
        default_transcriber_model=os.getenv(
            "APP_DEFAULT_TRANSCRIBER_MODEL",
            "small",
        ),
        max_duration_seconds=int(
            os.getenv("APP_MAX_DURATION_SECONDS", "600")
        ),
        request_timeout_seconds=int(
            os.getenv("APP_REQUEST_TIMEOUT_SECONDS", "300")
        ),
        celery_broker_url=os.getenv(
            "CELERY_BROKER_URL",
            "amqp://guest:guest@localhost:5672//",
        ),
        celery_queue_name=os.getenv("CELERY_QUEUE_NAME", "pipeline"),
        celery_task_soft_time_limit_seconds=int(
            os.getenv("CELERY_TASK_SOFT_TIME_LIMIT_SECONDS", "1800")
        ),
        celery_task_time_limit_seconds=int(
            os.getenv("CELERY_TASK_TIME_LIMIT_SECONDS", "1860")
        ),
        api_host=_environment_text(
            "APP_API_HOST",
            default="127.0.0.1",
        ),
        api_port=_positive_environment_int(
            "APP_API_PORT",
            default=8000,
        ),
        api_cors_origins=_environment_cors_origins(
            "APP_API_CORS_ORIGINS",
        ),
        public_web_url=_environment_text(
            "APP_PUBLIC_WEB_URL",
            default="http://localhost:8080",
        ),
        max_upload_bytes=_positive_environment_int(
            "APP_MAX_UPLOAD_BYTES",
            default=2 * 1024 * 1024 * 1024,
        ),
        api_upload_timeout_seconds=_positive_environment_int(
            "APP_API_UPLOAD_TIMEOUT_SECONDS",
            default=1800,
        ),
        accepted_input_media_types=_environment_csv(
            "APP_ACCEPTED_INPUT_MEDIA_TYPES",
            default=DEFAULT_ACCEPTED_INPUT_MEDIA_TYPES,
        ),
        auth_jwt_secret=_optional_auth_jwt_secret("AUTH_JWT_SECRET"),
        auth_jwt_algorithm=_auth_jwt_algorithm(),
        auth_issuer=_environment_text(
            "AUTH_ISSUER",
            default="kyrgstudio",
        ),
        auth_audience=_environment_text(
            "AUTH_AUDIENCE",
            default="kyrgstudio-api",
        ),
        auth_access_token_ttl_seconds=auth_access_token_ttl_seconds,
        auth_refresh_token_ttl_seconds=auth_refresh_token_ttl_seconds,
        auth_refresh_cookie_name=auth_refresh_cookie_name,
        auth_refresh_cookie_secure=auth_refresh_cookie_secure,
        auth_refresh_cookie_samesite=auth_refresh_cookie_samesite,
        auth_csrf_cookie_name=auth_csrf_cookie_name,
        auth_allowed_clock_skew_seconds=auth_allowed_clock_skew_seconds,
        google_client_ids=_google_client_ids("GOOGLE_CLIENT_IDS"),
        
        email_host=_environment_text(
            "EMAIL_HOST",
            default="smtp.gmail.com",
        ),
        email_port=_positive_environment_int(
            "EMAIL_PORT",
            default=465,
        ),
        email_username=os.getenv("EMAIL_USERNAME"),
        email_password=os.getenv("EMAIL_PASSWORD"),
        email_from=os.getenv("EMAIL_FROM"),
        email_from_name=_environment_text(
            "EMAIL_FROM_NAME",
            default="Kyrg Studio",
        ),
    )


def _environment_bool(name: str, *, default: bool) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    normalized_value = value.strip().lower()

    if normalized_value in {"1", "true", "yes", "on"}:
        return True

    if normalized_value in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"{name} must be a boolean environment variable.")


def _environment_text(name: str, *, default: str) -> str:
    value = os.getenv(name, default).strip()

    if not value:
        raise ValueError(f"{name} must not be blank.")

    return value


def _positive_environment_int(name: str, *, default: int) -> int:
    value = _environment_text(name, default=str(default))

    try:
        parsed_value = int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer.") from error

    if parsed_value <= 0:
        raise ValueError(f"{name} must be greater than zero.")

    return parsed_value


def _non_negative_environment_int(name: str, *, default: int) -> int:
    value = _environment_text(name, default=str(default))

    try:
        parsed_value = int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer.") from error

    if parsed_value < 0:
        raise ValueError(f"{name} must be zero or greater.")

    return parsed_value


def _environment_cors_origins(name: str) -> tuple[str, ...]:
    origins = _environment_csv(name, default=())

    if "*" in origins:
        raise ValueError(
            f"{name} must contain explicit origins; wildcard is not allowed."
        )

    return origins


def _environment_csv(
    name: str,
    *,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    values = tuple(
        dict.fromkeys(
            value.strip()
            for value in raw_value.split(",")
            if value.strip()
        )
    )

    return values


def _optional_auth_jwt_secret(name: str) -> str | None:
    raw_value = os.getenv(name)

    if raw_value is None:
        return None

    try:
        return _validate_auth_jwt_secret(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} is invalid: {error}") from error


def _validate_auth_jwt_secret(secret: str) -> str:
    if not secret.strip():
        raise ValueError("the secret must not be blank")

    if secret != secret.strip():
        raise ValueError(
            "the secret must not begin or end with whitespace"
        )

    if len(secret.encode("utf-8")) < MINIMUM_AUTH_JWT_SECRET_BYTES:
        raise ValueError(
            "the secret must contain at least "
            f"{MINIMUM_AUTH_JWT_SECRET_BYTES} bytes"
        )

    return secret


def _auth_jwt_algorithm() -> AuthJWTAlgorithm:
    value = _environment_text(
        "AUTH_JWT_ALGORITHM",
        default="HS256",
    ).upper()

    if value not in SUPPORTED_AUTH_JWT_ALGORITHMS:
        supported_values = ", ".join(SUPPORTED_AUTH_JWT_ALGORITHMS)
        raise ValueError(
            "AUTH_JWT_ALGORITHM must be one of: "
            f"{supported_values}."
        )

    return cast(AuthJWTAlgorithm, value)


def _auth_cookie_same_site() -> AuthCookieSameSite:
    value = _environment_text(
        "AUTH_REFRESH_COOKIE_SAMESITE",
        default="lax",
    ).lower()

    if value not in SUPPORTED_AUTH_COOKIE_SAME_SITE_VALUES:
        supported_values = ", ".join(
            SUPPORTED_AUTH_COOKIE_SAME_SITE_VALUES
        )
        raise ValueError(
            "AUTH_REFRESH_COOKIE_SAMESITE must be one of: "
            f"{supported_values}."
        )

    return cast(AuthCookieSameSite, value)


def _environment_cookie_name(name: str, *, default: str) -> str:
    value = _environment_text(name, default=default)

    if COOKIE_NAME_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} contains invalid cookie-name characters.")

    return value


def _google_client_ids(name: str) -> tuple[str, ...]:
    client_ids = _environment_csv(name, default=())

    if any("*" in client_id for client_id in client_ids):
        raise ValueError(f"{name} must not contain wildcard client IDs.")

    return client_ids


def _validate_auth_ttls(
    *,
    access_token_ttl_seconds: int,
    refresh_token_ttl_seconds: int,
    allowed_clock_skew_seconds: int,
) -> None:
    if refresh_token_ttl_seconds <= access_token_ttl_seconds:
        raise ValueError(
            "AUTH_REFRESH_TOKEN_TTL_SECONDS must be greater than "
            "AUTH_ACCESS_TOKEN_TTL_SECONDS."
        )

    if allowed_clock_skew_seconds >= access_token_ttl_seconds:
        raise ValueError(
            "AUTH_ALLOWED_CLOCK_SKEW_SECONDS must be lower than "
            "AUTH_ACCESS_TOKEN_TTL_SECONDS."
        )


def _validate_auth_cookie_security(
    *,
    environment: str,
    secure: bool,
    same_site: AuthCookieSameSite,
    cookie_names: tuple[str, ...],
) -> None:
    if _requires_secure_cookies(environment) and not secure:
        raise ValueError(
            "AUTH_REFRESH_COOKIE_SECURE must be enabled outside local and "
            "test environments."
        )

    if same_site == "none" and not secure:
        raise ValueError(
            "AUTH_REFRESH_COOKIE_SECURE must be enabled when "
            "AUTH_REFRESH_COOKIE_SAMESITE is 'none'."
        )

    if not secure and any(
        cookie_name.startswith(("__Host-", "__Secure-"))
        for cookie_name in cookie_names
    ):
        raise ValueError(
            "AUTH_REFRESH_COOKIE_SECURE must be enabled for cookies using "
            "the '__Host-' or '__Secure-' prefix."
        )


def _validate_auth_cookie_names(
    *,
    refresh_cookie_name: str,
    csrf_cookie_name: str,
) -> None:
    if refresh_cookie_name == csrf_cookie_name:
        raise ValueError(
            "AUTH_REFRESH_COOKIE_NAME and AUTH_CSRF_COOKIE_NAME must differ."
        )


def _requires_secure_cookies(environment: str) -> bool:
    return environment not in {"development", "dev", "local", "test", "testing"}
