"""Unit tests for the public LLM package exports."""

from __future__ import annotations

import kyrg.llms as llms
from kyrg.llms.base import LLMBase
from kyrg.llms.gemini_llm import GoogleLLM
from kyrg.llms.langchain_llm import LangChainLLM
from kyrg.llms.openai_llm import OpenAILLM
from kyrg.llms.openrouter_llm import OpenRouterLLM


def test_public_llm_exports_are_available() -> None:
    """Expose the supported provider adapters from the package root."""
    assert llms.OpenAILLM is OpenAILLM
    assert llms.OpenRouterLLM is OpenRouterLLM
    assert llms.LangChainLLM is LangChainLLM
    assert llms.GoogleLLM is GoogleLLM
    assert llms.LLMBase is LLMBase


def test_all_contains_only_public_symbols() -> None:
    """Keep the package root API explicit and minimal."""
    assert set(llms.__all__) == {
        "OpenAILLM",
        "OpenRouterLLM",
        "LangChainLLM",
        "GoogleLLM",
        "LLMBase",
    }
