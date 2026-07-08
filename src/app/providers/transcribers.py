"""Transcriber provider factory for the application layer.

The app should not decide concrete transcriber classes inside pipeline, API,
CLI, or worker code. This module maps app configuration to the
``TranscriptorConfig`` consumed by the transcription workflow.
"""

from __future__ import annotations

from typing import Literal

from app.errors import ProviderConfigError
from app.settings import AppSettings
from kyrg.transcribers import (
    OpenAITranscriber,
    OpenRouterTranscriber,
    TranscriberBase,
    TranscriberWhisperLocal,
)
from kyrg.workflows.transcriber.schemas import TranscriptorConfig


TranscriberProvider = Literal["whisper_local", "openai", "openrouter"]

SUPPORTED_TRANSCRIBER_PROVIDERS: tuple[TranscriberProvider, ...] = (
    "whisper_local",
    "openai",
    "openrouter",
)


def build_transcriptor_config(
    *,
    provider: str,
    settings: AppSettings,
    temperature: float | None = None,
) -> TranscriptorConfig:
    """Build transcriber workflow configuration from app provider settings.

    Args:
        provider: Transcription provider requested by app input or settings.
        settings: Loaded application settings containing provider credentials.
        temperature: Optional transcription temperature.

    Returns:
        A ``TranscriptorConfig`` consumed by ``TranscriberWorkflow``.

    Raises:
        ProviderConfigError: If provider or required API key is invalid.
    """

    normalized_provider = _normalize_provider(provider)
    normalized_temperature = _normalize_temperature(temperature)

    if normalized_provider == "whisper_local":
        return _build_config(
            transcriptor=TranscriberWhisperLocal,
            temperature=normalized_temperature,
        )

    if normalized_provider == "openai":
        return _build_config(
            transcriptor=OpenAITranscriber,
            temperature=normalized_temperature,
            api_key=_required_api_key(
                settings.openai_api_key,
                provider=normalized_provider,
                setting_name="OPENAI_API_KEY",
            ),
        )

    if normalized_provider == "openrouter":
        return _build_config(
            transcriptor=OpenRouterTranscriber,
            temperature=normalized_temperature,
            api_key=_required_api_key(
                settings.openrouter_api_key,
                provider=normalized_provider,
                setting_name="OPENROUTER_API_KEY",
            ),
        )

    raise _unsupported_provider(normalized_provider)


def _build_config(
    *,
    transcriptor: type[TranscriberBase],
    temperature: float,
    api_key: str | None = None,
) -> TranscriptorConfig:
    return TranscriptorConfig(
        transcriptor=transcriptor,
        transcriptor_temperature=temperature,
        transcriptor_api_key=api_key,
    )


def _normalize_provider(provider: str) -> str:
    normalized_provider = str(provider or "").strip().lower()

    if not normalized_provider:
        raise ProviderConfigError(
            technical_message="Transcriber provider is required.",
            details={
                "provider": provider,
                "supported_providers": sorted(SUPPORTED_TRANSCRIBER_PROVIDERS),
            },
        )

    return normalized_provider


def _normalize_temperature(temperature: float | None) -> float:
    if temperature is None:
        return 0.0

    return float(temperature)


def _required_api_key(
    api_key: str | None,
    *,
    provider: str,
    setting_name: str,
) -> str:
    if api_key is None or api_key.strip() == "":
        raise ProviderConfigError(
            technical_message=(
                f"Missing API key for transcriber provider '{provider}'."
            ),
            details={
                "provider": provider,
                "setting": setting_name,
            },
        )

    return api_key


def _unsupported_provider(provider: str) -> ProviderConfigError:
    return ProviderConfigError(
        technical_message=f"Unsupported transcriber provider: {provider}",
        details={
            "provider": provider,
            "supported_providers": sorted(SUPPORTED_TRANSCRIBER_PROVIDERS),
        },
    )


__all__ = [
    "SUPPORTED_TRANSCRIBER_PROVIDERS",
    "TranscriberProvider",
    "build_transcriptor_config",
]
