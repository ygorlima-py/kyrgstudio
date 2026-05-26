"""Base contracts for transcription providers.

This module defines the common interface implemented by all transcription
providers. Concrete implementations may run locally or call remote APIs, but
they all expose the same ``transcribe`` contract and return a normalized
``TranscriptionResult``.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from kyrg.transcribers.schemas import TranscriptionResult



class TranscriberBase(ABC):
    """Abstract base class for all transcription providers.

    Subclasses receive the audio path, model name, optional language, and
    decoding temperature required to perform a transcription. Each subclass is
    responsible for implementing the provider-specific ``transcribe`` method.
    """

    PROVIDER = ""

    def __init__(
        self,
        audio_path: str,
        model_name: str,
        language: Optional[str] = None,
        temperature: float = 0,
    ):
        """Initialize shared transcription configuration.

        Args:
            audio_path: Path to the audio file that should be transcribed.
            model_name: Provider-specific model identifier.
            language: Optional language hint used by the provider.
            temperature: Sampling temperature used by supported providers.
        """

        self.audio_path = audio_path
        self.model_name = model_name
        self.language = language
        self.temperature = temperature

    @abstractmethod
    def transcribe(self) -> TranscriptionResult:
        """Transcribe the configured audio file.

        Returns:
            A normalized ``TranscriptionResult``.
        """

        pass


class TranscriberAPIBase(TranscriberBase):
    """Base class for remote API-backed transcription providers.

    API providers share the same high-level flow: send a provider-specific
    request, receive a raw response, and normalize that response into the
    application-level schema.
    """

    URL = ""

    def __init__(
        self,
        audio_path: str,
        model_name: str,
        language: str,
        temperature: float,
        api_key: str,
    ):
        """Initialize shared API transcription configuration.

        Args:
            audio_path: Path to the audio file that should be transcribed.
            model_name: Provider-specific model identifier.
            language: Optional language hint used by the provider.
            temperature: Sampling temperature used by supported providers.
            api_key: Secret API key used to authenticate with the provider.
        """

        super().__init__(audio_path, model_name, language, temperature)
        self.api_key = api_key

    @abstractmethod
    def _request(self) -> dict[str, Any]:
        """Send the provider-specific API request and return its raw response."""

        pass

    @abstractmethod
    def _normalize_response(self, response: dict[str, Any]) -> TranscriptionResult:
        """Normalize a provider response into ``TranscriptionResult``.

        Args:
            response: Raw response returned by the provider API.

        Returns:
            A normalized transcription result.
        """

        pass

    def transcribe(self) -> TranscriptionResult:
        """Run the standard API transcription flow.

        The default implementation delegates provider-specific request and
        normalization behavior to subclass implementations.

        Returns:
            A normalized ``TranscriptionResult``.
        """

        response = self._request()
        return self._normalize_response(response)
