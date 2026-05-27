"""Internal utilities for ElevenLabs voice adapters."""

from typing import Iterable


def _write_audio_chunks(output_path: str, audio: Iterable[bytes]) -> None:
    """Write streamed audio chunks to a binary file.

    ElevenLabs audio generation endpoints return an iterable of byte chunks.
    This helper centralizes the file writing behavior used by the generation
    adapters.

    Args:
        output_path: Destination path where the audio file will be written.
        audio: Iterable of audio byte chunks returned by the ElevenLabs SDK.
    """

    with open(output_path, "wb") as audio_file:
        for chunk in audio:
            audio_file.write(chunk)
