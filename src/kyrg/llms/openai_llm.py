"""OpenAI Responses API implementation of the project LLM interface.

The adapter wraps the official OpenAI SDK behind ``LLMBase`` so workflows can
call OpenAI models through the same interface used by every other provider.
It supports plain text generation, structured Pydantic output, async calls, and
latest-call token usage tracking.
"""

from typing import Optional

from loguru import logger
from openai import AsyncOpenAI, OpenAI, OpenAIError

from kyrg.llms.base import LLMBase, OutputT
from kyrg.llms.error import StructuredOutputParsingError


class OpenAILLM(LLMBase):
    """LLM adapter backed by the OpenAI Responses API.

    The class uses ``responses.create`` for plain text calls and
    ``responses.parse`` for structured Pydantic output. Provider-specific
    ``OpenAIError`` exceptions are wrapped as ``RuntimeError`` to keep the
    public provider contract consistent.
    """

    BASE_URL = "https://api.openai.com/v1"
    
    def __init__(
        self,
        api_key: str | None,
        model: str,
        temperature: Optional[float] = None,
        ):
        """Create synchronous and asynchronous OpenAI clients.

        Args:
            api_key: OpenAI API key. ``None`` allows the SDK to resolve
                credentials from its normal environment configuration.
            model: Model name accepted by the OpenAI Responses API.
            temperature: Optional sampling temperature forwarded to each call.
        """
        self.client = OpenAI(api_key=api_key, base_url=self.BASE_URL)
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=self.BASE_URL)
        self.model = model
        self.temperature = temperature
        super().__init__()

    def invoke(self, prompt: str) -> str:
        """Generate plain text with ``responses.create``.

        Args:
            prompt: Complete input prompt.

        Returns:
            ``response.output_text`` from the OpenAI SDK.

        Raises:
            RuntimeError: If the OpenAI SDK raises ``OpenAIError``.
        """
        logger.info(f"Calling OpenAI LLM provider: model={self.model}, method=invoke")

        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
                temperature=self.temperature,
            )
        except OpenAIError as error:
            logger.exception(f"OpenAI LLM provider failed: model={self.model}, method=invoke")
            raise RuntimeError(f"Error calling OpenAI LLM provider: {error}") from error

        logger.info(f"OpenAI LLM provider succeeded: model={self.model}, method=invoke")
        
        usage = response.usage
        
        if usage is not None:
            self._add_token(input_tokens=usage.input_tokens, output_tokens=usage.output_tokens)
            
        return response.output_text

    def _structured_once(
        self,
        prompt: str,
        system_prompt: str,
        prompt_cache_key: str,
        output_schema: type[OutputT],
        ) -> OutputT:
        """Execute one structured-output attempt with ``responses.parse``.

        Args:
            prompt: Prompt for this attempt.
            output_schema: Pydantic model passed as ``text_format``.

        Returns:
            Parsed Pydantic object returned by ``response.output_parsed``.

        Raises:
            RuntimeError: If the OpenAI SDK raises ``OpenAIError``.
            StructuredOutputParsingError: If OpenAI returns no parsed object.
        """
        logger.info(
            f"Calling OpenAI LLM provider: model={self.model}, method=structured"
        )

        try:
            response = self.client.responses.parse(
                model=self.model,
                input=prompt,
                instructions=system_prompt,
                prompt_cache_key=prompt_cache_key,
                text_format=output_schema,
                temperature=self.temperature,
            )
        except OpenAIError as error:
            logger.exception(
                f"OpenAI LLM provider failed: model={self.model}, method=structured"
            )
            raise RuntimeError(f"Error calling OpenAI LLM provider: {error}") from error
        
        parsed = response.output_parsed
        
        usage = response.usage
        if usage is not None:
            self._add_token(input_tokens=usage.input_tokens, output_tokens=usage.output_tokens)
        
        if parsed is None:
            raise StructuredOutputParsingError(
                "OpenAI returned no structured output."
            )

        logger.info(
            f"OpenAI LLM provider succeeded: model={self.model}, method=structured"
        )
        return parsed
    
    async def ainvoke(self, prompt: str) -> str:
        """Asynchronously generate plain text with ``responses.create``.

        Args:
            prompt: Complete input prompt.

        Returns:
            ``response.output_text`` from the OpenAI SDK.

        Raises:
            RuntimeError: If the OpenAI SDK raises ``OpenAIError``.
        """
        logger.info(f"Calling OpenAI LLM provider: model={self.model}, method=ainvoke")

        try:
            response = await self.async_client.responses.create(
                model=self.model,
                input=prompt,
                temperature=self.temperature,
            )
        except OpenAIError as error:
            logger.exception(f"OpenAI LLM provider failed: model={self.model}, method=ainvoke")
            raise RuntimeError(f"Error calling OpenAI LLM provider: {error}") from error

        logger.info(f"OpenAI LLM provider succeeded: model={self.model}, method=ainvoke")
        
        usage = response.usage
        if usage is not None:
            self._add_token(input_tokens=usage.input_tokens, output_tokens=usage.output_tokens)
            
        return response.output_text
    
    async def _astructured_once(
        self,
        prompt: str,
        system_prompt: str,
        prompt_cache_key: str,
        output_schema: type[OutputT],
        ) -> OutputT:
        """Execute one asynchronous structured-output attempt.

        Args:
            prompt: Prompt for this attempt.
            output_schema: Pydantic model passed as ``text_format``.

        Returns:
            Parsed Pydantic object returned by ``response.output_parsed``.

        Raises:
            RuntimeError: If the OpenAI SDK raises ``OpenAIError``.
            StructuredOutputParsingError: If OpenAI returns no parsed object.
        """
        logger.info(
            f"Calling OpenAI LLM provider: model={self.model}, method=astructured"
        )

        try:
            response = await self.async_client.responses.parse(
                model=self.model,
                input=prompt,
                instructions=system_prompt,
                prompt_cache_key=prompt_cache_key,
                text_format=output_schema,
                temperature=self.temperature
            )
        except OpenAIError as error:
            logger.exception(
                f"OpenAI LLM provider failed: model={self.model}, method=astructured"
            )
            raise RuntimeError(f"Error calling OpenAI LLM provider: {error}") from error
        
        usage = response.usage
        if usage is not None:
            self._add_token(input_tokens=usage.input_tokens, output_tokens=usage.output_tokens)
        
        parsed = response.output_parsed
        
        if parsed is None:
            raise StructuredOutputParsingError(
                "OpenAI returned no structured output."
            )

        logger.info(
            f"OpenAI LLM provider succeeded: model={self.model}, method=astructured"
        )
        return parsed
