"""Unit tests for the Google Gemini LLM provider adapter."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest
from google.genai import errors
from pydantic import BaseModel

from kyrg.llms.base import LLMBase
from kyrg.llms.error import StructuredOutputParsingError
from kyrg.llms.gemini_llm import GoogleLLM


SYSTEM_PROMPT = "Follow the structured-output contract."
PROMPT_CACHE_KEY = "test:gemini-structured"


class SimpleOutput(BaseModel):
    """Small schema used by Gemini structured-output tests."""

    value: str


@dataclass(frozen=True)
class Usage:
    """Minimal Gemini usage metadata object."""

    prompt_token_count: int | None = None
    candidates_token_count: int | None = None


class GeminiResponse:
    """Minimal Gemini response object."""

    def __init__(
        self,
        *,
        text: str | None = None,
        parsed: Any = None,
        usage_metadata: Usage | None = None,
    ) -> None:
        self.text = text
        self.parsed = parsed
        self.usage_metadata = usage_metadata


class SyncModels:
    """Fake synchronous Gemini models resource."""

    def __init__(self, response: GeminiResponse | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def generate_content(self, **kwargs: Any) -> GeminiResponse:
        """Record generation calls and return or raise the configured result."""
        self.calls.append(kwargs)

        if self.error is not None:
            raise self.error

        assert self.response is not None
        return self.response


class AsyncModels:
    """Fake asynchronous Gemini models resource."""

    def __init__(self, response: GeminiResponse) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def generate_content(self, **kwargs: Any) -> GeminiResponse:
        """Record async generation calls and return the configured result."""
        self.calls.append(kwargs)
        return self.response


class Client:
    """Fake Gemini client exposing sync and async model resources."""

    def __init__(
        self,
        *,
        models: SyncModels | None = None,
        async_models: AsyncModels | None = None,
    ) -> None:
        self.models = models
        self.aio = type("Aio", (), {"models": async_models})()


def _llm(client: Client, *, temperature: float | None = None) -> GoogleLLM:
    """Create a GoogleLLM without constructing the real SDK client."""
    llm = GoogleLLM.__new__(GoogleLLM)
    LLMBase.__init__(llm)
    llm.client = client
    llm.model = "gemini-test"
    llm.temperature = temperature
    llm.system_prompt = None
    return llm


def test_invoke_calls_generate_content_and_records_tokens() -> None:
    """Invoke should call Gemini and map usage metadata to token usage."""
    models = SyncModels(
        GeminiResponse(
            text="hello",
            usage_metadata=Usage(prompt_token_count=4, candidates_token_count=6),
        )
    )
    llm = _llm(Client(models=models), temperature=0.3)

    result = llm.invoke("prompt")

    assert result == "hello"
    assert models.calls[0]["model"] == "gemini-test"
    assert models.calls[0]["contents"] == "prompt"
    assert "config" in models.calls[0]
    assert llm.token_usage() == {
        "input_tokens": 4,
        "output_tokens": 6,
        "total_tokens": 10,
    }


def test_invoke_wraps_api_errors_and_rejects_missing_text() -> None:
    """Provider errors and empty text should become RuntimeError."""
    api_error = errors.APIError(400, {"error": "boom"})
    llm = _llm(Client(models=SyncModels(error=api_error)))

    with pytest.raises(RuntimeError, match="Error calling Google LLM provider"):
        llm.invoke("prompt")

    missing_text = _llm(Client(models=SyncModels(GeminiResponse(text=None))))

    with pytest.raises(RuntimeError, match="Google returned no text output"):
        missing_text.invoke("prompt")


def test_structured_once_accepts_instance_and_dict_outputs() -> None:
    """Structured Gemini output should accept schema instances and dictionaries."""
    instance = SimpleOutput(value="instance")
    instance_llm = _llm(
        Client(
            models=SyncModels(
                GeminiResponse(
                    parsed=instance,
                    usage_metadata=Usage(prompt_token_count=None, candidates_token_count=None),
                )
            )
        )
    )

    assert (
        instance_llm._structured_once(
            "prompt",
            SYSTEM_PROMPT,
            PROMPT_CACHE_KEY,
            SimpleOutput,
        )
        is instance
    )
    assert instance_llm.token_usage() == {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }

    dict_llm = _llm(Client(models=SyncModels(GeminiResponse(parsed={"value": "dict"}))))

    assert dict_llm._structured_once(
        "prompt",
        SYSTEM_PROMPT,
        PROMPT_CACHE_KEY,
        SimpleOutput,
    ) == SimpleOutput(value="dict")


def test_structured_once_rejects_missing_or_invalid_parsed_output() -> None:
    """Structured Gemini output must be present and schema-compatible."""
    missing = _llm(Client(models=SyncModels(GeminiResponse(parsed=None))))

    with pytest.raises(StructuredOutputParsingError, match="no structured output"):
        missing._structured_once(
            "prompt",
            SYSTEM_PROMPT,
            PROMPT_CACHE_KEY,
            SimpleOutput,
        )

    invalid = _llm(Client(models=SyncModels(GeminiResponse(parsed=["bad"]))))

    with pytest.raises(StructuredOutputParsingError, match="invalid format"):
        invalid._structured_once(
            "prompt",
            SYSTEM_PROMPT,
            PROMPT_CACHE_KEY,
            SimpleOutput,
        )


def test_async_methods_mirror_sync_behavior() -> None:
    """Async Gemini methods should use client.aio and normalize results."""
    async_models = AsyncModels(
        GeminiResponse(
            text="async text",
            parsed={"value": "async parsed"},
            usage_metadata=Usage(prompt_token_count=8, candidates_token_count=1),
        )
    )
    llm = _llm(Client(async_models=async_models))

    text = asyncio.run(llm.ainvoke("async prompt"))
    parsed = asyncio.run(
        llm._astructured_once(
            "structured prompt",
            SYSTEM_PROMPT,
            PROMPT_CACHE_KEY,
            SimpleOutput,
        )
    )

    assert text == "async text"
    assert parsed == SimpleOutput(value="async parsed")
    assert async_models.calls[0]["contents"] == "async prompt"
    assert async_models.calls[1]["contents"] == "structured prompt"
    assert async_models.calls[1]["config"].system_instruction == SYSTEM_PROMPT
    assert llm.token_usage()["total_tokens"] == 9
