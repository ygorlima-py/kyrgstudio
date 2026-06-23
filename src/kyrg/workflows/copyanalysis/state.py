from typing import Annotated, NotRequired, TypedDict

from kyrg.transcribers import TranscriptionResult
from kyrg.workflows.copyanalysis.schemas import (
    StructuredTranscript,
    CopyStructureOutput,
    OfferAnalysisOutput,
    PersuasionAnalysisOutput,
    CopyAnalysisOutput,
    )
from operator import add

class CopyAnalysisState(TypedDict):
    transcription: TranscriptionResult

    clean_transcript: NotRequired[str]
    structured_transcription: NotRequired[list[StructuredTranscript] | None]
    language: NotRequired[str | None]
    
    input_tokens: NotRequired[Annotated[int, add]]
    output_tokens: NotRequired[Annotated[int, add]]
    total_tokens: NotRequired[Annotated[int, add]]
    
    copy_structure: NotRequired[CopyStructureOutput]
    offer_analysis: NotRequired[OfferAnalysisOutput]
    persuasion_analysis: NotRequired[PersuasionAnalysisOutput]
    analysis: NotRequired[CopyAnalysisOutput]
