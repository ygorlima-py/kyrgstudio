from langchain_core.language_models.chat_models import BaseChatModel

from kyrg.llms.base import LLMBase, OutputT

class LangChainLLM(LLMBase):
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    def invoke(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)

        content = response.content

        if isinstance(content, str):
            return content

        return str(content)

    def structured(self, prompt: str, output_schema: type[OutputT]) -> OutputT:
        structured_llm = self.llm.with_structured_output(output_schema)
        response = structured_llm.invoke(prompt)

        if isinstance(response, output_schema):
            return response

        if isinstance(response, dict):
            return output_schema.model_validate(response)

        raise RuntimeError("LangChain returned structured output in an invalid format.")

    async def ainvoke(self, prompt: str) -> str:
        response = await self.llm.ainvoke(prompt)

        content = response.content

        if isinstance(content, str):
            return content

        return str(content)

    async def astructured(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        structured_llm = self.llm.with_structured_output(output_schema)
        response = await structured_llm.ainvoke(prompt)

        if isinstance(response, output_schema):
            return response

        if isinstance(response, dict):
            return output_schema.model_validate(response)

        raise RuntimeError("LangChain returned structured output in an invalid format.")