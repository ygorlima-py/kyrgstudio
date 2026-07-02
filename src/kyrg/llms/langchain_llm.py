"""LangChain chat model implementation of the project LLM interface.

This module lets workflows use any LangChain ``BaseChatModel`` through the
same ``LLMBase`` contract used by direct provider SDK adapters. It is useful
when callers want LangChain model configuration, routing, tracing, or provider
abstraction while keeping the rest of the project provider-neutral.
"""

from loguru import logger
from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.chat_models import BaseChatModel
from typing import Any, cast

from kyrg.llms.base import LLMBase, OutputT
from kyrg.llms.error import StructuredOutputParsingError


class LangChainLLM(LLMBase):
    """LLM adapter backed by a LangChain ``BaseChatModel``.

    Plain calls delegate to ``llm.invoke`` / ``llm.ainvoke``. Structured calls
    use LangChain's ``with_structured_output`` with ``include_raw=True`` so the
    adapter can read both parsed output and raw token usage metadata.
    """

    def __init__(self, llm: BaseChatModel):
        """Create a LangChain-backed LLM adapter.

        Args:
            llm: Configured LangChain chat model. The model must support
                ``invoke`` / ``ainvoke`` and, for structured output,
                ``with_structured_output``.
        """
        self.llm = llm
        super().__init__()

    def invoke(self, prompt: str) -> str:
        """Generate plain text through the wrapped LangChain model.

        Args:
            prompt: Complete input prompt.

        Returns:
            Message content as a string. Non-string content is converted with
            ``str`` to keep the project contract stable.

        Raises:
            StructuredOutputParsingError: If LangChain raises
                ``OutputParserException``.
            RuntimeError: If any other LangChain call failure occurs.
        """
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
        """Execute one structured-output attempt through LangChain.

        Args:
            prompt: Prompt for this attempt.
            output_schema: Pydantic model requested from
                ``with_structured_output``.

        Returns:
            Parsed output as an instance of ``output_schema``.

        Raises:
            RuntimeError: If the LangChain structured runnable fails before a
                structured response can be inspected.
            ValidationError: If parsed dictionary output fails Pydantic
                validation.
            StructuredOutputParsingError: If LangChain reports
                ``parsing_error`` or returns an unsupported parsed type.
        """
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
        """Asynchronously generate plain text through LangChain.

        Args:
            prompt: Complete input prompt.

        Returns:
            Message content as a string. Non-string content is converted with
            ``str`` to keep the project contract stable.

        Raises:
            StructuredOutputParsingError: If LangChain raises
                ``OutputParserException``.
            RuntimeError: If any other LangChain call failure occurs.
        """
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
        """Execute one asynchronous structured-output attempt.

        Args:
            prompt: Prompt for this attempt.
            output_schema: Pydantic model requested from
                ``with_structured_output``.

        Returns:
            Parsed output as an instance of ``output_schema``.

        Raises:
            RuntimeError: If the LangChain structured runnable fails before a
                structured response can be inspected.
            ValidationError: If parsed dictionary output fails Pydantic
                validation.
            StructuredOutputParsingError: If LangChain reports
                ``parsing_error`` or returns an unsupported parsed type.
        """
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
