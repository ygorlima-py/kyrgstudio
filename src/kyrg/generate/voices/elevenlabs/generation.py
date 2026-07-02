"""ElevenLabs audio generation adapters.

This module contains the public ElevenLabs actions that produce audio files:
text-to-speech and speech-to-speech. Each adapter translates a Kyrg input
schema into an ElevenLabs SDK call and normalizes the result into VoiceOutput.
"""

from typing import Any
 
from elevenlabs.client import ElevenLabs, AsyncElevenLabs
from elevenlabs.core.api_error import ApiError
 
from kyrg.adapters.base import APIAdapterSDKBase
from kyrg.generate.voices.schemas import SpeechToSpeechInput, TextToSpeechInput, VoiceOutput
from kyrg.generate.voices.elevenlabs.utils import _write_audio_chunks


class ElevenLabsVoiceGenerator(APIAdapterSDKBase[VoiceOutput, ElevenLabs]):
    """Generate speech audio from text using ElevenLabs.

    The adapter receives a TextToSpeechInput, calls the ElevenLabs
    text-to-speech endpoint, writes the streamed audio chunks to
    ``tts_input.output_path``, and returns a normalized VoiceOutput.

    Provider-specific options can be passed through ``tts_input.settings``.
    Supported settings currently include ``output_format`` and
    ``voice_settings``.
    """

    PROVIDER = "elevenlabs"
    
    def __init__(self, api_key: str, tts_input: TextToSpeechInput):
        """Initialize the ElevenLabs text-to-speech adapter.

        Args:
            api_key: ElevenLabs API key used to authenticate the SDK client.
            tts_input: Text, model, voice, output path, and optional settings.
        """

        client = ElevenLabs(api_key=api_key)
        super().__init__(client)
        self.async_client = AsyncElevenLabs(api_key=api_key)
        self.tts_input = tts_input
 
    def _request(self) -> dict[str, Any]:
        """Call ElevenLabs and persist the generated audio file.

        Returns:
            Raw adapter metadata used later to build VoiceOutput.

        Raises:
            RuntimeError: If the ElevenLabs SDK returns an ApiError.
        """

        output_format = self.tts_input.settings.get("output_format", "mp3_44100_128")
 
        kwargs: dict[str, Any] = {
            "voice_id": self.tts_input.voice,
            "text": self.tts_input.text,
            "model_id": self.tts_input.model,
            "output_format": output_format,
        }
 
        voice_settings = self.tts_input.settings.get("voice_settings")
        if voice_settings is not None:
            kwargs["voice_settings"] = voice_settings
 
        try:
            audio = self.client.text_to_speech.convert(**kwargs)
            _write_audio_chunks(self.tts_input.output_path, audio)
 
            return {
                "audio_path": self.tts_input.output_path,
                "model": self.tts_input.model,
                "voice": self.tts_input.voice,
                "output_format": output_format,
            }
 
        except ApiError as error:
            raise RuntimeError(f"Error calling ElevenLabs text-to-speech: {error}")

    async def _arequest(self) -> dict[str, Any]:
        """Call ElevenLabs asynchronously and persist the generated audio file."""

        output_format = self.tts_input.settings.get("output_format", "mp3_44100_128")

        kwargs: dict[str, Any] = {
            "voice_id": self.tts_input.voice,
            "text": self.tts_input.text,
            "model_id": self.tts_input.model,
            "output_format": output_format,
        }

        voice_settings = self.tts_input.settings.get("voice_settings")
        if voice_settings is not None:
            kwargs["voice_settings"] = voice_settings

        try:
            audio = self.async_client.text_to_speech.convert(**kwargs)

            with open(self.tts_input.output_path, "wb") as audio_file:
                async for chunk in audio:
                    audio_file.write(chunk)

            return {
                "audio_path": self.tts_input.output_path,
                "model": self.tts_input.model,
                "voice": self.tts_input.voice,
                "output_format": output_format,
            }

        except ApiError as error:
            raise RuntimeError(f"Error calling ElevenLabs text-to-speech: {error}")
 
    def _normalize_response(self, raw_result: dict[str, Any]) -> VoiceOutput:
        """Convert provider metadata into the public VoiceOutput schema."""

        return VoiceOutput(
            audio_path=raw_result["audio_path"],
            provider=self.PROVIDER,
            model=raw_result["model"],
            voice_id=raw_result["voice"],
            output_format=raw_result.get("output_format"),
            raw_response=raw_result,
        )
 
 
