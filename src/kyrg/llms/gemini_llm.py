from typing import Optional

from google import genai
from google.genai import errors, types
from loguru import logger

from kyrg.llms.base import LLMBase, OutputT


class GoogleLLM(LLMBase):
    def __init__(self, api_key: str, model: str, temperature: Optional[float] = None):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.temperature = temperature
        super().__init__()

    def invoke(self, prompt: str) -> str:
        logger.info(f"Calling Google LLM provider: model={self.model}, method=invoke")

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self.temperature,
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

    def structured(self, prompt: str, output_schema: type[OutputT]) -> OutputT:
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
            raise RuntimeError("Google returned no structured output.")

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

        raise RuntimeError("Google returned structured output in an invalid format.")

    async def ainvoke(self, prompt: str) -> str:
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

    async def astructured(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
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
            raise RuntimeError("Google returned no structured output.")

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

        raise RuntimeError("Google returned structured output in an invalid format.")
