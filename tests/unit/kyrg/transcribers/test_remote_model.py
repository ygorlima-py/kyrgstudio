"""Unit tests for remote transcription provider adapters."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from kyrg.transcribers.remote_model import OpenRouterTranscriber


def _transcriber(audio_path: Path) -> OpenRouterTranscriber:
    """Build an OpenRouter adapter without making a network request."""

    return OpenRouterTranscriber(
        audio_path=str(audio_path),
        model_name="openai/whisper-large-v3",
        language="pt",
        temperature=0.0,
        api_key="test-secret",
    )


def test_openrouter_payload_uses_mp3_extension_and_base64_data(
    tmp_path: Path,
) -> None:
    """Keep the declared provider format aligned with the encoded file."""

    audio_path = tmp_path / "transcription.mp3"
    audio_bytes = b"compressed-audio"
    audio_path.write_bytes(audio_bytes)

    payload = _transcriber(audio_path)._request_payload()

    assert payload == {
        "model": "openai/whisper-large-v3",
        "input_audio": {
            "data": base64.b64encode(audio_bytes).decode("utf-8"),
            "format": "mp3",
        },
        "temperature": 0.0,
        "language": "pt",
    }
    assert "test-secret" not in repr(payload)


def test_openrouter_rejects_unknown_audio_extension(tmp_path: Path) -> None:
    """Reject files whose extension cannot be represented in the API payload."""

    audio_path = tmp_path / "transcription.bin"
    audio_path.write_bytes(b"audio")

    with pytest.raises(ValueError, match="Unsupported OpenRouter"):
        _transcriber(audio_path)._request_payload()
