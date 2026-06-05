from google import genai
from google.genai import types
from typing import Optional

from kyrg.llms.base import LLMBase, OutputT


class GoogleLLM(LLMBase):
    def __init__(self, api_key: str, model: str, temperature: Optional[float] = None):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def invoke(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=self.temperature,
            )
        )

        if response.text is None:
            raise RuntimeError("Google returned no text output.")

        return response.text

    def structured(self, prompt: str, output_schema: type[OutputT]) -> OutputT:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=output_schema,
                temperature=self.temperature,
            ),
        )

        parsed = response.parsed

        if parsed is None:
            raise RuntimeError("Google returned no structured output.")

        if isinstance(parsed, output_schema):
            return parsed

        if isinstance(parsed, dict):
            return output_schema.model_validate(parsed)

        raise RuntimeError("Google returned structured output in an invalid format.")

    async def ainvoke(self, prompt: str) -> str:
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=self.temperature,
            )
        )

        if response.text is None:
            raise RuntimeError("Google returned no text output.")

        return response.text

    async def astructured(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=output_schema,
                temperature=self.temperature,
            ),
        )

        parsed = response.parsed

        if parsed is None:
            raise RuntimeError("Google returned no structured output.")

        if isinstance(parsed, output_schema):
            return parsed

        if isinstance(parsed, dict):
            return output_schema.model_validate(parsed)

        raise RuntimeError("Google returned structured output in an invalid format.")