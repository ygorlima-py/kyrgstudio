"""Remote transcription providers.

This module contains API-backed transcriber implementations. Each class adapts
one external provider response into the shared ``TranscriptionResult`` schema
used by the application.
"""

import base64
import requests
import httpx
from typing import Any

from kyrg.transcribers.base import TranscriberAPIBase
from kyrg.transcribers.schemas import TranscriptionResult, WordSegment, TextSegment


class OpenRouterTranscriber(TranscriberAPIBase):
    """Transcriber implementation for OpenRouter audio transcription models.

    OpenRouter accepts audio as a base64-encoded payload in a JSON request.
    This adapter handles the provider-specific request format and normalizes
    the response into the common ``TranscriptionResult`` contract.
    """

    URL = "https://openrouter.ai/api/v1/audio/transcriptions"
    PROVIDER = "openrouter"

    def _open_file(self) -> str:
        """Read the configured audio file and return it as a base64 string."""

        with open(self.audio_path, "rb") as f:
            base64_audio = base64.b64encode(f.read()).decode("utf-8")
            return base64_audio

    def _request(self) -> dict[str, Any]:
        """Send the transcription request to OpenRouter.

        Returns:
            The decoded JSON response returned by the provider.

        Raises:
            RuntimeError: If the HTTP request fails or returns an error status.
        """

        request_args: dict[str, Any] = {
            "headers": {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            "json": {
                "model": self.model_name,
                "input_audio": {
                    "data": self._open_file(),
                    "format": "wav",
                },
                "temperature": self.temperature,
            },
            "timeout": 300,
        }

        if self.language is not None:
            request_args["json"]["language"] = self.language

        try:
            response = requests.post(self.URL, **request_args)
            response.raise_for_status()
            return response.json()

        except requests.RequestException as error:
            raise RuntimeError(f"Error calling OpenRouter provider: {error}") from error

    async def _arequest(self):
        """Send the transcription async request to OpenRouter.

        Returns:
            The decoded JSON response returned by the provider.

        Raises:
            RuntimeError: If the HTTP request fails or returns an error status.
        """
        request_args: dict[str, Any] = {
            "headers": {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            "json": {
                "model": self.model_name,
                "input_audio": {
                    "data": self._open_file(),
                    "format": "wav",
                },
                "temperature": self.temperature,
            },
            "timeout": 300,
        }

        if self.language is not None:
            request_args["json"]["language"] = self.language

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.URL, **request_args)
                response.raise_for_status()
                return response.json()
            
            except httpx.HTTPError as error:
                raise RuntimeError(f"Error calling OpenRouter provider: {error}")

    def _normalize_response(self, raw_result: dict[str, Any]) -> TranscriptionResult:
        """Convert an OpenRouter response into ``TranscriptionResult``."""

        return TranscriptionResult(
            audio_path=self.audio_path,
            language=raw_result.get("language", self.language),
            text=raw_result.get("text", "").strip(),
            segments=[],
            model=self.model_name,
            raw_response=raw_result,
            provider=self.PROVIDER,
        )


class OpenAITranscriber(TranscriberAPIBase):
    """Transcriber implementation for the OpenAI audio transcription API.

    OpenAI receives the audio file as multipart form data. This adapter keeps
    file handling scoped to the request and converts the provider response into
    the shared application schema.
    """

    URL = "https://api.openai.com/v1/audio/transcriptions"
    PROVIDER = "openai"

    def _request(self) -> dict[str, Any]:
        """Send the transcription request to OpenAI.

        Returns:
            The decoded JSON response returned by the provider.

        Raises:
            RuntimeError: If the HTTP request fails or returns an error status.
        """

        data = {
            "model": self.model_name,
            "response_format": "json",
        }

        if self.language:
            data["language"] = self.language

        request_args: dict[str, Any] = {
            "headers": {
                "Authorization": f"Bearer {self.api_key}",
            },
            "data": data,
            "timeout": 300,
        }

        try:
            with open(self.audio_path, "rb") as audio_file:
                response = requests.post(
                    self.URL,
                    **request_args,
                    files={"file": audio_file},
                )

            response.raise_for_status()
            return response.json()

        except requests.RequestException as error:
            raise RuntimeError(f"Error calling OpenAI provider: {error}") from error

    async def _arequest(self) -> dict[str, Any]:
        """Send the transcription request to OpenAI.

        Returns:
            The decoded JSON response returned by the provider.

        Raises:
            RuntimeError: If the HTTP request fails or returns an error status.
        """

        data = {
            "model": self.model_name,
            "response_format": "json",
        }

        if self.language:
            data["language"] = self.language

        request_args: dict[str, Any] = {
            "headers": {
                "Authorization": f"Bearer {self.api_key}",
            },
            "data": data,
            "timeout": 300,
        }

        try:
            with open(self.audio_path, "rb") as audio_file:
                files = {
                    "file": (
                        self.audio_path,
                        audio_file,
                        "application/octet-stream",
                    )
                }

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.URL,
                        **request_args,
                        files=files,
                    )

            response.raise_for_status()
            return response.json()
    
        except requests.RequestException as error:
            raise RuntimeError(f"Error calling OpenAI provider: {error}") from error
        
    def _normalize_response(self, raw_result: dict[str, Any]) -> TranscriptionResult:
        """Convert an OpenAI response into ``TranscriptionResult``."""

        return TranscriptionResult(
            audio_path=self.audio_path,
            language=raw_result.get("language", self.language),
            text=raw_result.get("text", "").strip(),
            segments=[],
            model=self.model_name,
            raw_response=raw_result,
            provider=self.PROVIDER,
        )


