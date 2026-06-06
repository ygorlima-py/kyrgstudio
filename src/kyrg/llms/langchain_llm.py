from loguru import logger
from langchain_core.language_models.chat_models import BaseChatModel

from kyrg.llms.base import LLMBase, OutputT


class LangChainLLM(LLMBase):
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    def invoke(self, prompt: str) -> str:
        logger.info("Calling LangChain LLM provider: method=invoke")

        try:
            response = self.llm.invoke(prompt)
        except Exception as error:
            logger.exception("LangChain LLM provider failed: method=invoke")
            raise RuntimeError(f"Error calling LangChain LLM provider: {error}") from error

        content = response.content

        logger.info("LangChain LLM provider succeeded: method=invoke")

        if isinstance(content, str):
            return content

        return str(content)

    def structured(self, prompt: str, output_schema: type[OutputT]) -> OutputT:
        logger.info("Calling LangChain LLM provider: method=structured")

        try:
            structured_llm = self.llm.with_structured_output(output_schema)
            response = structured_llm.invoke(prompt)
        except Exception as error:
            logger.exception("LangChain LLM provider failed: method=structured")
            raise RuntimeError(f"Error calling LangChain LLM provider: {error}") from error

        if isinstance(response, output_schema):
            logger.info("LangChain LLM provider succeeded: method=structured")
            return response

        if isinstance(response, dict):
            result = output_schema.model_validate(response)
            logger.info("LangChain LLM provider succeeded: method=structured")
            return result

        raise RuntimeError("LangChain returned structured output in an invalid format.")

    async def ainvoke(self, prompt: str) -> str:
        logger.info("Calling LangChain LLM provider: method=ainvoke")

        try:
            response = await self.llm.ainvoke(prompt)
        except Exception as error:
            logger.exception("LangChain LLM provider failed: method=ainvoke")
            raise RuntimeError(f"Error calling LangChain LLM provider: {error}") from error

        content = response.content

        logger.info("LangChain LLM provider succeeded: method=ainvoke")

        if isinstance(content, str):
            return content

        return str(content)

    async def astructured(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        logger.info("Calling LangChain LLM provider: method=astructured")

        try:
            structured_llm = self.llm.with_structured_output(output_schema)
            response = await structured_llm.ainvoke(prompt)
        except Exception as error:
            logger.exception("LangChain LLM provider failed: method=astructured")
            raise RuntimeError(f"Error calling LangChain LLM provider: {error}") from error

        if isinstance(response, output_schema):
            logger.info("LangChain LLM provider succeeded: method=astructured")
            return response

        if isinstance(response, dict):
            result = output_schema.model_validate(response)
            logger.info("LangChain LLM provider succeeded: method=astructured")
            return result

        raise RuntimeError("LangChain returned structured output in an invalid format.")
