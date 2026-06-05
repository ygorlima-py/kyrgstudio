from kyrg.llms.base import LLMBase
from kyrg.workflows.base import AIActionBase
from kyrg.transcribers.schemas import TranscriptionResult
from kyrg.workflows.transcriber.prompts import TranscriptionPrompts

from typing import Any

class ExtractTranscriptionContext(AIActionBase):
    def __init__(self, llm: LLMBase, resul):
        super().__init__(llm)
        
class CorrectTranscription(AIActionBase):
    
    def __init__(
        self,
        llm: LLMBase,
        result: TranscriptionResult,
        domain_context: dict[str, Any],
        ):
        self.result = result
        self.domain_context = domain_context
        super().__init__(llm)
    
    def execute(self) -> TranscriptionResult:
        return self.llm.structured(
            prompt=self._build_prompt(),
            output_schema=TranscriptionResult,
        )
        
    async def aexeculte(self) -> TranscriptionResult:
        return await self.llm.astructured(
            prompt=self._build_prompt(),
            output_schema=TranscriptionResult,
        )
        
    def _build_prompt(self) -> str:
        return TranscriptionPrompts.CORRECTION.format(
            domain_context=self.domain_context,
            result=self.result,
        )