class ElevenLabsTranscriber(TranscriberAPIBase):
    """Transcriber implementation for the ElevenLabs speech-to-text API.

    ElevenLabs receives the audio file as multipart form data and can return
    word-level timing metadata. This adapter preserves that metadata as
    ``WordSegment`` instances inside a normalized ``TranscriptionResult``.
    """

    URL = "https://api.elevenlabs.io/v1/speech-to-text"
    PROVIDER = "elevenlabs"

    def _request(self) -> dict[str, Any]:
        """Send the transcription request to ElevenLabs.

        Returns:
            The decoded JSON response returned by the provider.

        Raises:
            RuntimeError: If the HTTP request fails or returns an error status.
        """

        data: dict[str, Any] = {
            "model_id": self.model_name,
            "timestamps_granularity": "word",
            "diarize": False,
            "temperature": self.temperature,
        }

        if self.language:
            data["language_code"] = self.language

        request_args: dict[str, Any] = {
            "headers": {
                "xi-api-key": self.api_key,
            },
            "data": data,
            "timeout": 300,
        }

        try:
            with open(self.audio_path, "rb") as audio_file:
                response = requests.post(
                    self.URL,
                    **request_args,
                    files={"file": audio_file},
                )

            response.raise_for_status()
            return response.json()

        except requests.RequestException as error:
            raise RuntimeError(f"Error calling ElevenLabs provider: {error}") from error

    async def _arequest(self) -> dict[str, Any]:
        """Send the transcription async request to ElevenLabs.

        Returns:
            The decoded JSON response returned by the provider.

        Raises:
            RuntimeError: If the HTTP request fails or returns an error status.
        """

        data: dict[str, Any] = {
            "model_id": self.model_name,
            "timestamps_granularity": "word",
            "diarize": False,
            "temperature": self.temperature,
        }

        if self.language:
            data["language_code"] = self.language

        request_args: dict[str, Any] = {
            "headers": {
                "xi-api-key": self.api_key,
            },
            "data": data,
            "timeout": 300,
        }

        try:
            with open(self.audio_path, "rb") as audio_file:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.URL,
                        **request_args,
                        files={"file": audio_file},
                    )

            response.raise_for_status()
            return response.json()
    
        except httpx.HTTPError as error:
            raise RuntimeError(f"Error calling ElevenLabs provider: {error}") from error
    
    def _normalize_response(self, raw_result: dict[str, Any]) -> TranscriptionResult:
        """Convert an ElevenLabs response into ``TranscriptionResult``."""

        words: list[WordSegment] = []

        for word in raw_result.get("words", []):
            if word.get("type") != "word":
                continue

            words.append(
                WordSegment(
                    word=word.get("text", "").strip(),
                    start=word.get("start"),
                    end=word.get("end"),
                    probability=word.get("logprob"),
                )
            )

        segment = TextSegment(
            id=0,
            start=words[0].start if words else None,
            end=words[-1].end if words else None,
            text=raw_result.get("text", "").strip(),
            words=words,
        )

        return TranscriptionResult(
            audio_path=self.audio_path,
            language=raw_result.get("language_code", self.language),
            text=raw_result.get("text", "").strip(),
            segments=[segment] if raw_result.get("text") else [],
            model=self.model_name,
            raw_response=raw_result,
            provider=self.PROVIDER,
        )
