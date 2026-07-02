"""Google Gemini implementation of the project LLM interface.

This module adapts the Google GenAI SDK to ``LLMBase``. It normalizes text
generation, structured JSON/Pydantic responses, async calls, provider errors,
and latest-call token usage into the same contract used by the rest of the
workflow layer.
"""

from typing import Optional

from google import genai
from google.genai import errors, types
from loguru import logger

from kyrg.llms.base import LLMBase, OutputT
from kyrg.llms.error import StructuredOutputParsingError


class GoogleLLM(LLMBase):
    """LLM adapter backed by the Google GenAI SDK.

    The adapter calls ``models.generate_content`` for both plain text and
    structured output. Structured calls request JSON output through
    ``GenerateContentConfig`` and then normalize ``response.parsed`` into the
    expected Pydantic schema.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        ):
        """Create a Google GenAI client.

        Args:
            api_key: Google API key used by ``genai.Client``.
            model: Gemini model name.
            temperature: Optional sampling temperature forwarded to generation
                config.
            system_prompt: Optional system instruction used by plain text
                generation.
        """
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.system_prompt = system_prompt
        super().__init__()

    def invoke(self, prompt: str) -> str:
        """Generate plain text with ``models.generate_content``.

        Args:
            prompt: Complete input prompt.

        Returns:
            ``response.text`` from the Google SDK.

        Raises:
            RuntimeError: If the Google SDK raises ``errors.APIError`` or if no
                text output is returned.
        """
        logger.info(f"Calling Google LLM provider: model={self.model}, method=invoke")

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self.temperature,
                    system_instruction=self.system_prompt,
                )
            )
        except errors.APIError as error:
            logger.exception(f"Google LLM provider failed: model={self.model}, method=invoke")
            raise RuntimeError(f"Error calling Google LLM provider: {error}") from error

        usage = response.usage_metadata
        if usage is not None:
            self._add_token(
                input_tokens=usage.prompt_token_count or 0,
                output_tokens=usage.candidates_token_count or 0,
            )

        if response.text is None:
            raise RuntimeError("Google returned no text output.")

        logger.info(f"Google LLM provider succeeded: model={self.model}, method=invoke")
        return response.text

    def _structured_once(self, prompt: str, output_schema: type[OutputT]) -> OutputT:
        """Execute one structured-output attempt with Gemini JSON mode.

        Args:
            prompt: Prompt for this attempt.
            output_schema: Pydantic model passed as ``response_schema``.

        Returns:
            Parsed object as an instance of ``output_schema``.

        Raises:
            RuntimeError: If the Google SDK raises ``errors.APIError``.
            ValidationError: If ``response.parsed`` is a dictionary that fails
                Pydantic validation.
            StructuredOutputParsingError: If Gemini returns no parsed output or
                an unsupported parsed type.
        """
        logger.info(
            f"Calling Google LLM provider: model={self.model}, method=structured"
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=output_schema,
                    temperature=self.temperature,
                ),
            )
        except errors.APIError as error:
            logger.exception(
                f"Google LLM provider failed: model={self.model}, method=structured"
            )
            raise RuntimeError(f"Error calling Google LLM provider: {error}") from error

        usage = response.usage_metadata
        if usage is not None:
            self._add_token(
                input_tokens=usage.prompt_token_count or 0,
                output_tokens=usage.candidates_token_count or 0,
            )

        parsed = response.parsed

        if parsed is None:
            raise StructuredOutputParsingError(
                "Google returned no structured output."
            )

        if isinstance(parsed, output_schema):
            logger.info(
                f"Google LLM provider succeeded: model={self.model}, method=structured"
            )
            return parsed

        if isinstance(parsed, dict):
            result = output_schema.model_validate(parsed)
            logger.info(
                f"Google LLM provider succeeded: model={self.model}, method=structured"
            )
            return result

        raise StructuredOutputParsingError(
            "Google returned structured output in an invalid format."
        )

    async def ainvoke(self, prompt: str) -> str:
        """Asynchronously generate plain text with Gemini.

        Args:
            prompt: Complete input prompt.

        Returns:
            ``response.text`` from the Google SDK.

        Raises:
            RuntimeError: If the Google SDK raises ``errors.APIError`` or if no
                text output is returned.
        """
        logger.info(f"Calling Google LLM provider: model={self.model}, method=ainvoke")

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self.temperature,
                )
            )
        except errors.APIError as error:
            logger.exception(f"Google LLM provider failed: model={self.model}, method=ainvoke")
            raise RuntimeError(f"Error calling Google LLM provider: {error}") from error

        usage = response.usage_metadata
        if usage is not None:
            self._add_token(
                input_tokens=usage.prompt_token_count or 0,
                output_tokens=usage.candidates_token_count or 0,
            )

        if response.text is None:
            raise RuntimeError("Google returned no text output.")

        logger.info(f"Google LLM provider succeeded: model={self.model}, method=ainvoke")
        return response.text

    async def _astructured_once(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        """Execute one asynchronous structured-output attempt.

        Args:
            prompt: Prompt for this attempt.
            output_schema: Pydantic model passed as ``response_schema``.

        Returns:
            Parsed object as an instance of ``output_schema``.

        Raises:
            RuntimeError: If the Google SDK raises ``errors.APIError``.
            ValidationError: If ``response.parsed`` is a dictionary that fails
                Pydantic validation.
            StructuredOutputParsingError: If Gemini returns no parsed output or
                an unsupported parsed type.
        """
        logger.info(
            f"Calling Google LLM provider: model={self.model}, method=astructured"
        )

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=output_schema,
                    temperature=self.temperature,
                ),
            )
        except errors.APIError as error:
            logger.exception(
                f"Google LLM provider failed: model={self.model}, method=astructured"
            )
            raise RuntimeError(f"Error calling Google LLM provider: {error}") from error

        usage = response.usage_metadata
        if usage is not None:
            self._add_token(
                input_tokens=usage.prompt_token_count or 0,
                output_tokens=usage.candidates_token_count or 0,
            )

        parsed = response.parsed

        if parsed is None:
            raise StructuredOutputParsingError(
                "Google returned no structured output."
            )

        if isinstance(parsed, output_schema):
            logger.info(
                f"Google LLM provider succeeded: model={self.model}, method=astructured"
            )
            return parsed

        if isinstance(parsed, dict):
            result = output_schema.model_validate(parsed)
            logger.info(
                f"Google LLM provider succeeded: model={self.model}, method=astructured"
            )
            return result

        raise StructuredOutputParsingError(
            "Google returned structured output in an invalid format."
        )
