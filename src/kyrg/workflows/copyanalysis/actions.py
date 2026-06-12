from typing import Any
import json

from kyrg.workflows.base import AIActionBase
from kyrg.workflows.copyanalysis.schemas import StructuredTranscript
from kyrg.llms.base import LLMBase
from kyrg.workflows.copyanalysis.schemas import (
                                                CopyStructureOutput,
                                                OfferAnalysisOutput,
                                                PersuasionAnalysisOutput,
)
from kyrg.workflows.copyanalysis.prompts import CopyAnalysisPrompts

class ExtractCopyStructure(AIActionBase):
    def __init__(
        self,
        llm: LLMBase,
        clean_transcript: str,
        structured_transcription: list[StructuredTranscript],
        language: str | None,
    ) -> None:
        
        self.clean_transcript = clean_transcript
        self.structured_transcription = structured_transcription
        self.language = language
        super().__init__(llm)
        
    def execute(self) -> CopyStructureOutput:
        return self.llm.structured(
            prompt=self._build_prompt(),
            output_schema=CopyStructureOutput,
        )
        
    async def aexecute(self) -> CopyStructureOutput:
        return await self.llm.astructured(
            prompt=self._build_prompt(),
            output_schema=CopyStructureOutput
        )
        
    def _build_prompt(self) -> str:
        return CopyAnalysisPrompts.EXTRACT_COPY_STRUCTURE.format(
            language=self.language,
            clean_transcript=self.clean_transcript,
            structured_transcription=json.dumps(
            [
            item.model_dump()
                for item in self.structured_transcription
            ],
            ensure_ascii=False,
            indent=2,
            )
        )
        
class ExtractOfferElements(AIActionBase):
    def __init__(
        self,
        llm: LLMBase,
        clean_transcript: str,
        copy_structure: CopyStructureOutput,
        language: str | None
        ) -> None:
        
        self.clean_transcript = clean_transcript
        self.copy_structure = copy_structure
        self.language = language
        super().__init__(llm)
        
    def execute(self) -> OfferAnalysisOutput:
        return self.llm.structured(
            prompt=self._build_prompt(),
            output_schema=OfferAnalysisOutput,
        )
        
    async def aexecute(self) -> OfferAnalysisOutput:
        return await self.llm.astructured(
            prompt=self._build_prompt(),
            output_schema=OfferAnalysisOutput
        )
        
    def _build_prompt(self) -> str:
        return CopyAnalysisPrompts.EXTRACT_OFFER_ELEMENTS.format(
            language=self.language,
            clean_transcript=self.clean_transcript,
            copy_structure=self.copy_structure.model_dump_json(indent=2),
        )
        
class AnalysePersuasion(AIActionBase):
    def __init__(
        self,
        llm: LLMBase,
        copy_structure: CopyStructureOutput,
        offer_analysis: OfferAnalysisOutput,
        language: str | None,
        ) -> None:
        
        self.copy_structure = copy_structure
        self.offer_analysis = offer_analysis
        self.language = language
        super().__init__(llm)
        
    def execute(self) -> PersuasionAnalysisOutput:
        return self.llm.structured(
            prompt=self._build_prompt(),
            output_schema=PersuasionAnalysisOutput,
        )
        
    async def aexecute(self) -> PersuasionAnalysisOutput:
        return await self.llm.astructured(
            prompt=self._build_prompt(),
            output_schema=PersuasionAnalysisOutput,
        )
        
    def _build_prompt(self) -> str:
        return CopyAnalysisPrompts.ANALYSE_PERSUASION.format(
            language=self.language,
            copy_structure=self.copy_structure.model_dump_json(indent=2),
            offer_analysis=self.offer_analysis.model_dump_json(indent=2),
        )
        
        