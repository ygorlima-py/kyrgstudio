from openai import OpenAI, AsyncOpenAI

from typing import Optional

from kyrg.llms.base import LLMBase, OutputT



class OpenAILLM(LLMBase):
    BASE_URL = "https://api.openai.com/v1"
    
    def __init__(self, api_key, model: str, temperature: Optional[float] = None):   
        self.client = OpenAI(api_key=api_key, base_url=self.BASE_URL)
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=self.BASE_URL)
        self.model = model
        self.temperature = temperature

    def invoke(self, prompt: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            temperature=self.temperature,
        )
        return response.output_text

    def structured(self, prompt: str, output_schema: type[OutputT]) -> OutputT:
        response = self.client.responses.parse(
            model=self.model,
            input=prompt,
            text_format=output_schema,
            temperature=self.temperature,
        )
        
        parsed = response.output_parsed
        
        if parsed is None:
            raise RuntimeError("OpenAI returned no structured output.")

        return parsed
    
    async def ainvoke(self, prompt: str) -> str:
        response = await self.async_client.responses.create(
            model=self.model,
            input=prompt,
            temperature=self.temperature,
        )
        return response.output_text
    
    async def astructured(self, prompt: str, output_schema: type[OutputT]) -> OutputT:
        response = await self.async_client.responses.parse(
            model=self.model,
            input=prompt,
            text_format=output_schema,
            temperature=self.temperature
        )
        
        parsed = response.output_parsed
        
        if parsed is None:
            raise RuntimeError("OpenAI returned no structured output.")

        return parsed