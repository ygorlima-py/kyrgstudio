"""LLM-backed actions for extracting structured copy analysis outputs."""

import json

from kyrg.llms.base import LLMBase
from kyrg.workflows.base import AIActionBase
from kyrg.workflows.copyanalysis.prompts import CopyAnalysisPrompts
from kyrg.workflows.copyanalysis.schemas import (
    CopyStructureOutput,
    OfferAnalysisOutput,
    PersuasionAnalysisOutput,
    StructuredTranscript,
)
from kyrg.workflows.copyanalysis.system_prompt import CopyAnalysisSystemPrompts


class ExtractCopyStructure(AIActionBase):
    """Extract the persuasive structure and section sequence from a transcript."""

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
        """Run the copy structure extraction synchronously."""
        return self.llm.structured(
            prompt=self._build_prompt(),
            system_prompt=CopyAnalysisSystemPrompts.EXTRACT_COPY_STRUCTURE_SYSTEM_PROMPT,
            prompt_cache_key="copy-analysis:structure",
            output_schema=CopyStructureOutput,
        )
        
    async def aexecute(self) -> CopyStructureOutput:
        """Run the copy structure extraction asynchronously."""
        return await self.llm.astructured(
            prompt=self._build_prompt(),
            system_prompt=CopyAnalysisSystemPrompts.EXTRACT_COPY_STRUCTURE_SYSTEM_PROMPT,
            prompt_cache_key="copy-analysis:structure",
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
            ),
        )
        
class ExtractOfferElements(AIActionBase):
    """Extract offer, audience, proof, objection, and CTA elements from copy."""

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
        """Run the offer element extraction synchronously."""
        return self.llm.structured(
            prompt=self._build_prompt(),
            system_prompt=CopyAnalysisSystemPrompts.EXTRACT_OFFER_ELEMENTS_SYSTEM_PROMPT,
            prompt_cache_key="copy-analysis:offer",
            output_schema=OfferAnalysisOutput,
        )
        
    async def aexecute(self) -> OfferAnalysisOutput:
        """Run the offer element extraction asynchronously."""
        return await self.llm.astructured(
            prompt=self._build_prompt(),
            system_prompt=CopyAnalysisSystemPrompts.EXTRACT_OFFER_ELEMENTS_SYSTEM_PROMPT,
            prompt_cache_key="copy-analysis:offer",
            output_schema=OfferAnalysisOutput
        )
        
    def _build_prompt(self) -> str:
        return CopyAnalysisPrompts.EXTRACT_OFFER_ELEMENTS.format(
            language=self.language,
            clean_transcript=self.clean_transcript,
            copy_structure=self.copy_structure.model_dump_json(indent=2),
        )
        
class AnalysePersuasion(AIActionBase):
    """Diagnose persuasion patterns, strengths, signals, and weaknesses."""

    def __init__(
        self,
        llm: LLMBase,
        copy_structure: CopyStructureOutput,
        offer_analysis: OfferAnalysisOutput,
        clean_transcript: str,
        language: str | None,
        ) -> None:
        
        self.copy_structure = copy_structure
        self.offer_analysis = offer_analysis
        self.clean_transcript = clean_transcript
        self.language = language
        super().__init__(llm)
        
    def execute(self) -> PersuasionAnalysisOutput:
        """Run the persuasion analysis synchronously."""
        return self.llm.structured(
            prompt=self._build_prompt(),
            system_prompt=CopyAnalysisSystemPrompts.ANALYSE_PERSUASION_SYSTEM_PROMPT,
            prompt_cache_key="copy-analysis:persuasion",
            output_schema=PersuasionAnalysisOutput,
        )
        
    async def aexecute(self) -> PersuasionAnalysisOutput:
        """Run the persuasion analysis asynchronously."""
        return await self.llm.astructured(
            prompt=self._build_prompt(),
            system_prompt=CopyAnalysisSystemPrompts.ANALYSE_PERSUASION_SYSTEM_PROMPT,
            prompt_cache_key="copy-analysis:persuasion",
            output_schema=PersuasionAnalysisOutput,
        )
        
    def _build_prompt(self) -> str:
        return CopyAnalysisPrompts.ANALYSE_PERSUASION.format(
            language=self.language,
            clean_transcript=self.clean_transcript,
            copy_structure=self.copy_structure.model_dump_json(indent=2),
            offer_analysis=self.offer_analysis.model_dump_json(indent=2),
        )
        
        
