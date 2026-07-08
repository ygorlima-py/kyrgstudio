"""LLM provider factory for the application layer.

The app should not instantiate concrete LLM adapters directly inside pipeline,
API, CLI, or worker code. This module centralizes provider selection, API key
validation, and provider-specific adapter construction.
"""

from __future__ import annotations

from typing import Literal

from app.errors import ProviderConfigError
from app.settings import AppSettings
from kyrg.llms import GoogleLLM, LLMBase, OpenAILLM, OpenRouterLLM


LLMProvider = Literal["openai", "gemini", "openrouter"]

SUPPORTED_LLM_PROVIDERS: tuple[LLMProvider, ...] = (
    "openai",
    "gemini",
    "openrouter",
)


def build_llm(
    *,
    provider: str,
    model: str,
    settings: AppSettings,
    temperature: float | None = None,
) -> LLMBase:
    """Build a configured LLM adapter for app workflows.

    Args:
        provider: Provider identifier requested by the app input or settings.
        model: Provider model name.
        settings: Loaded application settings containing provider credentials.
        temperature: Optional sampling temperature.

    Returns:
        A concrete ``LLMBase`` implementation ready for workflow actions.

    Raises:
        ProviderConfigError: If provider, model, or required API key is invalid.
    """

    normalized_provider = _normalize_provider(provider)
    normalized_model = _required_model(model, provider=normalized_provider)

    if normalized_provider == "openai":
        return OpenAILLM(
            api_key=_required_api_key(
                settings.openai_api_key,
                provider=normalized_provider,
                setting_name="OPENAI_API_KEY",
            ),
            model=normalized_model,
            temperature=temperature,
        )

    if normalized_provider == "gemini":
        return GoogleLLM(
            api_key=_required_api_key(
                settings.gemini_api_key,
                provider=normalized_provider,
                setting_name="GEMINI_API_KEY",
            ),
            model=normalized_model,
            temperature=temperature,
        )

    if normalized_provider == "openrouter":
        return OpenRouterLLM(
            api_key=_required_api_key(
                settings.openrouter_api_key,
                provider=normalized_provider,
                setting_name="OPENROUTER_API_KEY",
            ),
            model=normalized_model,
            temperature=temperature,
        )

    raise _unsupported_provider(normalized_provider)


def _normalize_provider(provider: str) -> str:
    normalized_provider = str(provider or "").strip().lower()

    if not normalized_provider:
        raise ProviderConfigError(
            technical_message="LLM provider is required.",
            details={
                "provider": provider,
                "supported_providers": sorted(SUPPORTED_LLM_PROVIDERS),
            },
        )

    return normalized_provider


def _required_model(model: str, *, provider: str) -> str:
    normalized_model = str(model or "").strip()

    if not normalized_model:
        raise ProviderConfigError(
            technical_message="LLM model is required.",
            details={"provider": provider, "model": model},
        )

    return normalized_model


def _required_api_key(
    api_key: str | None,
    *,
    provider: str,
    setting_name: str,
) -> str:
    if api_key is None or api_key.strip() == "":
        raise ProviderConfigError(
            technical_message=(
                f"Missing API key for LLM provider '{provider}'."
            ),
            details={
                "provider": provider,
                "setting": setting_name,
            },
        )

    return api_key


def _unsupported_provider(provider: str) -> ProviderConfigError:
    return ProviderConfigError(
        technical_message=f"Unsupported LLM provider: {provider}",
        details={
            "provider": provider,
            "supported_providers": sorted(SUPPORTED_LLM_PROVIDERS),
        },
    )


__all__ = [
    "LLMProvider",
    "SUPPORTED_LLM_PROVIDERS",
    "build_llm",
]
