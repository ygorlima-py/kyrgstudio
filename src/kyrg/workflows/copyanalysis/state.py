from typing import Any, NotRequired, TypedDict

from kyrg.transcribers import TranscriptionResult


class CopyAnalysisState(TypedDict):
    transcription: TranscriptionResult

    clean_transcript: NotRequired[str]
    language: NotRequired[str | None]

    copy_structure: NotRequired[Any]
    offer_analysis: NotRequired[Any]
    persuasion_analysis: NotRequired[Any]
    analysis: NotRequired[Any]
