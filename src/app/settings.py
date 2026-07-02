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


def load_settings() -> AppSettings:
    storage_dir = Path(os.getenv("APP_STORAGE_DIR", ".storage"))

    return AppSettings(
        environment=os.getenv("APP_ENV", "development"),
        storage_dir=storage_dir,
        sqlite_path=Path(os.getenv("APP_SQLITE_PATH", str(storage_dir / "app.sqlite"))),

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
    )