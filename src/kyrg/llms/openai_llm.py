from typing import Optional

from loguru import logger
from openai import AsyncOpenAI, OpenAI, OpenAIError

from kyrg.llms.base import LLMBase, OutputT


class OpenAILLM(LLMBase):
    BASE_URL = "https://api.openai.com/v1"
    
    def __init__(self, api_key, model: str, temperature: Optional[float] = None):   
        self.client = OpenAI(api_key=api_key, base_url=self.BASE_URL)
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=self.BASE_URL)
        self.model = model
        self.temperature = temperature
        super().__init__()

    def invoke(self, prompt: str) -> str:
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

    def structured(self, prompt: str, output_schema: type[OutputT]) -> OutputT:
        logger.info(
            f"Calling OpenAI LLM provider: model={self.model}, method=structured"
        )

        try:
            response = self.client.responses.parse(
                model=self.model,
                input=prompt,
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
            raise RuntimeError("OpenAI returned no structured output.")

        logger.info(
            f"OpenAI LLM provider succeeded: model={self.model}, method=structured"
        )
        return parsed
    
    async def ainvoke(self, prompt: str) -> str:
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
    
    async def astructured(self, prompt: str, output_schema: type[OutputT]) -> OutputT:
        logger.info(
            f"Calling OpenAI LLM provider: model={self.model}, method=astructured"
        )

        try:
            response = await self.async_client.responses.parse(
                model=self.model,
                input=prompt,
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
            raise RuntimeError("OpenAI returned no structured output.")

        logger.info(
            f"OpenAI LLM provider succeeded: model={self.model}, method=astructured"
        )
        return parsed
