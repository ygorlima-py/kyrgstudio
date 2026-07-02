"""Local transcription provider backed by Faster Whisper.

This module contains the local Whisper transcriber implementation. It adapts
``faster_whisper`` segment objects into the shared ``TranscriptionResult``
schema used by the rest of the application.
"""
from typing import Any
import asyncio
from faster_whisper import WhisperModel # type: ignore[reportMissingTypeStubs]

from kyrg.transcribers.base import TranscriberBase
from kyrg.transcribers.schemas import TranscriptionResult, TextSegment, WordSegment


class TranscriberWhisperLocal(TranscriberBase):
    """Local Whisper transcriber using the ``faster_whisper`` runtime.

    The class loads a Whisper model locally, transcribes the configured audio
    file, requests word-level timestamps, and normalizes the raw model output
    into the application-level transcription schema.
    """

    PROVIDER = "whisper_local"

    def _normalize_word(self, word: Any) -> WordSegment:
        """Convert a Faster Whisper word object into a ``WordSegment``."""

        return WordSegment(
            word=getattr(word, "word", "").strip(),
            start=getattr(word, "start", None),
            end=getattr(word, "end", None),
            probability=getattr(word, "probability", None),
        )

    def _normalize_segment(self, segment: Any, index: int) -> TextSegment:
        """Convert a Faster Whisper segment object into a ``TextSegment``."""

        return TextSegment(
            id=index,
            start=getattr(segment, "start", None),
            end=getattr(segment, "end", None),
            text=getattr(segment, "text", "").strip(),
            words=[
                self._normalize_word(word)
                for word in (getattr(segment, "words", None) or [])
            ],
        )

    def _normalize_result(
        self,
        raw_segments: list[Any],
        info: Any,
    ) -> TranscriptionResult:
        """Build a normalized transcription result from raw Whisper output."""

        normalized_segments = [
            self._normalize_segment(segment, index)
            for index, segment in enumerate(raw_segments)
        ]

        full_text = " ".join(
            segment.text for segment in normalized_segments
        ).strip()

        return TranscriptionResult(
            audio_path=self.audio_path,
            language=getattr(info, "language", self.language),
            text=full_text,
            segments=normalized_segments,
            provider=self.PROVIDER,
            model=self.model_name,
            raw_response={
                "language": getattr(info, "language", self.language),
                "duration": getattr(info, "duration", None),
                "duration_after_vad": getattr(info, "duration_after_vad", None),
            },
        )

    def transcribe(self) -> TranscriptionResult:
        """Run local transcription and return a normalized result.

        Returns:
            A ``TranscriptionResult`` containing full text, segment timing,
            optional word timing, model metadata, and local provider metadata.
        """

        model: Any = WhisperModel(self.model_name, device="cpu", compute_type="int8")
        segments_generator, info = model.transcribe(
            self.audio_path,
            language=self.language,
            temperature=self.temperature,
            word_timestamps=True,
        )

        raw_segments = list(segments_generator)

        return self._normalize_result(raw_segments, info)

    async def atranscribe(self) -> TranscriptionResult:
        
        model: Any = WhisperModel(self.model_name, device="cpu", compute_type="int8")
        segments_generator, info = await asyncio.to_thread(
            model.transcribe,
            self.audio_path,
            language=self.language,
            temperature=self.temperature,
            word_timestamps=True,
        )
        
        raw_segments = await asyncio.to_thread(list, segments_generator)
        
        return self._normalize_result(raw_segments, info)
