"""Public transcription provider API.

This package exposes the shared transcription contracts, normalized result
schemas, and concrete local or remote provider adapters. Provider classes hide
the differences between external APIs and local runtimes by returning the same
``TranscriptionResult`` shape.

Typical usage:

    from app.transcribers import OpenAITranscriber, TranscriptionResult

    transcriber = OpenAITranscriber(...)
    result: TranscriptionResult = transcriber.transcribe()
"""

from kyrg.transcribers.base import TranscriberAPIBase, TranscriberBase
from kyrg.transcribers.local_model import TranscriberWhisperLocal
from kyrg.transcribers.remote_model import (
    ElevenLabsTranscriber,
    OpenAITranscriber,
    OpenRouterTranscriber,
)
from kyrg.transcribers.schemas import (
    TextSegment,
    TranscriptionResult,
    WordSegment,
)


__all__ = [
    "ElevenLabsTranscriber",
    "OpenAITranscriber",
    "OpenRouterTranscriber",
    "TextSegment",
    "TranscriberAPIBase",
    "TranscriberBase",
    "TranscriberWhisperLocal",
    "TranscriptionResult",
    "WordSegment",
]
