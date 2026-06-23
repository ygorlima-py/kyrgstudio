from loguru import logger
from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.chat_models import BaseChatModel
from typing import Any, cast

from kyrg.llms.base import LLMBase, OutputT
from kyrg.llms.error import StructuredOutputParsingError


class LangChainLLM(LLMBase):
    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        super().__init__()

    def invoke(self, prompt: str) -> str:
        logger.info("Calling LangChain LLM provider: method=invoke")

        try:
            response = self.llm.invoke(prompt)
        except OutputParserException as error:
            raise StructuredOutputParsingError(str(error)) from error
        except Exception as error:
            logger.exception("LangChain LLM provider failed: method=invoke")
            raise RuntimeError(f"Error calling LangChain LLM provider: {error}") from error

        content = response.content
        
        metadata = response.usage_metadata
        if metadata is not None:
            self._add_token(input_tokens=metadata["input_tokens"], output_tokens=metadata["output_tokens"])
    
        logger.info("LangChain LLM provider succeeded: method=invoke")
        
        if isinstance(content, str):
            return content

        return str(content)

    def _structured_once(self, prompt: str, output_schema: type[OutputT]) -> OutputT:
        logger.info("Calling LangChain LLM provider: method=structured")

        try:
            structured_llm = self.llm.with_structured_output(output_schema, include_raw=True,)
            response = cast(
                        dict[str, Any],
                        structured_llm.invoke(prompt),
                    )
            
            raw = response["raw"]
            parsed = response["parsed"]
            parsing_error = response.get("parsing_error")
            usage = getattr(raw, "usage_metadata", None)

        except Exception as error:
            logger.exception("LangChain LLM provider failed: method=structured")
            raise RuntimeError(f"Error calling LangChain LLM provider: {error}") from error

        if usage:
            self._add_token(
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
            )

        if parsing_error is not None:
            raise StructuredOutputParsingError(
                str(parsing_error)
            ) from parsing_error
        
        if isinstance(parsed, output_schema):
            logger.info("LangChain LLM provider succeeded: method=structured")
            return parsed

        if isinstance(parsed, dict):
            result = output_schema.model_validate(parsed)
            logger.info("LangChain LLM provider succeeded: method=structured")
            return result

        raise StructuredOutputParsingError(
            "LangChain returned structured output in an invalid format."
        )

    async def ainvoke(self, prompt: str) -> str:
        logger.info("Calling LangChain LLM provider: method=ainvoke")

        try:
            response = await self.llm.ainvoke(prompt)
        except OutputParserException as error:
            raise StructuredOutputParsingError(str(error)) from error
        except Exception as error:
            logger.exception("LangChain LLM provider failed: method=ainvoke")
            raise RuntimeError(f"Error calling LangChain LLM provider: {error}") from error

        content = response.content

        metadata = response.usage_metadata
        if metadata is not None:
            self._add_token(input_tokens=metadata["input_tokens"], output_tokens=metadata["output_tokens"])
            
        logger.info("LangChain LLM provider succeeded: method=ainvoke")

        if isinstance(content, str):
            return content

        return str(content)

    async def _astructured_once(
        self,
        prompt: str,
        output_schema: type[OutputT],
    ) -> OutputT:
        logger.info("Calling LangChain LLM provider: method=astructured")

        try:
            structured_llm = self.llm.with_structured_output(output_schema, include_raw=True)
            response = cast(
                        dict[str, Any],
                        await structured_llm.ainvoke(prompt),
                    )
            
            raw = response["raw"]
            parsed = response["parsed"]
            parsing_error = response.get("parsing_error")
            usage = getattr(raw, "usage_metadata", None)
            
        except Exception as error:
            logger.exception("LangChain LLM provider failed: method=astructured")
            raise RuntimeError(f"Error calling LangChain LLM provider: {error}") from error

        if usage:
            self._add_token(
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
            )

        if parsing_error is not None:
            raise StructuredOutputParsingError(
                str(parsing_error)
            ) from parsing_error
            
        if isinstance(parsed, output_schema):
            logger.info("LangChain LLM provider succeeded: method=astructured")
            return parsed

        if isinstance(parsed, dict):
            result = output_schema.model_validate(parsed)
            logger.info("LangChain LLM provider succeeded: method=astructured")
            return result

        raise StructuredOutputParsingError(
            "LangChain returned structured output in an invalid format."
        )
