# LLM Unit Test Plan

This document defines the unit tests that should cover `src/kyrg/llms`.
The goal is to validate retry behavior, provider normalization, token tracking,
and error handling without making real network calls.

## Scope

The unit test suite should cover:

- `LLMBase` structured-output retry orchestration.
- Structured output error formatting and retry prompt construction.
- OpenAI provider adapter behavior.
- Google Gemini provider adapter behavior.
- LangChain provider adapter behavior.
- Package-level public exports.

The suite must not call real provider APIs. All provider clients should be fake
objects or monkeypatched test doubles.

## Test Modules

### `test_base.py`

**Status:** Implemented.

Validate the shared `LLMBase` behavior.

Tests:

- `structured()` returns the first valid result from `_structured_once`.
- `structured()` retries when `_structured_once` raises `ValidationError`.
- `structured()` retries when `_structured_once` raises `StructuredOutputParsingError`.
- `structured()` raises `StructuredOutputError` after `max_attempts` failures.
- `structured()` preserves the original exception as `__cause__`.
- `structured()` sends a retry prompt containing the original prompt and formatted errors.
- `astructured()` mirrors the synchronous retry behavior.
- `astructured()` raises `StructuredOutputError` after async retry exhaustion.
- `_add_token()` stores the latest token values.
- `token_usage()` returns `input_tokens`, `output_tokens`, and `total_tokens`.

Important edge cases:

- `max_attempts=1` should not build a retry prompt.
- A later successful attempt should return the parsed object and stop retrying.
- Token usage currently stores the latest call, not an accumulated sum. Tests
  should reflect the current contract unless the implementation changes.

### `test_errors.py`

**Status:** Implemented.

Validate structured-output error utilities.

Tests:

- `format_validation_error()` converts Pydantic `ValidationError` into a list
  of dictionaries with `path`, `type`, `message`, `invalid_value`, and
  `constraints`.
- `format_validation_error()` joins nested paths using dot notation.
- `format_structured_error()` delegates to `format_validation_error()` for
  Pydantic validation errors.
- `format_structured_error()` converts `StructuredOutputParsingError` into a
  single parsing-error dictionary.
- `build_retry_prompt()` includes the original prompt.
- `build_retry_prompt()` includes the serialized validation errors.
- `build_retry_prompt()` includes explicit retry instructions.

Important edge cases:

- Missing required fields.
- Invalid literal or enum-like values.
- Nested list/index paths.

### `test_openai_llm.py`

**Status:** Implemented.

Validate the OpenAI Responses API adapter using fake clients.

Tests:

- `invoke()` calls `client.responses.create()` with model, input, and temperature.
- `invoke()` returns `response.output_text`.
- `invoke()` records token usage when `response.usage` exists.
- `invoke()` raises `RuntimeError` when the OpenAI client raises `OpenAIError`.
- `_structured_once()` calls `client.responses.parse()` with `text_format`.
- `_structured_once()` returns `response.output_parsed` when present.
- `_structured_once()` records structured token usage.
- `_structured_once()` raises `StructuredOutputParsingError` when
  `output_parsed` is `None`.
- `ainvoke()` mirrors `invoke()` using `async_client.responses.create()`.
- `_astructured_once()` mirrors `_structured_once()` using
  `async_client.responses.parse()`.

Important edge cases:

- `temperature=None` should still be forwarded as currently implemented.
- `usage=None` should not fail.
- The fake response should expose only the attributes used by the adapter.

### `test_gemini_llm.py`

**Status:** Implemented.

Validate the Google Gemini adapter using fake GenAI clients.

Tests:

- `invoke()` calls `client.models.generate_content()` with model, contents, and
  `GenerateContentConfig`.
- `invoke()` returns `response.text`.
- `invoke()` records `prompt_token_count` as input tokens.
- `invoke()` records `candidates_token_count` as output tokens.
- `invoke()` raises `RuntimeError` when Google raises `errors.APIError`.
- `invoke()` raises `RuntimeError` when `response.text` is `None`.
- `_structured_once()` returns `response.parsed` when it is already an instance
  of the output schema.
- `_structured_once()` validates a dictionary into the output schema.
- `_structured_once()` raises `StructuredOutputParsingError` when
  `response.parsed` is `None`.
- `_structured_once()` raises `StructuredOutputParsingError` when parsed output
  has an unsupported type.
- `ainvoke()` mirrors `invoke()` through `client.aio.models.generate_content()`.
- `_astructured_once()` mirrors `_structured_once()` through the async client.

Important edge cases:

- Usage fields may be `None`; they should count as zero.
- Structured output returned as dict should be validated by Pydantic.

### `test_langchain_llm.py`

**Status:** Implemented.

Validate the LangChain adapter using fake chat models and fake structured
runnables.

Tests:

- `invoke()` calls `llm.invoke(prompt)`.
- `invoke()` returns string content unchanged.
- `invoke()` converts non-string content to string.
- `invoke()` records token usage from `response.usage_metadata`.
- `invoke()` converts `OutputParserException` into
  `StructuredOutputParsingError`.
- `invoke()` wraps other exceptions in `RuntimeError`.
- `_structured_once()` calls `with_structured_output(output_schema, include_raw=True)`.
- `_structured_once()` invokes the structured runnable with the prompt.
- `_structured_once()` records token usage from `raw.usage_metadata`.
- `_structured_once()` raises `StructuredOutputParsingError` when
  `parsing_error` is present.
- `_structured_once()` returns parsed Pydantic instances unchanged.
- `_structured_once()` validates parsed dictionaries into the output schema.
- `_structured_once()` raises `StructuredOutputParsingError` for invalid parsed
  output types.
- `ainvoke()` mirrors `invoke()` using `llm.ainvoke()`.
- `_astructured_once()` mirrors `_structured_once()` using async structured
  runnable invocation.

Important edge cases:

- `usage_metadata=None` should not fail.
- Missing `raw`, `parsed`, or malformed response dictionaries should be wrapped
  as runtime errors according to the current implementation.

### `test_public_api.py`

**Status:** Implemented.

Validate the package exports in `src/kyrg/llms/__init__.py`.

Tests:

- `OpenAILLM` is exported from `kyrg.llms`.
- `LangChainLLM` is exported from `kyrg.llms`.
- `GoogleLLM` is exported from `kyrg.llms`.
- `LLMBase` is exported from `kyrg.llms`.
- `__all__` contains only intended public symbols.

## Suggested Fixtures

Use small Pydantic schemas for structured-output tests:

```python
class SimpleOutput(BaseModel):
    value: str
```

Use fake usage objects with only the attributes required by each adapter:

- OpenAI: `input_tokens`, `output_tokens`.
- Gemini: `prompt_token_count`, `candidates_token_count`.
- LangChain: `usage_metadata` dictionary.

Use fake provider clients instead of monkeypatching provider internals deeply.
Each fake should record calls and return minimal response objects.

## Execution

Recommended command:

```bash
.venv/bin/python -m pytest tests/unit/llms -q
```

These tests should be deterministic, fast, and safe to run in CI because they
must not use real API keys, external network calls, or real model providers.
