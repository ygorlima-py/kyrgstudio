from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

OutputT = TypeVar("OutputT", bound=BaseModel)


class LLMBase(ABC):
    
    def __init__(self):
        self._input_tokens = 0
        self._output_tokens = 0
    
    @abstractmethod
    def invoke(self, prompt: str) -> str:
        ...
    
    @abstractmethod
    async def ainvoke(self, prompt: str) -> str:
        ...

    @abstractmethod
    def structured(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        ...
    
    @abstractmethod
    async def astructured(
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