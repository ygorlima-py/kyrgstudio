from kyrg.llms.base import LLMBase
from kyrg.transcribers.schemas import TranscriptionResult
from kyrg.workflows.base import AIActionBase
from kyrg.workflows.transcriber.prompts import TranscriptionPrompts
from kyrg.workflows.transcriber.schemas import (
    CorrectedTranscriptionOutput,
    DomainContextOutput,
)
from kyrg.workflows.transcriber.system_prompt import TranscriptionSystemPrompts


class ExtractDomainContext(AIActionBase):
    def __init__(
        self,
        llm: LLMBase,
        result: TranscriptionResult,
    ):

        self.result = result
        super().__init__(llm)

    def execute(self) -> DomainContextOutput:
        return self.llm.structured(
            prompt=self._build_prompt(),
            system_prompt=(
                TranscriptionSystemPrompts.SYSTEM_PROMPT_EXTRACT_DOMAIN_CONTEXT
            ),
            prompt_cache_key="transcription:domain-context",
            output_schema=DomainContextOutput,
        )

    async def aexecute(self) -> DomainContextOutput:
        return await self.llm.astructured(
            prompt=self._build_prompt(),
            system_prompt=(
                TranscriptionSystemPrompts.SYSTEM_PROMPT_EXTRACT_DOMAIN_CONTEXT
            ),
            prompt_cache_key="transcription:domain-context",
            output_schema=DomainContextOutput,
        )

    def _build_prompt(self) -> str:
        return TranscriptionPrompts.EXTRACT_DOMAIN_CONTEXT.format(
            raw_transcription=self.result.model_dump_json(indent=2)
        )


class CorrectTranscription(AIActionBase):
    def __init__(
        self,
        llm: LLMBase,
        result: TranscriptionResult,
        domain_context: DomainContextOutput,
    ):
        self.result = result
        self.domain_context = domain_context
        super().__init__(llm)

    def execute(self) -> CorrectedTranscriptionOutput:
        return self.llm.structured(
            prompt=self._build_prompt(),
            system_prompt=(
                TranscriptionSystemPrompts.SYSTEM_PROMPT_CORRECT_TRANSCRIPTION
            ),
            prompt_cache_key="transcription:correction",
            output_schema=CorrectedTranscriptionOutput,
        )

    async def aexecute(self) -> CorrectedTranscriptionOutput:
        return await self.llm.astructured(
            prompt=self._build_prompt(),
            system_prompt=(
                TranscriptionSystemPrompts.SYSTEM_PROMPT_CORRECT_TRANSCRIPTION
            ),
            prompt_cache_key="transcription:correction",
            output_schema=CorrectedTranscriptionOutput,
        )

    def _build_prompt(self) -> str:
        return TranscriptionPrompts.CORRECTION.format(
            domain_context=self.domain_context.model_dump_json(indent=2),
            result=self.result.model_dump_json(indent=2),
        )
