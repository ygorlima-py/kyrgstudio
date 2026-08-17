"""Unit tests for the OpenAI LLM provider adapter."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, cast

import pytest
from openai import OpenAIError
from pydantic import BaseModel

from kyrg.llms.base import LLMBase
from kyrg.llms.error import StructuredOutputParsingError
from kyrg.llms.openai_llm import OpenAILLM


SYSTEM_PROMPT = "Follow the structured-output contract."
PROMPT_CACHE_KEY = "test:openai-structured"


class SimpleOutput(BaseModel):
    """Small structured response schema used by OpenAI adapter tests."""

    value: str


@dataclass(frozen=True)
class Usage:
    """Minimal OpenAI usage object."""

    input_tokens: int
    output_tokens: int


class OpenAIResponse:
    """Minimal response object for OpenAI Responses API tests."""

    def __init__(
        self,
        *,
        output_text: str = "",
        output_parsed: Any = None,
        usage: Usage | None = None,
    ) -> None:
        self.output_text = output_text
        self.output_parsed = output_parsed
        self.usage = usage


class SyncResponses:
    """Fake synchronous OpenAI responses resource."""

    def __init__(
        self,
        *,
        create_response: OpenAIResponse | None = None,
        parse_response: OpenAIResponse | None = None,
        create_error: Exception | None = None,
        parse_error: Exception | None = None,
    ) -> None:
        self.create_response = create_response
        self.parse_response = parse_response
        self.create_error = create_error
        self.parse_error = parse_error
        self.create_calls: list[dict[str, Any]] = []
        self.parse_calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> OpenAIResponse:
        """Record a create call and return or raise the configured outcome."""
        self.create_calls.append(kwargs)

        if self.create_error is not None:
            raise self.create_error

        assert self.create_response is not None
        return self.create_response

    def parse(self, **kwargs: Any) -> OpenAIResponse:
        """Record a parse call and return or raise the configured outcome."""
        self.parse_calls.append(kwargs)

        if self.parse_error is not None:
            raise self.parse_error

        assert self.parse_response is not None
        return self.parse_response


class AsyncResponses:
    """Fake asynchronous OpenAI responses resource."""

    def __init__(
        self,
        *,
        create_response: OpenAIResponse | None = None,
        parse_response: OpenAIResponse | None = None,
    ) -> None:
        self.create_response = create_response
        self.parse_response = parse_response
        self.create_calls: list[dict[str, Any]] = []
        self.parse_calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> OpenAIResponse:
        """Record an async create call and return the configured response."""
        self.create_calls.append(kwargs)
        assert self.create_response is not None
        return self.create_response

    async def parse(self, **kwargs: Any) -> OpenAIResponse:
        """Record an async parse call and return the configured response."""
        self.parse_calls.append(kwargs)
        assert self.parse_response is not None
        return self.parse_response


class Client:
    """Fake OpenAI client exposing only the responses resource."""

    def __init__(self, responses: SyncResponses | AsyncResponses) -> None:
        self.responses = responses


def _llm(
    *,
    client: Client | None = None,
    async_client: Client | None = None,
    temperature: float | None = None,
) -> OpenAILLM:
    """Create an OpenAILLM without constructing real SDK clients."""
    llm = OpenAILLM.__new__(OpenAILLM)
    LLMBase.__init__(llm)
    llm.client = cast(Any, client)
    llm.async_client = cast(Any, async_client)
    llm.model = "gpt-test"
    llm.temperature = temperature
    return llm


def test_invoke_calls_responses_create_and_records_tokens() -> None:
    """Invoke should call the Responses API and store usage metadata."""
    responses = SyncResponses(
        create_response=OpenAIResponse(
            output_text="plain text",
            usage=Usage(input_tokens=7, output_tokens=3),
        )
    )
    llm = _llm(client=Client(responses), temperature=None)

    result = llm.invoke("hello")

    assert result == "plain text"
    assert responses.create_calls == [
        {
            "model": "gpt-test",
            "input": "hello",
            "temperature": None,
        }
    ]
    assert llm.token_usage() == {
        "input_tokens": 7,
        "output_tokens": 3,
        "total_tokens": 10,
    }


def test_invoke_wraps_openai_errors() -> None:
    """Provider OpenAIError should be exposed as RuntimeError."""
    responses = SyncResponses(create_error=OpenAIError("boom"))
    llm = _llm(client=Client(responses))

    with pytest.raises(RuntimeError, match="Error calling OpenAI LLM provider"):
        llm.invoke("hello")


def test_structured_once_calls_parse_and_returns_parsed_object() -> None:
    """Structured calls should request text_format and return parsed output."""
    parsed = SimpleOutput(value="ok")
    responses = SyncResponses(
        parse_response=OpenAIResponse(
            output_parsed=parsed,
            usage=Usage(input_tokens=11, output_tokens=5),
        )
    )
    llm = _llm(client=Client(responses), temperature=0.2)

    result = llm._structured_once(
        "prompt",
        SYSTEM_PROMPT,
        PROMPT_CACHE_KEY,
        SimpleOutput,
    )

    assert result is parsed
    assert responses.parse_calls == [
        {
            "model": "gpt-test",
            "input": "prompt",
            "instructions": SYSTEM_PROMPT,
            "prompt_cache_key": PROMPT_CACHE_KEY,
            "text_format": SimpleOutput,
            "temperature": 0.2,
        }
    ]
    assert llm.token_usage()["total_tokens"] == 16


def test_structured_once_rejects_missing_parsed_output() -> None:
    """Missing parsed output should become a structured parsing error."""
    responses = SyncResponses(parse_response=OpenAIResponse(output_parsed=None))
    llm = _llm(client=Client(responses))

    with pytest.raises(StructuredOutputParsingError):
        llm._structured_once(
            "prompt",
            SYSTEM_PROMPT,
            PROMPT_CACHE_KEY,
            SimpleOutput,
        )


def test_ainvoke_and_astructured_once_use_async_client() -> None:
    """Async methods should mirror sync behavior through async client calls."""
    responses = AsyncResponses(
        create_response=OpenAIResponse(
            output_text="async text",
            usage=Usage(input_tokens=2, output_tokens=4),
        ),
        parse_response=OpenAIResponse(
            output_parsed=SimpleOutput(value="async parsed"),
            usage=Usage(input_tokens=5, output_tokens=6),
        ),
    )
    llm = _llm(async_client=Client(responses), temperature=0.0)

    text = asyncio.run(llm.ainvoke("hello async"))
    parsed = asyncio.run(
        llm._astructured_once(
            "structured async",
            SYSTEM_PROMPT,
            PROMPT_CACHE_KEY,
            SimpleOutput,
        )
    )

    assert text == "async text"
    assert parsed == SimpleOutput(value="async parsed")
    assert responses.create_calls[0]["temperature"] == 0.0
    assert responses.parse_calls[0]["instructions"] == SYSTEM_PROMPT
    assert responses.parse_calls[0]["prompt_cache_key"] == PROMPT_CACHE_KEY
    assert responses.parse_calls[0]["text_format"] is SimpleOutput
    assert llm.token_usage() == {
        "input_tokens": 5,
        "output_tokens": 6,
        "total_tokens": 11,
    }
