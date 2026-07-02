"""OpenAI voice generation adapters.

This module defines the OpenAI text-to-speech implementation and a reusable
base for providers that expose an OpenAI-compatible audio speech API. The
adapter writes streamed audio directly to the requested output path and returns
Kyrg's normalized VoiceOutput schema.
"""

from typing import Any

from openai import OpenAI, AsyncOpenAI, OpenAIError

from kyrg.adapters.base import APIAdapterSDKBase
from kyrg.generate.voices.schemas import TextToSpeechInput, VoiceOutput


class OpenAITTSBase(APIAdapterSDKBase[VoiceOutput, OpenAI]):
    """Base adapter for OpenAI-compatible text-to-speech providers.

    Subclasses only need to define ``PROVIDER`` and ``URL``. The request and
    normalization behavior is shared for providers that use the OpenAI SDK
    speech API shape.

    This class is intentionally not exported as the main user-facing API. It is
    infrastructure for concrete adapters such as OpenAIVoiceGenerator and
    OpenRouterVoiceGenerator.
    """
    
    def __init__(self, api_key: str, tts_input: TextToSpeechInput):
        """Initialize the OpenAI-compatible text-to-speech adapter.

        Args:
            api_key: API key used by the selected provider.
            tts_input: Text, model, voice, and output path for the request.
        """

        client = OpenAI(api_key=api_key, base_url=self.URL)
        super().__init__(client)
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=self.URL)
        self.tts_input = tts_input
        
    def _request(self) -> dict[str, Any]:
        """Call the provider and stream the generated audio to disk.

        Returns:
            Raw adapter metadata used later to build VoiceOutput.

        Raises:
            RuntimeError: If the OpenAI SDK returns an OpenAIError.
        """

        try:
            with self.client.audio.speech.with_streaming_response.create(
                    model=self.tts_input.model,
                    input=self.tts_input.text,
                    voice=self.tts_input.voice,
            ) as response:
                
                response.stream_to_file(self.tts_input.output_path)
            
            return {
                "audio_path": self.tts_input.output_path,
                "model": self.tts_input.model,
                "voice": self.tts_input.voice,
            }
            
        except OpenAIError as error:
            raise RuntimeError(
                f"Error calling {self.PROVIDER} speech provider: {error}"
            ) from error

    async def _arequest(self) -> dict[str, Any]:
        """Call the provider asynchronously and stream audio to disk."""

        try:
            async with self.async_client.audio.speech.with_streaming_response.create(
                    model=self.tts_input.model,
                    input=self.tts_input.text,
                    voice=self.tts_input.voice,
            ) as response:

                await response.stream_to_file(self.tts_input.output_path)

            return {
                "audio_path": self.tts_input.output_path,
                "model": self.tts_input.model,
                "voice": self.tts_input.voice,
            }

        except OpenAIError as error:
            raise RuntimeError(
                f"Error calling {self.PROVIDER} speech provider: {error}"
            ) from error
        
    def _normalize_response(self, raw_result: dict[str, Any]) -> VoiceOutput:
        """Convert provider metadata into the public VoiceOutput schema."""

        return VoiceOutput(
            audio_path=raw_result['audio_path'],
            provider=self.PROVIDER,
            model=raw_result['model'],
            voice_id=raw_result['voice'],
            raw_response=raw_result,
        )


class OpenAIVoiceGenerator(OpenAITTSBase):
    """Generate speech audio with OpenAI's text-to-speech API."""

    PROVIDER = 'openai'
    URL = "https://api.openai.com/v1"
