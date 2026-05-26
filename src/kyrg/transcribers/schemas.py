"""Normalized transcription data models.

These Pydantic schemas define the provider-independent shape used by the
application after raw local or remote transcription responses are normalized.
"""

from typing import Optional, List

from pydantic import BaseModel, Field


class WordSegment(BaseModel):
    """A single transcribed word with optional timing and confidence metadata."""

    word: str = Field(description="Transcribed word text.")
    start: Optional[float] = Field(
        default=None,
        description="Word start time in seconds, when provided by the provider.",
    )
    end: Optional[float] = Field(
        default=None,
        description="Word end time in seconds, when provided by the provider.",
    )
    probability: Optional[float] = Field(
        default=None,
        description="Provider confidence or probability score for the word.",
    )


class TextSegment(BaseModel):
    """A contiguous transcription segment with optional word-level metadata."""

    id: int = Field(description="Provider-independent segment index.")
    start: Optional[float] = Field(
        default=None,
        description="Segment start time in seconds, when available.",
    )
    end: Optional[float] = Field(
        default=None,
        description="Segment end time in seconds, when available.",
    )
    text: str = Field(description="Transcribed text for this segment.")
    words: List[WordSegment] = Field(
        default_factory=list,
        description="Word-level timing and confidence metadata for this segment.",
    )


class TranscriptionResult(BaseModel):
    """Normalized transcription result returned by every transcriber."""

    audio_path: str = Field(description="Path to the source audio file.")
    language: Optional[str] = Field(
        default=None,
        description="Detected or requested transcription language.",
    )
    text: str = Field(description="Full normalized transcription text.")
    segments: List[TextSegment] = Field(
        default_factory=list,
        description="Normalized text segments produced by the provider.",
    )
    model: str = Field(description="Model identifier used for transcription.")
    raw_response: dict = Field(
        default_factory=dict,
        description="Original provider response or relevant raw metadata.",
    )
    provider: str = Field(description="Provider identifier that produced the result.")
