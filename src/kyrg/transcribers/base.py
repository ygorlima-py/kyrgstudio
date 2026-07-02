"""Base contracts for transcription providers.

This module defines the transcription-specific interface implemented by local
and remote providers. Local providers implement ``transcribe`` directly, while
remote providers combine the transcription contract with the shared API adapter
flow from ``kyrg.adapters``.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from kyrg.adapters.base import APIAdapterBase
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
    
    @abstractmethod
    async def atranscribe(self) -> TranscriptionResult:
        """
        Transcribe async the configured audio file.
        
        Returns:
            A normalized ``TranscriptionResult``.
        """
        pass


class TranscriberAPIBase(TranscriberBase, APIAdapterBase[TranscriptionResult]):
    """Base class for remote API-backed transcription providers.

    This class joins the transcription domain state from ``TranscriberBase``
    with the reusable API request flow from ``AdapterAPIBase``. Provider
    subclasses only need to implement ``_request`` and ``_normalize_response``;
    ``transcribe`` delegates to the shared adapter flow.
    """

    def __init__(
        self,
        audio_path: str,
        model_name: str,
        language: Optional[str],
        temperature: float,
        api_key: str,
    ):
        """Initialize shared remote transcription configuration.

        Args:
            audio_path: Path to the audio file that should be transcribed.
            model_name: Provider-specific model identifier.
            language: Optional language hint used by the provider.
            temperature: Sampling temperature used by supported providers.
            api_key: Secret API key used to authenticate with the provider.
        """

        super().__init__(audio_path, model_name, language, temperature)
        self.api_key = api_key
        
        
    def transcribe(self) -> TranscriptionResult:
        """Run the standard API transcription flow.

        The public transcription method stays domain-specific, while the
        request and normalization sequence is reused from ``AdapterAPIBase``.

        Returns:
            A normalized ``TranscriptionResult``.
        """

        return self.run()

    async def atranscribe(self) -> TranscriptionResult:
        return await self.arun()