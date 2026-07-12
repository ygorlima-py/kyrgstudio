from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class AppSettings:
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


def load_settings() -> AppSettings:
    storage_dir = Path(os.getenv("APP_STORAGE_DIR", ".storage"))
    sqlite_path = Path(
        os.getenv("APP_SQLITE_PATH", str(storage_dir / "app.sqlite"))
    )

    return AppSettings(
        environment=os.getenv("APP_ENV", "development"),
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

        default_llm_provider=os.getenv("APP_DEFAULT_LLM_PROVIDER", "openrouter"),
        default_analysis_model=os.getenv("APP_DEFAULT_ANALYSIS_MODEL", "deepseek/deepseek-v4-flash"),
        default_adaptation_model=os.getenv("APP_DEFAULT_ADAPTATION_MODEL", "deepseek/deepseek-v4-flash"),

        default_transcriber_provider=os.getenv("APP_DEFAULT_TRANSCRIBER_PROVIDER", "whisper_local"),
        default_transcriber_model=os.getenv("APP_DEFAULT_TRANSCRIBER_MODEL", "small"),

        max_duration_seconds=int(os.getenv("APP_MAX_DURATION_SECONDS", "300")),
        request_timeout_seconds=int(os.getenv("APP_REQUEST_TIMEOUT_SECONDS", "300")),

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
