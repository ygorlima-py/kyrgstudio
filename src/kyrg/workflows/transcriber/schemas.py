from __future__ import annotations
from pydantic import BaseModel, Field
from dataclasses import dataclass, field

from kyrg.llms.base import LLMBase

class DomainContextOutput(BaseModel):
    language: str = Field(
        description="Primary language detected in the transcription."
    )
    main_subject: str = Field(
        description="Main subject or central topic discussed in the video."
    )
    content_type: str = Field(
        description="Content category, such as lesson, podcast, interview, meeting, tutorial, vlog, presentation, sales video, or advertisement."
    )
    summary: str = Field(
        description="Short factual summary of the transcription content."
    )
    important_terms: list[str] = Field(
        default_factory=list,
        description="Important terms that should be preserved, checked, or used as context during transcription correction."
    )
    named_entities: list[str] = Field(
        default_factory=list,
        description="Detected proper nouns, including people, places, brands, products, organizations, institutions, or events."
    )
    technical_terms: list[str] = Field(
        default_factory=list,
        description="Domain-specific or technical terms detected in the transcription."
    )
    possible_corrections: list[PossibleCorrection] = Field(
        default_factory=list,
        description="Likely transcription corrections inferred from context, especially for names, brands, technical terms, or phonetically similar words."
    )
    uncertain_terms: list[UncertainTerm] = Field(
        default_factory=list,
        description="Terms or expressions that may be incorrect, ambiguous, unclear, or require human or contextual review."
    )
    correction_rules: list[str] = Field(
        default_factory=list,
        description="Correction guidelines that should be followed by later transcription correction steps."
    )
    
class PossibleCorrection(BaseModel):
    original: str = Field(
        description="Original word, phrase, or transcript segment that may have been transcribed incorrectly."
    )
    corrected: str = Field(
        description="Most likely corrected version inferred from the surrounding context."
    )
    confidence: float = Field(
        ge=0,
        le=1,
        description="Confidence score for the suggested correction, from 0.0 to 1.0."
    )
    reason: str = Field(
        description="Short explanation describing why this correction is likely."
    )

class UncertainTerm(BaseModel):
    term: str = Field(
        description="Word, phrase, name, or expression that appears ambiguous, suspicious, or contextually uncertain."
    )
    reason: str = Field(
        description="Short explanation describing why this term is uncertain and may need review."
    )
    

    
class CorrectedSegment(BaseModel):
    id: int = Field(description="Original segment id.")
    text: str = Field(description="Corrected text for this segment.")


class CorrectedTranscriptionOutput(BaseModel):
    corrected_text: str = Field(description="Full corrected transcription text.")
    corrected_segments: list[CorrectedSegment] = Field(
        default_factory=list,
        description="Only segments whose text should be changed.",
    )
    

@dataclass    
class TranscriberWorkflowContext:
    correction_llm: LLMBase = field(
        metadata={
            "description": "LLM used to correct transcription errors when the quality agent decides correction is safe."
        }
    )

    extract_context_llm: LLMBase = field(
        metadata={
            "description": "LLM used to extract domain context from the raw transcription before quality analysis."
        }
    )