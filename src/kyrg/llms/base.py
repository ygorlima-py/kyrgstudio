from abc import ABC, abstractmethod
from typing import TypeVar
from pydantic import BaseModel, ValidationError

from kyrg.llms.error import (
    StructuredOutputError,
    StructuredOutputParsingError,
    format_structured_error,
    build_retry_prompt,
)

OutputT = TypeVar("OutputT", bound=BaseModel)


class LLMBase(ABC):
    
    def __init__(self, max_attempts: int = 2):
        self.max_attempts = max_attempts
        self._input_tokens = 0
        self._output_tokens = 0
    
    @abstractmethod
    def invoke(self, prompt: str) -> str:
        ...
    
    @abstractmethod
    async def ainvoke(self, prompt: str) -> str:
        ...

   
    def structured(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        
        current_prompt = prompt
        last_error: ValidationError | StructuredOutputParsingError | None = None
    
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self._structured_once(
                    current_prompt,
                    output_schema,
                )
            except (ValidationError, StructuredOutputParsingError) as error:
                last_error = error

                if attempt == self.max_attempts:
                    break

                current_prompt=build_retry_prompt(
                    original_prompt=prompt,
                    errors=format_structured_error(error),
                )

        raise StructuredOutputError(
            f"{output_schema.__name__} remained invalid after "
            f"{self.max_attempts} attempts"
        ) from last_error
    
    async def astructured(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        
        current_prompt = prompt
        last_error: ValidationError | StructuredOutputParsingError | None = None
    
        for attempt in range(1, self.max_attempts + 1):
            try:
                return await self._astructured_once(
                    current_prompt,
                    output_schema,
                )
            except (ValidationError, StructuredOutputParsingError) as error:
                last_error = error

                if attempt == self.max_attempts:
                    break

                current_prompt=build_retry_prompt(
                    original_prompt=prompt,
                    errors=format_structured_error(error),
                )

        raise StructuredOutputError(
            f"{output_schema.__name__} remained invalid after "
            f"{self.max_attempts} attempts"
        ) from last_error
    
        
    @abstractmethod
    def _structured_once(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        ...
        
    @abstractmethod
    async def _astructured_once(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        ...
    
    def _add_token(self, input_tokens: int, output_tokens: int):
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        
        
    def token_usage(self):
        total_input_tokens = self._input_tokens
        total_output_tokens = self._output_tokens
        
        return {
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
        }
