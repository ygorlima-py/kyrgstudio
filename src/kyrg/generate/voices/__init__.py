"""Public voice generation API.

This package exposes the stable voice adapters and schemas intended for
library users. Provider internals, shared adapter bases, and helper functions
remain private to their modules.
"""

from kyrg.generate.voices.openai_provider import OpenAIVoiceGenerator
from kyrg.generate.voices.openrouter_provider import OpenRouterVoiceGenerator
from kyrg.generate.voices.elevenlabs import (
    ElevenLabsSpeechToSpeech,
    ElevenLabsVoiceCloner,
    ElevenLabsVoiceDesignPreview,
    ElevenLabsVoiceDesignSaver,
    ElevenLabsVoiceGenerator,
)

from kyrg.generate.voices.schemas import (
    SpeechToSpeechInput,
    TextToSpeechInput,
    VoiceCloneInput,
    VoiceDesignInput,
    VoiceDesignOutput,
    VoiceDesignPreview,
    VoiceDesignSaveInput,
    VoiceIdentityOutput,
    VoiceOutput,
)

__all__ = [
    "ElevenLabsSpeechToSpeech",
    "ElevenLabsVoiceCloner",
    "ElevenLabsVoiceDesignPreview",
    "ElevenLabsVoiceDesignSaver",
    "ElevenLabsVoiceGenerator",
    "OpenAIVoiceGenerator",
    "OpenRouterVoiceGenerator",
    "SpeechToSpeechInput",
    "TextToSpeechInput",
    "VoiceCloneInput",
    "VoiceDesignInput",
    "VoiceDesignOutput",
    "VoiceDesignPreview",
    "VoiceDesignSaveInput",
    "VoiceIdentityOutput",
    "VoiceOutput",
]
