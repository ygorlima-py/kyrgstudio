"""OpenRouter LLM adapter.

OpenRouter exposes an OpenAI-compatible API. This adapter reuses the existing
``OpenAILLM`` implementation and changes only the provider base URL.
"""

from kyrg.llms.openai_llm import OpenAILLM


class OpenRouterLLM(OpenAILLM):
    """LLM adapter backed by OpenRouter's OpenAI-compatible API."""

    BASE_URL = "https://openrouter.ai/api/v1"


__all__ = ["OpenRouterLLM"]
