"""Unit tests for the shared LLM base retry and accounting behavior."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from kyrg.llms.base import LLMBase
from kyrg.llms.error import (
    StructuredOutputError,
    StructuredOutputParsingError,
)


SYSTEM_PROMPT = "Follow the structured-output contract."
PROMPT_CACHE_KEY = "test:structured-output"


class SimpleOutput(BaseModel):
    """Small schema used to validate structured output handling."""

    value: str


class QueueLLM(LLMBase):
    """LLM test double that returns or raises queued structured outcomes."""

    def __init__(
        self,
        outcomes: Sequence[SimpleOutput | Exception],
        *,
        max_attempts: int = 2,
    ) -> None:
        super().__init__(max_attempts=max_attempts)
        self._outcomes = list(outcomes)
        self.structured_prompts: list[str] = []
        self.astructured_prompts: list[str] = []
        self.system_prompts: list[str] = []
        self.prompt_cache_keys: list[str] = []

    def invoke(self, prompt: str) -> str:
        """Return the prompt for synchronous plain invocation tests."""
        return prompt

    async def ainvoke(self, prompt: str) -> str:
        """Return the prompt for asynchronous plain invocation tests."""
        return prompt

    def _next_outcome(self) -> SimpleOutput:
        outcome = self._outcomes.pop(0)

        if isinstance(outcome, Exception):
            raise outcome

        return outcome

    def _structured_once(
        self,
        prompt: str,
        system_prompt: str,
        prompt_cache_key: str,
        output_schema: type[SimpleOutput],
    ) -> SimpleOutput:
        """Record the prompt and return the next queued sync outcome."""
        self.structured_prompts.append(prompt)
        self.system_prompts.append(system_prompt)
        self.prompt_cache_keys.append(prompt_cache_key)
        return self._next_outcome()

    async def _astructured_once(
        self,
        prompt: str,
        system_prompt: str,
        prompt_cache_key: str,
        output_schema: type[SimpleOutput],
    ) -> SimpleOutput:
        """Record the prompt and return the next queued async outcome."""
        self.astructured_prompts.append(prompt)
        self.system_prompts.append(system_prompt)
        self.prompt_cache_keys.append(prompt_cache_key)
        return self._next_outcome()


def _validation_error() -> ValidationError:
    """Create a real Pydantic validation error for retry tests."""
    with pytest.raises(ValidationError) as exc_info:
        SimpleOutput.model_validate({})

    return exc_info.value


def test_structured_returns_first_valid_result() -> None:
    """Return the first valid structured result without retrying."""
    expected = SimpleOutput(value="ok")
    llm = QueueLLM([expected], max_attempts=3)

    result = llm.structured(
        "original prompt",
        SYSTEM_PROMPT,
        PROMPT_CACHE_KEY,
        SimpleOutput,
    )

    assert result is expected
    assert llm.structured_prompts == ["original prompt"]
    assert llm.system_prompts == [SYSTEM_PROMPT]
    assert llm.prompt_cache_keys == [PROMPT_CACHE_KEY]


def test_structured_retries_validation_error_with_retry_prompt() -> None:
    """Retry validation errors with schema feedback in the next prompt."""
    expected = SimpleOutput(value="fixed")
    llm = QueueLLM([_validation_error(), expected], max_attempts=2)

    result = llm.structured(
        "extract value",
        SYSTEM_PROMPT,
        PROMPT_CACHE_KEY,
        SimpleOutput,
    )

    assert result is expected
    assert llm.structured_prompts[0] == "extract value"
    assert "<schema_validation_retry>" in llm.structured_prompts[1]
    assert "extract value" in llm.structured_prompts[1]
    assert "Field required" in llm.structured_prompts[1]
    assert llm.system_prompts == [SYSTEM_PROMPT, SYSTEM_PROMPT]
    assert llm.prompt_cache_keys == [PROMPT_CACHE_KEY, PROMPT_CACHE_KEY]


def test_structured_retries_parsing_error_with_retry_prompt() -> None:
    """Retry provider parsing errors using the shared retry prompt."""
    expected = SimpleOutput(value="fixed")
    llm = QueueLLM(
        [StructuredOutputParsingError("invalid json"), expected],
        max_attempts=2,
    )

    result = llm.structured(
        "extract value",
        SYSTEM_PROMPT,
        PROMPT_CACHE_KEY,
        SimpleOutput,
    )

    assert result is expected
    assert "parsing_error" in llm.structured_prompts[1]
    assert "invalid json" in llm.structured_prompts[1]


def test_structured_raises_after_retry_exhaustion_and_preserves_cause() -> None:
    """Raise StructuredOutputError with the final structured failure as cause."""
    last_error = StructuredOutputParsingError("still invalid")
    llm = QueueLLM([_validation_error(), last_error], max_attempts=2)

    with pytest.raises(StructuredOutputError) as exc_info:
        llm.structured(
            "extract value",
            SYSTEM_PROMPT,
            PROMPT_CACHE_KEY,
            SimpleOutput,
        )

    assert "SimpleOutput remained invalid after 2 attempts" in str(exc_info.value)
    assert exc_info.value.__cause__ is last_error
    assert len(llm.structured_prompts) == 2


def test_structured_with_one_attempt_does_not_build_retry_prompt() -> None:
    """Avoid retry prompt construction when only one attempt is allowed."""
    llm = QueueLLM([StructuredOutputParsingError("invalid")], max_attempts=1)

    with pytest.raises(StructuredOutputError):
        llm.structured(
            "original only",
            SYSTEM_PROMPT,
            PROMPT_CACHE_KEY,
            SimpleOutput,
        )

    assert llm.structured_prompts == ["original only"]


def test_astructured_mirrors_sync_retry_behavior() -> None:
    """Retry async structured calls and return the later valid result."""
    expected = SimpleOutput(value="async-fixed")
    llm = QueueLLM([_validation_error(), expected], max_attempts=2)

    result = asyncio.run(
        llm.astructured(
            "async prompt",
            SYSTEM_PROMPT,
            PROMPT_CACHE_KEY,
            SimpleOutput,
        )
    )

    assert result is expected
    assert llm.astructured_prompts[0] == "async prompt"
    assert "<schema_validation_retry>" in llm.astructured_prompts[1]


def test_astructured_raises_after_retry_exhaustion() -> None:
    """Raise StructuredOutputError when async structured retries fail."""
    last_error = StructuredOutputParsingError("async invalid")
    llm = QueueLLM([_validation_error(), last_error], max_attempts=2)

    with pytest.raises(StructuredOutputError) as exc_info:
        asyncio.run(
            llm.astructured(
                "async prompt",
                SYSTEM_PROMPT,
                PROMPT_CACHE_KEY,
                SimpleOutput,
            )
        )

    assert exc_info.value.__cause__ is last_error
    assert len(llm.astructured_prompts) == 2


def test_token_usage_returns_latest_values_and_total() -> None:
    """Report the latest token usage values plus their total."""
    llm = QueueLLM([])

    llm._add_token(input_tokens=10, output_tokens=4)
    llm._add_token(input_tokens=3, output_tokens=2)

    assert llm.token_usage() == {
        "input_tokens": 3,
        "output_tokens": 2,
        "total_tokens": 5,
    }
