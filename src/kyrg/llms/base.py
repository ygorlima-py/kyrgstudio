from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

OutputT = TypeVar("OutputT", bound=BaseModel)


class LLMBase(ABC):
    
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