"""Unit tests for the LangChain LLM provider adapter."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from langchain_core.exceptions import OutputParserException
from pydantic import BaseModel

from kyrg.llms.error import StructuredOutputParsingError
from kyrg.llms.langchain_llm import LangChainLLM


SYSTEM_PROMPT = "Follow the structured-output contract."
PROMPT_CACHE_KEY = "test:langchain-structured"


class SimpleOutput(BaseModel):
    """Small schema used by LangChain structured-output tests."""

    value: str


class Message:
    """Minimal LangChain message response."""

    def __init__(self, content: Any, usage_metadata: dict[str, int] | None = None) -> None:
        self.content = content
        self.usage_metadata = usage_metadata


class RawMessage:
    """Minimal raw message carrying structured-output token usage."""

    def __init__(self, usage_metadata: dict[str, int] | None = None) -> None:
        self.usage_metadata = usage_metadata


class StructuredRunnable:
    """Fake structured LangChain runnable."""

    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.invoke_calls: list[Any] = []
        self.ainvoke_calls: list[Any] = []

    def invoke(self, prompt: Any) -> dict[str, Any]:
        """Record sync invocation and return the structured response."""
        self.invoke_calls.append(prompt)
        return self.response

    async def ainvoke(self, prompt: Any) -> dict[str, Any]:
        """Record async invocation and return the structured response."""
        self.ainvoke_calls.append(prompt)
        return self.response


class FakeChatModel:
    """Fake LangChain chat model with plain and structured calls."""

    def __init__(
        self,
        *,
        response: Message | None = None,
        async_response: Message | None = None,
        structured: StructuredRunnable | None = None,
        invoke_error: Exception | None = None,
    ) -> None:
        self.response = response
        self.async_response = async_response
        self.structured = structured
        self.invoke_error = invoke_error
        self.invoke_calls: list[str] = []
        self.ainvoke_calls: list[str] = []
        self.with_structured_output_calls: list[dict[str, Any]] = []

    def invoke(self, prompt: str) -> Message:
        """Record sync prompt calls and return or raise the configured result."""
        self.invoke_calls.append(prompt)

        if self.invoke_error is not None:
            raise self.invoke_error

        assert self.response is not None
        return self.response

    async def ainvoke(self, prompt: str) -> Message:
        """Record async prompt calls and return or raise the configured result."""
        self.ainvoke_calls.append(prompt)

        if self.invoke_error is not None:
            raise self.invoke_error

        assert self.async_response is not None
        return self.async_response

    def with_structured_output(
        self,
        output_schema: type[SimpleOutput],
        *,
        include_raw: bool,
    ) -> StructuredRunnable:
        """Record structured-output configuration and return a fake runnable."""
        self.with_structured_output_calls.append(
            {"output_schema": output_schema, "include_raw": include_raw}
        )
        assert self.structured is not None
        return self.structured


def test_invoke_returns_string_content_and_records_usage() -> None:
    """Plain invoke should return string content and map usage metadata."""
    model = FakeChatModel(
        response=Message(
            "hello",
            usage_metadata={"input_tokens": 3, "output_tokens": 2},
        )
    )
    llm = LangChainLLM(model)  # type: ignore[arg-type]

    result = llm.invoke("prompt")

    assert result == "hello"
    assert model.invoke_calls == ["prompt"]
    assert llm.token_usage() == {
        "input_tokens": 3,
        "output_tokens": 2,
        "total_tokens": 5,
    }


def test_invoke_converts_non_string_content_and_handles_errors() -> None:
    """Plain invoke should stringify content and normalize provider errors."""
    llm = LangChainLLM(FakeChatModel(response=Message(["a", "b"])))  # type: ignore[arg-type]

    assert llm.invoke("prompt") == "['a', 'b']"

    parsing = LangChainLLM(  # type: ignore[arg-type]
        FakeChatModel(invoke_error=OutputParserException("bad parse"))
    )
    with pytest.raises(StructuredOutputParsingError):
        parsing.invoke("prompt")

    runtime = LangChainLLM(FakeChatModel(invoke_error=ValueError("boom")))  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="Error calling LangChain LLM provider"):
        runtime.invoke("prompt")


def test_structured_once_uses_structured_runnable_and_returns_instance() -> None:
    """Structured sync calls should configure LangChain and return parsed objects."""
    parsed = SimpleOutput(value="ok")
    structured = StructuredRunnable(
        {
            "raw": RawMessage({"input_tokens": 4, "output_tokens": 5}),
            "parsed": parsed,
            "parsing_error": None,
        }
    )
    model = FakeChatModel(structured=structured)
    llm = LangChainLLM(model)  # type: ignore[arg-type]

    result = llm._structured_once(
        "structured prompt",
        SYSTEM_PROMPT,
        PROMPT_CACHE_KEY,
        SimpleOutput,
    )

    assert result is parsed
    assert model.with_structured_output_calls == [
        {"output_schema": SimpleOutput, "include_raw": True}
    ]
    assert [message.content for message in structured.invoke_calls[0]] == [
        SYSTEM_PROMPT,
        "structured prompt",
    ]
    assert llm.token_usage()["total_tokens"] == 9


def test_structured_once_validates_dict_and_rejects_parser_or_invalid_output() -> None:
    """Structured sync calls should validate dicts and reject bad parse results."""
    dict_llm = LangChainLLM(  # type: ignore[arg-type]
        FakeChatModel(
            structured=StructuredRunnable(
                {
                    "raw": RawMessage(None),
                    "parsed": {"value": "from dict"},
                    "parsing_error": None,
                }
            )
        )
    )
    assert dict_llm._structured_once(
        "prompt",
        SYSTEM_PROMPT,
        PROMPT_CACHE_KEY,
        SimpleOutput,
    ) == SimpleOutput(value="from dict")

    parser_error = OutputParserException("bad structured parse")
    parsing_llm = LangChainLLM(  # type: ignore[arg-type]
        FakeChatModel(
            structured=StructuredRunnable(
                {
                    "raw": RawMessage(None),
                    "parsed": None,
                    "parsing_error": parser_error,
                }
            )
        )
    )
    with pytest.raises(StructuredOutputParsingError):
        parsing_llm._structured_once(
            "prompt",
            SYSTEM_PROMPT,
            PROMPT_CACHE_KEY,
            SimpleOutput,
        )

    invalid_llm = LangChainLLM(  # type: ignore[arg-type]
        FakeChatModel(
            structured=StructuredRunnable(
                {
                    "raw": RawMessage(None),
                    "parsed": ["bad"],
                    "parsing_error": None,
                }
            )
        )
    )
    with pytest.raises(StructuredOutputParsingError, match="invalid format"):
        invalid_llm._structured_once(
            "prompt",
            SYSTEM_PROMPT,
            PROMPT_CACHE_KEY,
            SimpleOutput,
        )


def test_structured_once_wraps_malformed_response_as_runtime_error() -> None:
    """Malformed LangChain structured dictionaries follow current runtime behavior."""
    llm = LangChainLLM(  # type: ignore[arg-type]
        FakeChatModel(structured=StructuredRunnable({"parsed": SimpleOutput(value="x")}))
    )

    with pytest.raises(RuntimeError, match="Error calling LangChain LLM provider"):
        llm._structured_once(
            "prompt",
            SYSTEM_PROMPT,
            PROMPT_CACHE_KEY,
            SimpleOutput,
        )


def test_async_methods_mirror_sync_behavior() -> None:
    """Async invoke and structured calls should mirror sync normalization."""
    structured = StructuredRunnable(
        {
            "raw": RawMessage({"input_tokens": 8, "output_tokens": 1}),
            "parsed": {"value": "async structured"},
            "parsing_error": None,
        }
    )
    model = FakeChatModel(
        async_response=Message(
            "async text",
            usage_metadata={"input_tokens": 2, "output_tokens": 3},
        ),
        structured=structured,
    )
    llm = LangChainLLM(model)  # type: ignore[arg-type]

    text = asyncio.run(llm.ainvoke("plain async"))
    parsed = asyncio.run(
        llm._astructured_once(
            "structured async",
            SYSTEM_PROMPT,
            PROMPT_CACHE_KEY,
            SimpleOutput,
        )
    )

    assert text == "async text"
    assert parsed == SimpleOutput(value="async structured")
    assert model.ainvoke_calls == ["plain async"]
    assert [message.content for message in structured.ainvoke_calls[0]] == [
        SYSTEM_PROMPT,
        "structured async",
    ]
    assert llm.token_usage() == {
        "input_tokens": 8,
        "output_tokens": 1,
        "total_tokens": 9,
    }