class ElevenLabsSpeechToSpeech(APIAdapterSDKBase[VoiceOutput, ElevenLabs]):
    """Convert an existing audio file into speech with another voice.

    The adapter opens ``speech_input.audio_path``, sends it to ElevenLabs
    speech-to-speech, writes the returned audio chunks to
    ``speech_input.output_path``, and returns a normalized VoiceOutput.

    Provider-specific options can be passed through ``speech_input.settings``.
    Supported settings currently include ``output_format``,
    ``voice_settings``, ``remove_background_noise``, and ``file_format``.
    """

    PROVIDER = "elevenlabs"

    def __init__(self, api_key: str, speech_input: SpeechToSpeechInput):
        """Initialize the ElevenLabs speech-to-speech adapter.

        Args:
            api_key: ElevenLabs API key used to authenticate the SDK client.
            speech_input: Source audio, model, voice, output path, and settings.
        """

        client = ElevenLabs(api_key=api_key)
        super().__init__(client)
        self.async_client = AsyncElevenLabs(api_key=api_key)
        self.speech_input = speech_input
 
    def _request(self) -> dict[str, Any]:
        """Call ElevenLabs and persist the converted audio file.

        Returns:
            Raw adapter metadata used later to build VoiceOutput.

        Raises:
            RuntimeError: If the ElevenLabs SDK returns an ApiError.
        """

        output_format = self.speech_input.settings.get("output_format", "mp3_44100_128")
 
        kwargs: dict[str, Any] = {
            "voice_id": self.speech_input.voice,
            "model_id": self.speech_input.model,
            "output_format": output_format,
        }
 
        for setting in ("voice_settings", "remove_background_noise", "file_format"):
            value = self.speech_input.settings.get(setting)
            if value is not None:
                kwargs[setting] = value
 
        try:
            with open(self.speech_input.audio_path, "rb") as audio_file:
                audio = self.client.speech_to_speech.convert(audio=audio_file, **kwargs)
                _write_audio_chunks(self.speech_input.output_path, audio)
 
            return {
                "audio_path": self.speech_input.output_path,
                "model": self.speech_input.model,
                "voice": self.speech_input.voice,
                "source_audio_path": self.speech_input.audio_path,
                "output_format": output_format,
            }
 
        except ApiError as error:
            raise RuntimeError(f"Error calling ElevenLabs speech-to-speech: {error}")

    async def _arequest(self) -> dict[str, Any]:
        """Call ElevenLabs asynchronously and persist the converted audio file."""

        output_format = self.speech_input.settings.get("output_format", "mp3_44100_128")

        kwargs: dict[str, Any] = {
            "voice_id": self.speech_input.voice,
            "model_id": self.speech_input.model,
            "output_format": output_format,
        }

        for setting in ("voice_settings", "remove_background_noise", "file_format"):
            value = self.speech_input.settings.get(setting)
            if value is not None:
                kwargs[setting] = value

        try:
            with open(self.speech_input.audio_path, "rb") as audio_file:
                audio = self.async_client.speech_to_speech.convert(
                    audio=audio_file,
                    **kwargs,
                )

                with open(self.speech_input.output_path, "wb") as output_file:
                    async for chunk in audio:
                        output_file.write(chunk)

            return {
                "audio_path": self.speech_input.output_path,
                "model": self.speech_input.model,
                "voice": self.speech_input.voice,
                "source_audio_path": self.speech_input.audio_path,
                "output_format": output_format,
            }

        except ApiError as error:
            raise RuntimeError(f"Error calling ElevenLabs speech-to-speech: {error}")
 
    def _normalize_response(self, raw_result: dict[str, Any]) -> VoiceOutput:
        """Convert provider metadata into the public VoiceOutput schema."""

        return VoiceOutput(
            audio_path=raw_result["audio_path"],
            provider=self.PROVIDER,
            model=raw_result["model"],
            voice_id=raw_result["voice"],
            output_format=raw_result.get("output_format"),
            raw_response=raw_result,
        )
 
